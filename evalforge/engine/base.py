from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MetricCategory(StrEnum):
    DETERMINISTIC = "DETERMINISTIC"
    HEURISTIC = "HEURISTIC"
    LLM_JUDGE = "LLM_JUDGE"
    RAG = "RAG"
    AGENT = "AGENT"
    SAFETY = "SAFETY"


class MetricSource(StrEnum):
    DEEPEVAL = "DEEPEVAL"
    RAGAS = "RAGAS"
    CUSTOM = "CUSTOM"
    BUILTIN = "BUILTIN"


@dataclass
class EvalTestCase:
    input: str
    output: str
    expected_output: str | None = None
    context: list[str] | None = None
    metadata: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    trajectory: list[dict[str, Any]] | None = None
    latency_ms: float | None = None
    cost_usd: float | None = None


@dataclass
class MetricResult:
    metric_name: str
    score: float
    passed: bool
    threshold: float
    reason: str
    source: MetricSource
    category: MetricCategory = MetricCategory.DETERMINISTIC
    details: dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    latency_ms: float = 0.0


class EvalForgeMetric(ABC):
    name: str = ""
    category: MetricCategory = MetricCategory.DETERMINISTIC
    source: MetricSource = MetricSource.BUILTIN
    threshold: float = 0.5
    version: str = "1.0.0"

    def __init__(self, threshold: float | None = None, **kwargs: Any) -> None:
        if threshold is not None:
            self.threshold = threshold
        self.config: dict[str, Any] = kwargs

    @abstractmethod
    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        pass

    def is_successful(self, result: MetricResult) -> bool:
        return result.passed


class EvaluationRequest(BaseModel):
    test_cases: list[dict[str, Any]] = Field(
        ..., description="List of raw test cases to parse into EvalTestCase"
    )
    metrics: list[str] = Field(..., description="List of metric names to evaluate against")
    config: dict[str, Any] | None = Field(
        default_factory=dict, description="Configuration overrides"
    )


class EvaluationResponse(BaseModel):
    results: list[list[dict[str, Any]]] = Field(
        ..., description="Matrix of results [test_cases][metrics]"
    )
    total_cost_usd: float = Field(0.0, description="Total cost of the evaluation")
    total_latency_ms: float = Field(0.0, description="Total latency of the evaluation")
    summary: dict[str, Any] = Field(default_factory=dict, description="Aggregated summary")
