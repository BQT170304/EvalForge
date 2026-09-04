"""JSON Schema validator metric."""

import json
import time
from typing import Any

import structlog
from jsonschema import Draft7Validator

from evalforge.engine.base import (
    EvalForgeMetric,
    EvalTestCase,
    MetricCategory,
    MetricResult,
    MetricSource,
)
from evalforge.engine.registry import MetricRegistry

logger = structlog.get_logger(__name__)


@MetricRegistry.register("json_schema_validator")
@MetricRegistry.register("json_schema")
class JsonSchemaValidator(EvalForgeMetric):
    """Validates that the test case output is valid JSON matching a schema."""

    def __init__(
        self, schema: dict[str, Any], name: str = "json_schema_validator", threshold: float = 1.0
    ):
        super().__init__(
            name=name,
            category=MetricCategory.DETERMINISTIC,
            source=MetricSource.BUILTIN,
            threshold=threshold,
        )
        self.schema = schema

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.perf_counter()
        score = 0.0
        reason = ""
        details: dict[str, Any] = {}

        try:
            if not test_case.output:
                raise ValueError("Test case output is empty.")

            output_obj = json.loads(test_case.output)

            validator = Draft7Validator(self.schema)
            errors = sorted(validator.iter_errors(output_obj), key=lambda e: e.path)

            if not errors:
                score = 1.0
                reason = "Output is valid JSON and matches the schema."
            else:
                score = 0.0
                reason = f"Output failed schema validation with {len(errors)} errors."
                details["errors"] = [e.message for e in errors]
                details["error"] = errors[0].message if errors else reason

        except json.JSONDecodeError as e:
            score = 0.0
            reason = f"Failed to parse output as JSON: {e!s}"
            details["error"] = "JSONDecodeError"
        except Exception as e:
            score = 0.0
            reason = f"Unexpected error during validation: {e!s}"
            logger.exception("JSON schema validation failed", error=str(e))
            details["error"] = str(e)

        latency_ms = (time.perf_counter() - start_time) * 1000

        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=score >= self.threshold,
            threshold=self.threshold,
            reason=reason,
            source=self.source,
            details=details,
            cost_usd=0.0,
            latency_ms=latency_ms,
        )
