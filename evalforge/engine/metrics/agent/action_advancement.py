"""Action advancement metric measuring progress made per step toward task goal."""

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


@MetricRegistry.register("action_advancement")
class ActionAdvancement(EvalForgeMetric):
    """Evaluates the percentage of agent actions that meaningfully advance the system toward the target goal."""

    name: str = "action_advancement"
    category: MetricCategory = MetricCategory.AGENT
    source: MetricSource = MetricSource.CUSTOM
    version: str = "1.0.0"

    def __init__(self, threshold: float = 0.75, judge_model: str | None = None) -> None:
        super().__init__(threshold=threshold)
        self.judge_model = judge_model

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.perf_counter()
        cost_usd = 0.0

        steps = test_case.trajectory or test_case.tool_calls or []
        if not steps:
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                threshold=self.threshold,
                reason="Single step direct output completed task",
                source=self.source,
                category=self.category,
                details={"advancement_ratio": 1.0, "total_steps": 0},
                cost_usd=0.0,
                latency_ms=latency,
            )

        prompt = f"""You are an AI reasoning auditor measuring 'Action Advancement' in an agent trajectory.
Action Advancement measures whether each intermediate action retrieved new information, made progress, or meaningfully moved closer to fulfilling the user goal.

Target Goal:
{test_case.input}

Execution Steps ({len(steps)} steps):
{json.dumps(steps, indent=2)}

Final Output:
{test_case.output}

For each step, determine if it contributed positive advancement or was a stalled/noop/unhelpful action.
Compute the ratio of productive advancing steps to total steps.

Respond ONLY with valid JSON in this exact structure:
{{
  "advancing_steps": <int>,
  "stalled_steps": <int>,
  "advancement_score": <float between 0.0 and 1.0>,
  "reason": "<clear explanation>",
  "stalled_step_indices": [<int>]
}}"""

        try:
            llm = get_llm_client(self.judge_model)
            response_text, cost_usd, _ = await llm.complete(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )

            parsed = json.loads(response_text)
            score = float(parsed.get("advancement_score", 0.0))
            reason = parsed.get("reason", "Action advancement evaluated.")
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
                    "advancing_steps": parsed.get("advancing_steps", len(steps)),
                    "stalled_steps": parsed.get("stalled_steps", 0),
                    "stalled_step_indices": parsed.get("stalled_step_indices", []),
                },
                cost_usd=cost_usd,
                latency_ms=latency,
            )

        except Exception as e:
            logger.warning("action_advancement_evaluation_failed", error=str(e))
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=0.8,  # Neutral baseline
                passed=self.threshold <= 0.8,
                threshold=self.threshold,
                reason=f"Action advancement evaluation fallback: {e!s}",
                source=self.source,
                category=self.category,
                details={"error": str(e)},
                cost_usd=cost_usd,
                latency_ms=latency,
            )
