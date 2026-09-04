"""Experiment comparison engine for delta analysis and regression detection."""

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from evalforge.models.db import EvaluationRunModel, ExperimentModel

logger = structlog.get_logger(__name__)


class ExperimentComparator:
    """Computes regressions, improvements, and delta statistics between baseline and candidate experiment runs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def compare(self, baseline_id: uuid.UUID, candidate_id: uuid.UUID) -> dict[str, Any]:
        """Compares two completed experiments and returns detailed delta analytics."""
        stmt = (
            select(ExperimentModel)
            .where(ExperimentModel.id.in_([baseline_id, candidate_id]))
            .options(
                selectinload(ExperimentModel.evaluation_runs).selectinload(
                    EvaluationRunModel.results
                )
            )
        )
        result = await self.db.execute(stmt)
        experiments = {e.id: e for e in result.scalars().all()}

        baseline = experiments.get(baseline_id)
        candidate = experiments.get(candidate_id)

        if not baseline or not candidate:
            raise ValueError("One or both experiments could not be found")

        # 1. High-level metric comparisons
        base_pass_rate = baseline.pass_rate or 0.0
        cand_pass_rate = candidate.pass_rate or 0.0
        pass_rate_delta = cand_pass_rate - base_pass_rate

        cost_delta = candidate.total_cost_usd - baseline.total_cost_usd
        duration_delta = (candidate.duration_seconds or 0.0) - (baseline.duration_seconds or 0.0)

        # 2. Per-metric delta breakdown
        base_scores = baseline.summary_scores or {}
        cand_scores = candidate.summary_scores or {}
        all_metrics = set(base_scores.keys()).union(cand_scores.keys())

        metric_deltas: dict[str, Any] = {}
        for m in all_metrics:
            b_avg = base_scores.get(m, {}).get("average", 0.0)
            c_avg = cand_scores.get(m, {}).get("average", 0.0)
            delta = c_avg - b_avg
            metric_deltas[m] = {
                "baseline_average": b_avg,
                "candidate_average": c_avg,
                "delta": float(delta),
                "status": "improved"
                if delta > 0.02
                else ("regressed" if delta < -0.02 else "unchanged"),
            }

        # 3. Item-level regression & improvement tracking
        base_runs_by_input = {r.input: r for r in baseline.evaluation_runs}
        cand_runs_by_input = {r.input: r for r in candidate.evaluation_runs}

        regressions: list[dict[str, Any]] = []
        improvements: list[dict[str, Any]] = []

        for inp, c_run in cand_runs_by_input.items():
            if inp in base_runs_by_input:
                b_run = base_runs_by_input[inp]
                if b_run.overall_passed and not c_run.overall_passed:
                    regressions.append(
                        {
                            "input": inp,
                            "baseline_score": b_run.average_score,
                            "candidate_score": c_run.average_score,
                            "candidate_output": c_run.output,
                        }
                    )
                elif not b_run.overall_passed and c_run.overall_passed:
                    improvements.append(
                        {
                            "input": inp,
                            "baseline_score": b_run.average_score,
                            "candidate_score": c_run.average_score,
                            "candidate_output": c_run.output,
                        }
                    )

        has_regression = len(regressions) > 0 or pass_rate_delta < -0.01

        return {
            "baseline": {
                "id": str(baseline.id),
                "name": baseline.name,
                "version": baseline.dataset_version,
                "pass_rate": base_pass_rate,
                "cost_usd": baseline.total_cost_usd,
            },
            "candidate": {
                "id": str(candidate.id),
                "name": candidate.name,
                "version": candidate.dataset_version,
                "pass_rate": cand_pass_rate,
                "cost_usd": candidate.total_cost_usd,
            },
            "summary_deltas": {
                "pass_rate_delta": float(pass_rate_delta),
                "cost_delta_usd": float(cost_delta),
                "duration_delta_seconds": float(duration_delta),
                "has_regression": has_regression,
                "regression_count": len(regressions),
                "improvement_count": len(improvements),
            },
            "metric_deltas": metric_deltas,
            "regressions": regressions[:20],
            "improvements": improvements[:20],
        }
