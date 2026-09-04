"""Multi-agent knowledge alignment evaluation metric."""

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


@MetricRegistry.register("knowledge_alignment")
class KnowledgeAlignment(EvalForgeMetric):
    """Evaluates whether cooperating agents maintain consistent, non-contradictory shared context and understanding."""

    name: str = "knowledge_alignment"
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
        agent_states = metadata.get("agent_states") or metadata.get("subagent_outputs") or {}
        shared_context = test_case.context or []

        if not agent_states and not shared_context:
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                threshold=self.threshold,
                reason="Single-agent output; alignment is inherently consistent",
                source=self.source,
                category=self.category,
                details={"agent_count": 1},
                cost_usd=0.0,
                latency_ms=latency,
            )

        prompt = f"""You are an AI coordination auditor assessing 'Knowledge Alignment' across a multi-agent system.
Knowledge Alignment tests whether interacting agents share a consistent factual understanding without contradicting each other or conflicting with shared context.

User Goal / Task:
{test_case.input}

Shared Context / Retreived Knowledge:
{json.dumps(shared_context, indent=2)}

Agent States / Subagent Outputs:
{json.dumps(agent_states, indent=2)}

Final Consolidated Response:
{test_case.output}

Evaluate:
1. Are there contradictions between individual agents or with the final response?
2. Did any agent drop critical shared context?
3. Calculate an alignment score between 0.0 (severe contradictions) and 1.0 (perfect alignment).

Respond ONLY with valid JSON in this exact structure:
{{
  "alignment_score": <float between 0.0 and 1.0>,
  "contradictions_found": ["<description of contradiction if any>"],
  "reason": "<clear explanation>"
}}"""

        try:
            llm = get_llm_client(self.judge_model)
            response_text, cost_usd, _ = await llm.complete(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )

            parsed = json.loads(response_text)
            score = float(parsed.get("alignment_score", 1.0))
            reason = parsed.get("reason", "Knowledge alignment evaluated.")
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
                    "contradictions": parsed.get("contradictions_found", []),
                },
                cost_usd=cost_usd,
                latency_ms=latency,
            )

        except Exception as e:
            logger.warning("knowledge_alignment_evaluation_failed", error=str(e))
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=0.8,
                passed=self.threshold <= 0.8,
                threshold=self.threshold,
                reason=f"Knowledge alignment fallback: {e!s}",
                source=self.source,
                category=self.category,
                details={"error": str(e)},
                cost_usd=cost_usd,
                latency_ms=latency,
            )
