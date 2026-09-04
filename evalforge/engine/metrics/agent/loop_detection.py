"""Agent loop and cycle detection evaluation metric."""

import hashlib
import json
import time
from typing import Any

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


@MetricRegistry.register("loop_detection")
class LoopDetection(EvalForgeMetric):
    """Detects infinite loops, cyclic tool calls, and repetitive action patterns in agent execution trajectories."""

    name: str = "loop_detection"
    category: MetricCategory = MetricCategory.AGENT
    source: MetricSource = MetricSource.CUSTOM
    version: str = "1.0.0"

    def __init__(self, threshold: float = 1.0, max_repeat_allowed: int = 1) -> None:
        # threshold 1.0 means 0 loops detected is required to pass
        super().__init__(threshold=threshold)
        self.max_repeat_allowed = max_repeat_allowed

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.perf_counter()

        steps = test_case.trajectory or test_case.tool_calls or []
        if not steps or len(steps) < 2:
            latency = (time.perf_counter() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                threshold=self.threshold,
                reason="No loop detected (insufficient step history)",
                source=self.source,
                category=self.category,
                details={"loops_detected": 0, "repeating_signatures": []},
                cost_usd=0.0,
                latency_ms=latency,
            )

        # 1. Action signature hashing
        signatures: list[str] = []
        for step in steps:
            sig = self._extract_step_signature(step)
            signatures.append(sig)

        # 2. Detect direct consecutive repetitions and multi-step cycles (period 1 to 4)
        detected_loops: list[dict[str, Any]] = []
        n = len(signatures)

        # Check for consecutive identical calls (period = 1)
        consecutive_count = 1
        for i in range(1, n):
            if signatures[i] == signatures[i - 1]:
                consecutive_count += 1
                if consecutive_count > self.max_repeat_allowed:
                    detected_loops.append(
                        {
                            "type": "consecutive_repeat",
                            "index": i,
                            "signature": signatures[i][:60],
                            "repeat_count": consecutive_count,
                        }
                    )
            else:
                consecutive_count = 1

        # Check for cycle periods (period k in [2, 3, 4])
        for period in [2, 3, 4]:
            if n >= period * 2:
                for i in range(n - period * 2 + 1):
                    window1 = signatures[i : i + period]
                    window2 = signatures[i + period : i + period * 2]
                    if window1 == window2:
                        detected_loops.append(
                            {
                                "type": f"cyclic_pattern_period_{period}",
                                "start_index": i,
                                "pattern": [s[:40] for s in window1],
                            }
                        )

        total_loops = len(detected_loops)
        if total_loops == 0:
            score = 1.0
            passed = True
            reason = "No loops or repeating patterns detected in trajectory."
        else:
            # Score penalizes loops proportionally
            score = max(0.0, 1.0 - (total_loops * 0.4))
            passed = score >= self.threshold
            reason = f"Detected {total_loops} repeating loop patterns in agent actions."

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
                "total_steps": n,
                "loops_detected": total_loops,
                "loop_details": detected_loops,
            },
            cost_usd=0.0,
            latency_ms=latency,
        )

    def _extract_step_signature(self, step: dict[str, Any] | Any) -> str:
        if isinstance(step, dict):
            # Extract key identifying parts: tool_name / action, and parameters
            action_name = step.get("name") or step.get("tool") or step.get("action") or "unknown"
            args = step.get("arguments") or step.get("args") or step.get("parameters") or {}
            serialized = f"{action_name}:{json.dumps(args, sort_keys=True, default=str)}"
        else:
            serialized = str(step)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
