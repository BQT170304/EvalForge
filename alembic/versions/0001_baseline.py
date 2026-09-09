"""baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-04

Snapshot of evalforge.models.db at the time Alembic was introduced.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_table(
        "datasets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schema_version", sa.String(length=50), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("entry_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_datasets_name"), "datasets", ["name"], unique=False)
    op.create_index("ix_datasets_name_version", "datasets", ["name", "version"], unique=True)
    op.create_table(
        "dataset_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("input", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column("trajectory", postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_dataset_entries_dataset_id"), "dataset_entries", ["dataset_id"], unique=False
    )
    op.create_table(
        "experiments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("dataset_version", sa.String(length=50), nullable=False),
        sa.Column("metrics_config", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("judge_model", sa.String(length=100), nullable=False),
        sa.Column("target_model", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("pass_rate", sa.Float(), nullable=True),
        sa.Column("summary_scores", postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column("total_cost_usd", sa.Float(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("total_entries", sa.Integer(), nullable=False),
        sa.Column("passed_entries", sa.Integer(), nullable=False),
        sa.Column("failed_entries", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_experiments_dataset_id"), "experiments", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_experiments_name"), "experiments", ["name"], unique=False)
    op.create_index(op.f("ix_experiments_status"), "experiments", ["status"], unique=False)
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("experiment_id", sa.UUID(), nullable=True),
        sa.Column("trace_id", sa.String(length=255), nullable=True),
        sa.Column("source_service", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("input", sa.Text(), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("overall_passed", sa.Boolean(), nullable=True),
        sa.Column("average_score", sa.Float(), nullable=True),
        sa.Column("total_cost_usd", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_runs_experiment_id"), "evaluation_runs", ["experiment_id"], unique=False
    )
    op.create_index(op.f("ix_evaluation_runs_status"), "evaluation_runs", ["status"], unique=False)
    op.create_index(
        op.f("ix_evaluation_runs_trace_id"), "evaluation_runs", ["trace_id"], unique=False
    )
    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_results_metric_name"),
        "evaluation_results",
        ["metric_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_results_run_id"), "evaluation_results", ["run_id"], unique=False
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_index(op.f("ix_evaluation_results_run_id"), table_name="evaluation_results")
    op.drop_index(op.f("ix_evaluation_results_metric_name"), table_name="evaluation_results")
    op.drop_table("evaluation_results")
    op.drop_index(op.f("ix_evaluation_runs_trace_id"), table_name="evaluation_runs")
    op.drop_index(op.f("ix_evaluation_runs_status"), table_name="evaluation_runs")
    op.drop_index(op.f("ix_evaluation_runs_experiment_id"), table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
    op.drop_index(op.f("ix_experiments_status"), table_name="experiments")
    op.drop_index(op.f("ix_experiments_name"), table_name="experiments")
    op.drop_index(op.f("ix_experiments_dataset_id"), table_name="experiments")
    op.drop_table("experiments")
    op.drop_index(op.f("ix_dataset_entries_dataset_id"), table_name="dataset_entries")
    op.drop_table("dataset_entries")
    op.drop_index("ix_datasets_name_version", table_name="datasets")
    op.drop_index(op.f("ix_datasets_name"), table_name="datasets")
    op.drop_table("datasets")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
    # ### end Alembic commands ###
