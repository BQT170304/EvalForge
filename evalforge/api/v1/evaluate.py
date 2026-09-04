"""Evaluation endpoints for submitting single and batch evaluation runs."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from evalforge.api.deps import get_db_session, verify_api_key
from evalforge.engine.base import EvalTestCase
from evalforge.engine.orchestrator import EvaluationOrchestrator
from evalforge.models.db import EvaluationResultModel, EvaluationRunModel, EvaluationStatus
from evalforge.models.schemas import (
    BatchEvaluationRequest,
    EvaluationResponse,
    MetricScoreResponse,
    SingleEvaluationRequest,
)

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Evaluations"])


@router.post(
    "/evaluate",
    response_model=EvaluationResponse,
    summary="Evaluate a single LLM output",
    description="Synchronously evaluate an LLM output across specified metrics and return comprehensive scores.",
)
async def evaluate_single(
    request: SingleEvaluationRequest,
    api_key: Annotated[str, Depends(verify_api_key)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> EvaluationResponse:
    orchestrator = EvaluationOrchestrator()

    # Convert API request to internal EvalTestCase
    test_case = EvalTestCase(
        input=request.input,
        output=request.output,
        expected_output=request.expected_output,
        context=request.context,
        metadata=request.metadata,
    )

    eval_run_id = uuid.uuid4()
    logger.info("Starting single evaluation", eval_id=str(eval_run_id), metrics=request.metrics)

    # Execute metrics in parallel
    metric_results = await orchestrator.evaluate(
        test_case=test_case,
        metrics=request.metrics,
        thresholds=request.thresholds,
        parameters=request.parameters,
    )

    # Compute aggregates
    total_cost = sum(r.cost_usd for r in metric_results)
    total_latency = sum(r.latency_ms for r in metric_results)
    overall_passed = all(r.passed for r in metric_results) if metric_results else False
    avg_score = (
        sum(r.score for r in metric_results) / len(metric_results) if metric_results else 0.0
    )

    now = datetime.now(UTC)

    # Save to database
    run_model = EvaluationRunModel(
        id=eval_run_id,
        trace_id=request.trace_id,
        source_service=request.source_service,
        status=EvaluationStatus.COMPLETED.value,
        input=request.input,
        output=request.output,
        expected_output=request.expected_output,
        context=request.context,
        metadata_=request.metadata or {},
        overall_passed=overall_passed,
        average_score=avg_score,
        total_cost_usd=total_cost,
        latency_ms=total_latency,
        created_at=now,
        completed_at=now,
    )
    db.add(run_model)

    results_response: list[MetricScoreResponse] = []
    for res in metric_results:
        res_model = EvaluationResultModel(
            run_id=eval_run_id,
            metric_name=res.metric_name,
            category=res.category.value if hasattr(res.category, "value") else str(res.category),
            source=res.source.value if hasattr(res.source, "value") else str(res.source),
            score=res.score,
            passed=res.passed,
            threshold=res.threshold,
            reason=res.reason,
            details=res.details,
            cost_usd=res.cost_usd,
            latency_ms=res.latency_ms,
            created_at=now,
        )
        db.add(res_model)

        results_response.append(
            MetricScoreResponse(
                metric_name=res.metric_name,
                category=res.category.value
                if hasattr(res.category, "value")
                else str(res.category),
                source=res.source.value if hasattr(res.source, "value") else str(res.source),
                score=res.score,
                passed=res.passed,
                threshold=res.threshold,
                reason=res.reason,
                details=res.details,
                cost_usd=res.cost_usd,
                latency_ms=res.latency_ms,
            )
        )

    await db.flush()

    return EvaluationResponse(
        eval_id=eval_run_id,
        status=EvaluationStatus.COMPLETED.value,
        overall_passed=overall_passed,
        average_score=avg_score,
        total_cost_usd=total_cost,
        latency_ms=total_latency,
        results=results_response,
        metadata=request.metadata or {},
        created_at=now,
    )


@router.get(
    "/evaluate/{eval_id}",
    response_model=EvaluationResponse,
    summary="Get evaluation results by ID",
)
async def get_evaluation_result(
    eval_id: uuid.UUID,
    api_key: Annotated[str, Depends(verify_api_key)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> EvaluationResponse:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = (
        select(EvaluationRunModel)
        .where(EvaluationRunModel.id == eval_id)
        .options(selectinload(EvaluationRunModel.results))
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run with ID {eval_id} not found",
        )

    return EvaluationResponse(
        eval_id=run.id,
        status=run.status,
        overall_passed=run.overall_passed or False,
        average_score=run.average_score or 0.0,
        total_cost_usd=run.total_cost_usd,
        latency_ms=run.latency_ms,
        results=[
            MetricScoreResponse(
                metric_name=r.metric_name,
                category=r.category,
                source=r.source,
                score=r.score,
                passed=r.passed,
                threshold=r.threshold,
                reason=r.reason,
                details=r.details,
                cost_usd=r.cost_usd,
                latency_ms=r.latency_ms,
            )
            for r in run.results
        ],
        metadata=run.metadata_,
        created_at=run.created_at,
    )


@router.post(
    "/evaluate/batch",
    response_model=list[EvaluationResponse],
    summary="Evaluate a batch of test cases",
    description="Evaluates multiple test cases in parallel across specified metrics.",
)
async def evaluate_batch(
    payload: BatchEvaluationRequest,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> list[EvaluationResponse]:
    responses: list[EvaluationResponse] = []
    for tc_request in payload.test_cases:
        resp = await evaluate_single(request=tc_request, api_key=api_key, db=db)
        responses.append(resp)
    return responses
