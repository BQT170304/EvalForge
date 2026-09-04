"""Agent trajectory optimality evaluation metric."""

import json
import time

import structlog

from evalforge.engine.base import (
    EvalForgeMetric,
    EvalTestCase,
    MetricCategory,
    MetricResult,
    MetricSource,
)
from evalforge.engine.registry import MetricRegistry
from evalforge.utils.llm_client import get_llm_client

logger = structlog.get_logger(__name__)


@MetricRegistry.register("trajectory_optimality")
class TrajectoryOptimality(EvalForgeMetric):
    """Evaluates whether an agent's execution trajectory followed an optimal, direct path without redundant actions."""

    name: str = "trajectory_optimality"
    category: MetricCategory = MetricCategory.AGENT
    source: MetricSource = MetricSource.CUSTOM
    version: str = "1.0.0"

    def __init__(
        self,
        threshold: float = 0.7,
        max_allowed_steps: int = 15,
        judge_model: str | None = None,
    ) -> None:
        super().__init__(threshold=threshold)
        self.max_allowed_steps = max_allowed_steps
        self.judge_model = judge_model

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.perf_counter()
        cost_usd = 0.0

        steps = test_case.trajectory or test_case.tool_calls or []
        step_count = len(steps)

        # If no trajectory provided, assume 1-step direct answer
        if step_count == 0:
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                threshold=self.threshold,
                reason="Direct answer without external tool overhead",
                source=self.source,
                category=self.category,
                details={"step_count": 0, "redundant_steps": 0},
                cost_usd=0.0,
                latency_ms=latency,
            )

        prompt = f"""You are an expert systems evaluator auditing the execution trajectory of an autonomous AI Agent.

Task / Goal:
{test_case.input}

Execution Trajectory ({step_count} actions):
{json.dumps(steps, indent=2)}

Final Output:
{test_case.output}

Analyze the trajectory for efficiency and optimality:
1. Identify any redundant, duplicated, circular, or unnecessary tool actions.
2. Estimate the minimal number of steps an optimal agent would require.
3. Compute the optimality score between 0.0 and 1.0 (1.0 = perfect direct path; < 0.5 = heavy meandering/waste).

Respond ONLY with valid JSON in this exact structure:
{{
  "optimality_score": <float between 0.0 and 1.0>,
  "estimated_optimal_steps": <int>,
  "actual_steps": {step_count},
  "redundant_step_count": <int>,
  "reason": "<clear explanation>",
  "inefficient_actions": ["<description of unnecessary step>"]
}}"""

        try:
            llm = get_llm_client(self.judge_model)
            response_text, cost_usd, _ = await llm.complete(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )

            parsed = json.loads(response_text)
            score = float(parsed.get("optimality_score", 0.0))
            reason = parsed.get("reason", "Trajectory evaluated.")
            passed = score >= self.threshold

            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=score,
                passed=passed,
                threshold=self.threshold,
                reason=reason,
                source=self.source,
                category=self.category,
                details={
                    "actual_steps": step_count,
                    "estimated_optimal_steps": parsed.get("estimated_optimal_steps", step_count),
                    "redundant_step_count": parsed.get("redundant_step_count", 0),
                    "inefficient_actions": parsed.get("inefficient_actions", []),
                },
                cost_usd=cost_usd,
                latency_ms=latency,
            )

        except Exception as e:
            logger.warning("trajectory_optimality_evaluation_failed", error=str(e))
            # Fallback heuristic calculation based on step count bounds
            ratio = max(0.0, 1.0 - (step_count / max(1, self.max_allowed_steps * 2)))
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=ratio,
                passed=ratio >= self.threshold,
                threshold=self.threshold,
                reason=f"Step ratio heuristic fallback ({step_count} steps): {e!s}",
                source=self.source,
                category=self.category,
                details={"step_count": step_count, "fallback": True},
                cost_usd=cost_usd,
                latency_ms=latency,
            )
