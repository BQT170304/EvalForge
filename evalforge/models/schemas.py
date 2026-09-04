"""Pydantic schemas for EvalForge API request and response validation."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MetricCategoryEnum(StrEnum):
    DETERMINISTIC = "deterministic"
    HEURISTIC = "heuristic"
    LLM_JUDGE = "llm_judge"
    RAG = "rag"
    AGENT = "agent"
    SAFETY = "safety"


class MetricSourceEnum(StrEnum):
    DEEPEVAL = "deepeval"
    RAGAS = "ragas"
    CUSTOM = "custom"
    BUILTIN = "builtin"


# --- Single Evaluation Schemas ---


class SingleEvaluationRequest(BaseModel):
    """Payload for submitting a single evaluation."""

    input: str = Field(..., description="The user query or prompt")
    output: str = Field(..., description="The model output/response")
    expected_output: str | None = Field(None, description="Ground truth answer (optional)")
    context: list[str] | None = Field(None, description="Retrieved context chunks (optional)")
    metrics: list[str] = Field(..., description="List of metric names to evaluate")
    thresholds: dict[str, float] | None = Field(
        default_factory=dict, description="Custom metric thresholds"
    )
    parameters: dict[str, dict[str, Any]] | None = Field(
        default_factory=dict, description="Metric-specific parameters"
    )
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Arbitrary metadata")
    trace_id: str | None = Field(None, description="Trace ID if coming from a monitoring platform")
    source_service: str | None = Field("api", description="Source of the evaluation request")


class MetricScoreResponse(BaseModel):
    """Evaluation result for an individual metric."""

    metric_name: str
    category: str
    source: str
    score: float
    passed: bool
    threshold: float
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)
    cost_usd: float = 0.0
    latency_ms: float = 0.0


class EvaluationResponse(BaseModel):
    """Full result for an evaluation run."""

    eval_id: UUID
    status: str
    overall_passed: bool
    average_score: float
    total_cost_usd: float
    latency_ms: float
    results: list[MetricScoreResponse]
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class BatchEvaluationRequest(BaseModel):
    """Payload for evaluating multiple test cases in batch."""

    test_cases: list[SingleEvaluationRequest]
    experiment_name: str | None = None


# --- Dataset Schemas ---


class DatasetEntryCreate(BaseModel):
    input: str
    expected_output: str | None = None
    context: list[str] | None = None
    metadata: dict[str, Any] | None = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] | None = None
    trajectory: list[dict[str, Any]] | None = None


class DatasetEntryResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    input: str
    expected_output: str | None = None
    context: list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DatasetCreate(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = Field(default_factory=dict)
    entries: list[DatasetEntryCreate] | None = None


class DatasetResponse(BaseModel):
    id: UUID
    name: str
    version: str
    description: str | None
    schema_version: str
    tags: list[str]
    entry_count: int
    created_at: datetime
    updated_at: datetime


# --- Experiment Schemas ---


class ExperimentCreate(BaseModel):
    name: str
    description: str | None = None
    dataset_id: UUID
    dataset_version: str | None = None
    metrics: list[str]
    thresholds: dict[str, float] | None = Field(default_factory=dict)
    judge_model: str = "gpt-4o"
    target_model: str | None = None
    prompt_version: str | None = None


class ExperimentResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    dataset_id: UUID
    dataset_version: str
    status: str
    pass_rate: float | None
    summary_scores: dict[str, Any] | None
    total_cost_usd: float
    duration_seconds: float | None
    total_entries: int
    passed_entries: int
    failed_entries: int
    created_at: datetime
    completed_at: datetime | None


# --- Metric Info Schema ---


class MetricInfo(BaseModel):
    name: str
    category: str
    source: str
    default_threshold: float
    description: str
    requires_context: bool = False
    requires_expected_output: bool = False
    requires_tools: bool = False
