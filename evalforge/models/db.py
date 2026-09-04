"""Database models for EvalForge using SQLAlchemy 2.0.

Tables:
- datasets: Dataset metadata and versioning
- dataset_entries: Individual test cases within a dataset
- experiments: Experiment runs linking dataset + metrics
- evaluation_runs: Individual evaluation execution records
- evaluation_results: Metric scores for each evaluation run / entry
- api_keys: API key management for authentication
- audit_logs: Audit trail of all actions
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    type_annotation_map: ClassVar[dict[Any, Any]] = {
        dict: JSONB,
        list: JSONB,
    }


class ExperimentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvaluationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DatasetModel(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    entry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    entries: Mapped[list["DatasetEntryModel"]] = relationship(
        "DatasetEntryModel", back_populates="dataset", cascade="all, delete-orphan"
    )
    experiments: Mapped[list["ExperimentModel"]] = relationship(
        "ExperimentModel", back_populates="dataset"
    )

    __table_args__ = (Index("ix_datasets_name_version", "name", "version", unique=True),)


class DatasetEntryModel(Base):
    __tablename__ = "dataset_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    tool_calls: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    trajectory: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    dataset: Mapped["DatasetModel"] = relationship("DatasetModel", back_populates="entries")


class ExperimentModel(Base):
    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False, index=True
    )
    dataset_version: Mapped[str] = mapped_column(String(50), nullable=False)
    metrics_config: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    judge_model: Mapped[str] = mapped_column(String(100), default="gpt-4o")
    target_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=ExperimentStatus.PENDING.value, index=True
    )

    # Results summary
    pass_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_entries: Mapped[int] = mapped_column(Integer, default=0)
    passed_entries: Mapped[int] = mapped_column(Integer, default=0)
    failed_entries: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    dataset: Mapped["DatasetModel"] = relationship("DatasetModel", back_populates="experiments")
    evaluation_runs: Mapped[list["EvaluationRunModel"]] = relationship(
        "EvaluationRunModel", back_populates="experiment"
    )


class EvaluationRunModel(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_service: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=EvaluationStatus.PENDING.value, index=True
    )

    # Input/Output captured
    input: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    # Evaluation outcomes
    overall_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    average_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    experiment: Mapped[Optional["ExperimentModel"]] = relationship(
        "ExperimentModel", back_populates="evaluation_runs"
    )
    results: Mapped[list["EvaluationResultModel"]] = relationship(
        "EvaluationResultModel", back_populates="evaluation_run", cascade="all, delete-orphan"
    )


class EvaluationResultModel(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    evaluation_run: Mapped["EvaluationRunModel"] = relationship(
        "EvaluationRunModel", back_populates="results"
    )


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor: Mapped[str] = mapped_column(String(255), default="system")
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
