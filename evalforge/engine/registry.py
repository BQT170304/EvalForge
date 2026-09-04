from collections.abc import Callable
from typing import Any, ClassVar, TypeVar

import structlog

from .base import EvalForgeMetric

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=EvalForgeMetric)


class MetricRegistry:
    _instance: "MetricRegistry | None" = None
    _metrics: ClassVar[dict[str, type[EvalForgeMetric]]] = {}

    def __new__(cls) -> "MetricRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, name: str) -> Callable[[type[T]], type[T]]:
        def decorator(metric_class: type[T]) -> type[T]:
            if name in cls._metrics:
                logger.warning(f"Metric {name} is already registered. Overwriting.")
            cls._metrics[name] = metric_class
            metric_class.name = name  # Ensure the class knows its registered name
            return metric_class

        return decorator

    @classmethod
    def get(cls, name: str) -> type[EvalForgeMetric] | None:
        return cls._metrics.get(name)

    @classmethod
    def list_all(cls) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "category": metric_class.category.value
                if hasattr(metric_class, "category")
                else None,
                "source": metric_class.source.value if hasattr(metric_class, "source") else None,
                "version": getattr(metric_class, "version", "1.0.0"),
                "default_threshold": getattr(metric_class, "threshold", 0.5),
            }
            for name, metric_class in cls._metrics.items()
        }

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> EvalForgeMetric:
        metric_class = cls.get(name)
        if not metric_class:
            raise ValueError(f"Metric '{name}' not found in registry.")
        return metric_class(**kwargs)
