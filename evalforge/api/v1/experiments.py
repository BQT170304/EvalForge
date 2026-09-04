"""Experiment management API routes."""

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from evalforge.api.deps import get_db_session, verify_api_key
from evalforge.experiments.comparator import ExperimentComparator
from evalforge.experiments.reporter import ExperimentReporter
from evalforge.experiments.runner import ExperimentRunner
from evalforge.models.db import ExperimentModel
from evalforge.models.schemas import ExperimentCreate, ExperimentResponse
from evalforge.tasks.experiment_tasks import run_experiment_batch

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/experiments", tags=["Experiments"])


class ExperimentTriggerRequest(BaseModel):
    system_prompt: str | None = Field(
        None, description="Optional system prompt when evaluating target model"
    )
    concurrency: int = Field(5, ge=1, le=20, description="Evaluation concurrency")
    async_execution: bool = Field(
        False, description="Whether to enqueue in Celery for background processing"
    )


@router.post(
    "",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and optionally execute an experiment run",
)
async def create_and_run_experiment(
    payload: ExperimentCreate,
    trigger: bool = Query(True, description="Whether to immediately trigger execution"),
    async_execution: bool = Query(False, description="Execute via Celery worker"),
    system_prompt: str | None = Query(None, description="Optional system prompt"),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> ExperimentResponse:
    runner = ExperimentRunner(db)

    try:
        exp = await runner.create_experiment(
            name=payload.name,
            dataset_id=payload.dataset_id,
            metrics=payload.metrics,
            description=payload.description,
            thresholds=payload.thresholds,
            judge_model=payload.judge_model,
            target_model=payload.target_model,
            prompt_version=payload.prompt_version,
        )

        if trigger:
            if async_execution:
                run_experiment_batch.delay(
                    experiment_id=str(exp.id),
                    system_prompt=system_prompt,
                    concurrency=5,
                )
            else:
                exp = await runner.run_experiment(
                    experiment_id=exp.id,
                    system_prompt=system_prompt,
                    concurrency=5,
                )

        return ExperimentResponse(
            id=exp.id,
            name=exp.name,
            description=exp.description,
            dataset_id=exp.dataset_id,
            dataset_version=exp.dataset_version,
            status=exp.status,
            pass_rate=exp.pass_rate,
            summary_scores=exp.summary_scores,
            total_cost_usd=exp.total_cost_usd,
            duration_seconds=exp.duration_seconds,
            total_entries=exp.total_entries,
            passed_entries=exp.passed_entries,
            failed_entries=exp.failed_entries,
            created_at=exp.created_at,
            completed_at=exp.completed_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "",
    response_model=list[ExperimentResponse],
    summary="List experiment runs with filters",
)
async def list_experiments(
    dataset_id: uuid.UUID | None = Query(None, description="Filter by dataset ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> list[ExperimentResponse]:
    stmt = (
        select(ExperimentModel)
        .order_by(ExperimentModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if dataset_id:
        stmt = stmt.where(ExperimentModel.dataset_id == dataset_id)

    result = await db.execute(stmt)
    experiments = list(result.scalars().all())

    return [
        ExperimentResponse(
            id=e.id,
            name=e.name,
            description=e.description,
            dataset_id=e.dataset_id,
            dataset_version=e.dataset_version,
            status=e.status,
            pass_rate=e.pass_rate,
            summary_scores=e.summary_scores,
            total_cost_usd=e.total_cost_usd,
            duration_seconds=e.duration_seconds,
            total_entries=e.total_entries,
            passed_entries=e.passed_entries,
            failed_entries=e.failed_entries,
            created_at=e.created_at,
            completed_at=e.completed_at,
        )
        for e in experiments
    ]


@router.get(
    "/{experiment_id}",
    response_model=ExperimentResponse,
    summary="Get experiment status and summary metrics",
)
async def get_experiment(
    experiment_id: uuid.UUID,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> ExperimentResponse:
    stmt = select(ExperimentModel).where(ExperimentModel.id == experiment_id)
    result = await db.execute(stmt)
    exp = result.scalar_one_or_none()

    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )

    return ExperimentResponse(
        id=exp.id,
        name=exp.name,
        description=exp.description,
        dataset_id=exp.dataset_id,
        dataset_version=exp.dataset_version,
        status=exp.status,
        pass_rate=exp.pass_rate,
        summary_scores=exp.summary_scores,
        total_cost_usd=exp.total_cost_usd,
        duration_seconds=exp.duration_seconds,
        total_entries=exp.total_entries,
        passed_entries=exp.passed_entries,
        failed_entries=exp.failed_entries,
        created_at=exp.created_at,
        completed_at=exp.completed_at,
    )


@router.get(
    "/{baseline_id}/compare/{candidate_id}",
    summary="Compare two experiment runs for regressions and improvements",
)
async def compare_experiments(
    baseline_id: uuid.UUID,
    candidate_id: uuid.UUID,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    comparator = ExperimentComparator(db)
    try:
        return await comparator.compare(baseline_id, candidate_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/{experiment_id}/report",
    response_class=PlainTextResponse,
    summary="Get Markdown evaluation report for an experiment",
)
async def get_experiment_report(
    experiment_id: uuid.UUID,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> str:
    reporter = ExperimentReporter(db)
    try:
        return await reporter.generate_markdown_report(experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
