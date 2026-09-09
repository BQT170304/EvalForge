"""Experiment execution engine evaluating datasets against configured metric suites."""

import asyncio
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from evalforge.datasets.converter import DatasetConverter
from evalforge.datasets.manager import DatasetManager
from evalforge.engine.base import MetricResult
from evalforge.engine.orchestrator import EvaluationOrchestrator
from evalforge.models.db import (
    DatasetModel,
    EvaluationResultModel,
    EvaluationRunModel,
    EvaluationStatus,
    ExperimentModel,
    ExperimentStatus,
)
from evalforge.utils.llm_client import get_llm_client

logger = structlog.get_logger(__name__)


class ExperimentRunner:
    """Orchestrates reproducible batch evaluation runs across versioned datasets."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orchestrator = EvaluationOrchestrator()

    async def create_experiment(
        self,
        name: str,
        dataset_id: uuid.UUID,
        metrics: list[str],
        description: str | None = None,
        thresholds: dict[str, float] | None = None,
        judge_model: str = "gpt-4o",
        target_model: str | None = None,
        prompt_version: str | None = None,
    ) -> ExperimentModel:
        """Initializes a new Experiment record in the database."""
        dm = DatasetManager(self.db)
        dataset = await dm.get_dataset(dataset_id, include_entries=False)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        metrics_config = []
        for m in metrics:
            cfg: dict[str, Any] = {"name": m}
            if thresholds and m in thresholds:
                cfg["threshold"] = thresholds[m]
            metrics_config.append(cfg)

        experiment_id = uuid.uuid4()
        now = datetime.now(UTC)

        experiment = ExperimentModel(
            id=experiment_id,
            name=name,
            description=description,
            dataset_id=dataset_id,
            dataset_version=dataset.version,
            metrics_config=metrics_config,
            judge_model=judge_model,
            target_model=target_model,
            prompt_version=prompt_version,
            status=ExperimentStatus.PENDING.value,
            total_entries=dataset.entry_count,
            created_at=now,
        )
        self.db.add(experiment)
        await self.db.flush()

        logger.info(
            "experiment_created",
            experiment_id=str(experiment_id),
            name=name,
            dataset_id=str(dataset_id),
        )
        return experiment

    async def run_experiment(
        self,
        experiment_id: uuid.UUID,
        system_prompt: str | None = None,
        concurrency: int = 5,
    ) -> ExperimentModel:
        """Executes an experiment asynchronously across all entries in its associated dataset."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ExperimentModel)
            .where(ExperimentModel.id == experiment_id)
            .options(selectinload(ExperimentModel.dataset).selectinload(DatasetModel.entries))
        )
        result = await self.db.execute(stmt)
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        dataset = experiment.dataset
        entries = dataset.entries if dataset else []

        experiment.status = ExperimentStatus.RUNNING.value
        await self.db.flush()

        start_time = time.perf_counter()
        metric_names = [m["name"] for m in experiment.metrics_config]
        threshold_map = {m["name"]: m.get("threshold", 0.7) for m in experiment.metrics_config}

        metric_configs: dict[str, Any] = {}
        for m in experiment.metrics_config:
            cfg = {"judge_model": experiment.judge_model}
            if "threshold" in m:
                cfg["threshold"] = m["threshold"]
            metric_configs[m["name"]] = cfg

        semaphore = asyncio.Semaphore(concurrency)
        total_cost = 0.0
        passed_entries = 0
        failed_entries = 0
        all_metric_scores: dict[str, list[float]] = {m: [] for m in metric_names}

        async def process_entry(entry: Any) -> None:
            nonlocal total_cost, passed_entries, failed_entries
            async with semaphore:
                # 1. Generate target model output if target_model is specified and output is missing
                actual_output = entry.expected_output or ""
                target_latency = 0.0
                target_cost = 0.0

                if experiment.target_model:
                    try:
                        llm = get_llm_client(experiment.target_model)
                        messages = []
                        if system_prompt:
                            messages.append({"role": "system", "content": system_prompt})
                        messages.append({"role": "user", "content": entry.input})

                        t0 = time.perf_counter()
                        actual_output, target_cost, _ = await llm.complete(messages=messages)
                        target_latency = (time.perf_counter() - t0) * 1000
                    except Exception as e:
                        logger.error(
                            "target_model_generation_error", entry_id=str(entry.id), error=str(e)
                        )
                        actual_output = f"Generation Error: {e}"

                test_case = DatasetConverter.entry_to_eval_test_case(
                    entry,
                    actual_output=actual_output,
                    latency_ms=target_latency,
                    cost_usd=target_cost,
                )

                # 2. Evaluate entry
                metric_results: list[MetricResult] = await self.orchestrator.evaluate(
                    test_case=test_case,
                    metric_names=metric_names,
                    config=metric_configs,
                )

                # 3. Aggregate entry results
                entry_passed = all(r.passed for r in metric_results) if metric_results else False
                entry_avg = (
                    sum(r.score for r in metric_results) / len(metric_results)
                    if metric_results
                    else 0.0
                )
                entry_cost = target_cost + sum(r.cost_usd for r in metric_results)
                entry_latency = target_latency + sum(r.latency_ms for r in metric_results)

                if entry_passed:
                    passed_entries += 1
                else:
                    failed_entries += 1

                total_cost += entry_cost

                # 4. Save evaluation run & individual scores
                now = datetime.now(UTC)
                run_id = uuid.uuid4()
                run_model = EvaluationRunModel(
                    id=run_id,
                    experiment_id=experiment.id,
                    status=EvaluationStatus.COMPLETED.value,
                    input=test_case.input,
                    output=test_case.output,
                    expected_output=test_case.expected_output,
                    context=test_case.context,
                    metadata_=test_case.metadata or {},
                    overall_passed=entry_passed,
                    average_score=entry_avg,
                    total_cost_usd=entry_cost,
                    latency_ms=entry_latency,
                    created_at=now,
                    completed_at=now,
                )
                self.db.add(run_model)

                for r in metric_results:
                    all_metric_scores[r.metric_name].append(r.score)
                    res_model = EvaluationResultModel(
                        run_id=run_id,
                        metric_name=r.metric_name,
                        category=r.category.value
                        if hasattr(r.category, "value")
                        else str(r.category),
                        source=r.source.value if hasattr(r.source, "value") else str(r.source),
                        score=r.score,
                        passed=r.passed,
                        threshold=r.threshold,
                        reason=r.reason,
                        details=r.details,
                        cost_usd=r.cost_usd,
                        latency_ms=r.latency_ms,
                        created_at=now,
                    )
                    self.db.add(res_model)

        # Run all entries concurrently
        tasks = [process_entry(e) for e in entries]
        if tasks:
            await asyncio.gather(*tasks)

        total_duration = time.perf_counter() - start_time
        total_evaluated = passed_entries + failed_entries
        pass_rate = (passed_entries / total_evaluated) if total_evaluated > 0 else 0.0

        summary_scores: dict[str, Any] = {}
        for metric_key, scores in all_metric_scores.items():
            if scores:
                summary_scores[metric_key] = {
                    "average": float(sum(scores) / len(scores)),
                    "min": float(min(scores)),
                    "max": float(max(scores)),
                    "pass_rate": float(
                        sum(1 for s in scores if s >= threshold_map.get(metric_key, 0.7))
                        / len(scores)
                    ),
                }

        now = datetime.now(UTC)
        experiment.status = ExperimentStatus.COMPLETED.value
        experiment.pass_rate = pass_rate
        experiment.summary_scores = summary_scores
        experiment.total_cost_usd = total_cost
        experiment.duration_seconds = total_duration
        experiment.total_entries = total_evaluated
        experiment.passed_entries = passed_entries
        experiment.failed_entries = failed_entries
        experiment.completed_at = now

        await self.db.flush()
        logger.info(
            "experiment_completed",
            experiment_id=str(experiment.id),
            pass_rate=pass_rate,
            duration=f"{total_duration:.2f}s",
            cost=f"${total_cost:.4f}",
        )
        return experiment
