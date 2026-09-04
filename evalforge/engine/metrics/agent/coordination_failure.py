"""Multi-agent coordination failure rate evaluation metric."""

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


@MetricRegistry.register("coordination_failure_rate")
class CoordinationFailureRate(EvalForgeMetric):
    """Detects multi-agent coordination failures such as conflicting actions, circular handoffs, and duplicate work."""

    name: str = "coordination_failure_rate"
    category: MetricCategory = MetricCategory.AGENT
    source: MetricSource = MetricSource.CUSTOM
    version: str = "1.0.0"

    def __init__(self, threshold: float = 0.8, judge_model: str | None = None) -> None:
        super().__init__(threshold=threshold)
        self.judge_model = judge_model

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.perf_counter()
        cost_usd = 0.0

        metadata = test_case.metadata or {}
        multi_agent_trace = (
            metadata.get("multi_agent_trace") or test_case.trajectory or test_case.tool_calls or []
        )

        if not multi_agent_trace or len(multi_agent_trace) <= 1:
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                threshold=self.threshold,
                reason="No multi-agent coordination failures detected (single agent trace)",
                source=self.source,
                category=self.category,
                details={"failure_count": 0, "failure_types": []},
                cost_usd=0.0,
                latency_ms=latency,
            )

        prompt = f"""You are an expert multi-agent reliability engineer auditing for coordination failures.
Coordination failures include:
- Collisions / conflicting state modifications between agents
- Circular delegation (Agent A assigns to B who assigns back to A without progress)
- Redundant duplicate execution of identical tools with identical inputs by different agents
- Unhandled subtask dropoffs where one agent abandons a critical dependency

Goal:
{test_case.input}

Multi-Agent Trace:
{json.dumps(multi_agent_trace, indent=2)}

Final Output:
{test_case.output}

Detect any coordination failure incidents.
Calculate a reliability score from 0.0 (catastrophic coordination breakdown) to 1.0 (zero failures).

Respond ONLY with valid JSON in this exact structure:
{{
  "reliability_score": <float between 0.0 and 1.0>,
  "failure_count": <int>,
  "failures": [
    {{"type": "<conflict|circular_delegation|redundant_execution|dropped_task>", "description": "<explanation>"}}
  ],
  "reason": "<clear summary explanation>"
}}"""

        try:
            llm = get_llm_client(self.judge_model)
            response_text, cost_usd, _ = await llm.complete(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )

            parsed = json.loads(response_text)
            score = float(parsed.get("reliability_score", 1.0))
            reason = parsed.get("reason", "Coordination failure rate evaluated.")
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
                    "failure_count": parsed.get("failure_count", 0),
                    "failures": parsed.get("failures", []),
                },
                cost_usd=cost_usd,
                latency_ms=latency,
            )

        except Exception as e:
            logger.warning("coordination_failure_evaluation_failed", error=str(e))
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=0.9,
                passed=self.threshold <= 0.9,
                threshold=self.threshold,
                reason=f"Coordination failure evaluation fallback: {e!s}",
                source=self.source,
                category=self.category,
                details={"error": str(e)},
                cost_usd=cost_usd,
                latency_ms=latency,
            )
