"""Multi-agent coordination overhead evaluation metric."""

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

logger = structlog.get_logger(__name__)


@MetricRegistry.register("coordination_overhead")
class CoordinationOverhead(EvalForgeMetric):
    """Evaluates communication and token overhead in multi-agent cooperative workflows."""

    name: str = "coordination_overhead"
    category: MetricCategory = MetricCategory.AGENT
    source: MetricSource = MetricSource.CUSTOM
    version: str = "1.0.0"

    def __init__(
        self,
        threshold: float = 0.6,
        max_acceptable_messages: int = 20,
        max_acceptable_tokens: int = 10000,
    ) -> None:
        super().__init__(threshold=threshold)
        self.max_acceptable_messages = max_acceptable_messages
        self.max_acceptable_tokens = max_acceptable_tokens

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.perf_counter()

        metadata = test_case.metadata or {}
        messages = metadata.get("agent_messages") or metadata.get("inter_agent_messages") or []
        total_tokens = metadata.get("coordination_tokens") or 0

        # Estimate tokens if not explicitly in metadata
        if not total_tokens and messages:
            total_tokens = sum(len(str(m).split()) * 4 // 3 for m in messages)

        message_count = len(messages)

        if message_count == 0 and total_tokens == 0:
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                threshold=self.threshold,
                reason="Zero inter-agent coordination overhead detected",
                source=self.source,
                category=self.category,
                details={"message_count": 0, "token_count": 0, "efficiency": 1.0},
                cost_usd=0.0,
                latency_ms=latency,
            )

        # Efficiency calculation: higher score means leaner communication
        msg_efficiency = max(
            0.0, 1.0 - (message_count / max(1, self.max_acceptable_messages * 1.5))
        )
        tok_efficiency = max(0.0, 1.0 - (total_tokens / max(1, self.max_acceptable_tokens * 1.5)))

        score = (msg_efficiency * 0.4) + (tok_efficiency * 0.6)
        passed = score >= self.threshold

        reason = f"Coordination overhead efficiency {score:.2f} ({message_count} messages, ~{total_tokens} tokens)"

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
                "message_count": message_count,
                "token_count": total_tokens,
                "message_efficiency": msg_efficiency,
                "token_efficiency": tok_efficiency,
            },
            cost_usd=0.0,
            latency_ms=latency,
        )
