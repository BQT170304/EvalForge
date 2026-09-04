"""Metrics catalog endpoint for discovering available evaluation metrics."""

from fastapi import APIRouter

import evalforge.engine.metrics  # noqa: F401
from evalforge.engine.registry import MetricRegistry
from evalforge.models.schemas import MetricInfo

router = APIRouter(tags=["Metrics"])


@router.get(
    "/metrics",
    response_model=list[MetricInfo],
    summary="List all available evaluation metrics",
    description="Returns metadata for all registered metrics across deterministic, heuristic, LLM-as-a-judge, RAG, agent, and safety categories.",
)
async def list_metrics() -> list[MetricInfo]:
    registry = MetricRegistry()
    registered = registry.list_all()

    metric_list: list[MetricInfo] = []
    for name, meta in registered.items():
        metric_list.append(
            MetricInfo(
                name=name,
                category=str(meta.get("category", "DETERMINISTIC")),
                source=str(meta.get("source", "BUILTIN")),
                default_threshold=float(meta.get("default_threshold", 0.5)),
                description=str(meta.get("description", f"Evaluation metric: {name}")),
                requires_context=bool(meta.get("requires_context", False)),
                requires_expected_output=bool(meta.get("requires_expected_output", False)),
                requires_tools=bool(meta.get("requires_tools", False)),
            )
        )
    return metric_list
