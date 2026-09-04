"""Result and evaluation caching layer supporting in-memory and Redis backends."""

import hashlib
import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from evalforge.config import get_settings
from evalforge.engine.base import EvalTestCase, MetricCategory, MetricResult, MetricSource

logger = structlog.get_logger(__name__)


class EvaluationCache:
    """Multi-tiered evaluation caching system (in-memory LRU with optional Redis persistence)."""

    def __init__(self, redis_url: str | None = None, ttl_seconds: int = 86400) -> None:
        self.ttl_seconds = ttl_seconds
        self._memory_cache: dict[str, dict[str, Any]] = {}
        self._max_memory_entries = 5000
        self._redis_client: aioredis.Redis | None = None
        self._redis_url = redis_url or str(get_settings().redis_url)

    async def _get_redis(self) -> aioredis.Redis | None:
        if self._redis_client is None:
            try:
                self._redis_client = aioredis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                )
                await self._redis_client.ping()
            except Exception as e:
                logger.debug("Redis cache unavailable, falling back to memory", error=str(e))
                self._redis_client = None
        return self._redis_client

    @staticmethod
    def generate_cache_key(
        metric_name: str, test_case: EvalTestCase, config: dict[str, Any] | None = None
    ) -> str:
        """Generates a deterministic SHA256 cache key based on inputs and metric parameters."""
        payload = {
            "metric": metric_name,
            "input": test_case.input,
            "output": test_case.output,
            "expected_output": test_case.expected_output,
            "context": sorted(test_case.context) if test_case.context else None,
            "config": config or {},
        }
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return f"evalcache:{hashlib.sha256(encoded).hexdigest()}"

    async def get(self, key: str) -> MetricResult | None:
        """Retrieves a cached MetricResult by key."""
        # 1. Check in-memory
        if key in self._memory_cache:
            data = self._memory_cache[key]
            return self._deserialize_result(data)

        # 2. Check Redis
        redis = await self._get_redis()
        if redis:
            try:
                cached_json = await redis.get(key)
                if cached_json:
                    data = json.loads(cached_json)
                    self._memory_cache[key] = data  # hydrate memory
                    return self._deserialize_result(data)
            except Exception as e:
                logger.debug("Redis cache read error", key=key, error=str(e))

        return None

    async def set(self, key: str, result: MetricResult) -> None:
        """Stores a MetricResult in memory and Redis."""
        data = self._serialize_result(result)

        # LRU memory eviction
        if len(self._memory_cache) >= self._max_memory_entries:
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]

        self._memory_cache[key] = data

        redis = await self._get_redis()
        if redis:
            try:
                await redis.setex(key, self.ttl_seconds, json.dumps(data, default=str))
            except Exception as e:
                logger.debug("Redis cache write error", key=key, error=str(e))

    def _serialize_result(self, result: MetricResult) -> dict[str, Any]:
        return {
            "metric_name": result.metric_name,
            "score": result.score,
            "passed": result.passed,
            "threshold": result.threshold,
            "reason": result.reason,
            "source": result.source.value
            if hasattr(result.source, "value")
            else str(result.source),
            "category": result.category.value
            if hasattr(result.category, "value")
            else str(result.category),
            "details": result.details,
            "cost_usd": result.cost_usd,
            "latency_ms": result.latency_ms,
        }

    def _deserialize_result(self, data: dict[str, Any]) -> MetricResult:
        source_val = data.get("source", MetricSource.CUSTOM.value)
        category_val = data.get("category", MetricCategory.HEURISTIC.value)
        try:
            source = MetricSource(source_val)
        except ValueError:
            source = MetricSource.CUSTOM

        try:
            category = MetricCategory(category_val)
        except ValueError:
            category = MetricCategory.HEURISTIC

        return MetricResult(
            metric_name=data["metric_name"],
            score=float(data["score"]),
            passed=bool(data["passed"]),
            threshold=float(data["threshold"]),
            reason=str(data["reason"]),
            source=source,
            category=category,
            details=data.get("details", {}),
            cost_usd=float(data.get("cost_usd", 0.0)),
            latency_ms=float(data.get("latency_ms", 0.0)),
        )


_cache_instance: EvaluationCache | None = None


def get_cache() -> EvaluationCache:
    """Get or instantiate singleton EvaluationCache."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = EvaluationCache()
    return _cache_instance
