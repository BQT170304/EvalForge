"""Agent task completion evaluation metric."""

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


@MetricRegistry.register("task_completion")
class TaskCompletionRate(EvalForgeMetric):
    """Evaluates whether an autonomous agent successfully completed its requested goal or task."""

    name: str = "task_completion"
    category: MetricCategory = MetricCategory.AGENT
    source: MetricSource = MetricSource.CUSTOM
    version: str = "1.0.0"

    def __init__(self, threshold: float = 0.8, judge_model: str | None = None) -> None:
        super().__init__(threshold=threshold)
        self.judge_model = judge_model

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.perf_counter()
        cost_usd = 0.0

        if not test_case.input or not test_case.output:
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason="Input query or output is empty",
                source=self.source,
                category=self.category,
                details={},
                cost_usd=0.0,
                latency_ms=latency,
            )

        # Deterministic check if expected_output exact match is present
        if (
            test_case.expected_output
            and test_case.output.strip() == test_case.expected_output.strip()
        ):
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                threshold=self.threshold,
                reason="Task output exactly matches expected ground truth",
                source=self.source,
                category=self.category,
                details={"method": "exact_match"},
                cost_usd=0.0,
                latency_ms=latency,
            )

        trajectory_summary = ""
        if test_case.trajectory:
            trajectory_summary = (
                f"\nAgent Action Trajectory ({len(test_case.trajectory)} steps):\n"
                + json.dumps(test_case.trajectory, indent=2)
            )
        elif test_case.tool_calls:
            trajectory_summary = (
                f"\nTool Invocations ({len(test_case.tool_calls)} calls):\n"
                + json.dumps(test_case.tool_calls, indent=2)
            )

        prompt = f"""You are an objective AI evaluation judge assessing whether an AI Agent completed its assigned task.

Task / User Goal:
{test_case.input}

Expected Goal / Criteria (if specified):
{test_case.expected_output or "Evaluate strictly against the user goal."}
{trajectory_summary}

Final Agent Output:
{test_case.output}

Evaluate the task completion on a scale from 0.0 to 1.0 where:
- 1.0: Task completely fulfilled without errors.
- 0.5: Task partially completed (some goals met, key elements missing or imperfect).
- 0.0: Task completely failed, unaddressed, or aborted.

Respond ONLY with valid JSON in this exact structure:
{{
  "score": <float between 0.0 and 1.0>,
  "completed": <true/false>,
  "reason": "<clear explanation>",
  "missing_elements": ["<element 1>", "<element 2>"]
}}"""

        try:
            llm = get_llm_client(self.judge_model)
            response_text, cost_usd, _ = await llm.complete(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )

            parsed = json.loads(response_text)
            score = float(parsed.get("score", 0.0))
            reason = parsed.get("reason", "Task completion evaluated.")
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
                    "completed": parsed.get("completed", passed),
                    "missing_elements": parsed.get("missing_elements", []),
                },
                cost_usd=cost_usd,
                latency_ms=latency,
            )

        except Exception as e:
            logger.warning("task_completion_evaluation_failed", error=str(e))
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason=f"Evaluation error: {e!s}",
                source=self.source,
                category=self.category,
                details={"error": str(e)},
                cost_usd=cost_usd,
                latency_ms=latency,
            )
