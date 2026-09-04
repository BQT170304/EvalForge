"""Evaluation reports API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from evalforge.api.deps import get_db_session, verify_api_key
from evalforge.experiments.reporter import ExperimentReporter

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/{experiment_id}",
    response_class=PlainTextResponse,
    summary="Get formatted Markdown evaluation report for an experiment",
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
