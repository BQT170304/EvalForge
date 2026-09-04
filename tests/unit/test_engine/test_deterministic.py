"""Comprehensive unit tests for deterministic metrics in EvalForge."""

import pytest

from evalforge.engine.base import EvalTestCase
from evalforge.engine.metrics.deterministic.cost_checker import CostChecker
from evalforge.engine.metrics.deterministic.json_schema import JsonSchemaValidator
from evalforge.engine.metrics.deterministic.latency_checker import LatencyChecker
from evalforge.engine.metrics.deterministic.length_checker import LengthChecker
from evalforge.engine.metrics.deterministic.regex_matcher import RegexMatcher


@pytest.mark.asyncio
async def test_json_schema_validator_success():
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        "required": ["name", "age"],
    }
    validator = JsonSchemaValidator(schema=schema)
    test_case = EvalTestCase(input="Give me user JSON", output='{"name": "Alice", "age": 30}')
    result = await validator.evaluate(test_case)
    assert result.score == 1.0
    assert result.passed is True


@pytest.mark.asyncio
async def test_json_schema_validator_failure():
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        "required": ["name", "age"],
    }
    validator = JsonSchemaValidator(schema=schema)
    test_case = EvalTestCase(input="Give me user JSON", output='{"name": "Alice"}')
    result = await validator.evaluate(test_case)
    assert result.score == 0.0
    assert result.passed is False
    assert "error" in result.details


@pytest.mark.asyncio
async def test_regex_matcher():
    patterns = [r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", r"verified"]
    matcher = RegexMatcher(patterns=patterns, match_mode="all")
    test_case = EvalTestCase(
        input="Send confirmation",
        output="Sent confirmation to test@example.com, status is verified.",
    )
    result = await matcher.evaluate(test_case)
    assert result.score == 1.0
    assert result.passed is True


@pytest.mark.asyncio
async def test_length_checker():
    checker = LengthChecker(min_length=10, max_length=50)
    test_case = EvalTestCase(input="Summary", output="This is a brief summary of the text.")
    result = await checker.evaluate(test_case)
    assert result.score == 1.0
    assert result.passed is True


@pytest.mark.asyncio
async def test_latency_checker():
    checker = LatencyChecker(max_latency_ms=1000.0)
    test_case = EvalTestCase(input="Query", output="Answer", latency_ms=250.0)
    result = await checker.evaluate(test_case)
    assert result.score == 0.75
    assert result.passed is True


@pytest.mark.asyncio
async def test_cost_checker():
    checker = CostChecker(max_cost_usd=0.05)
    test_case = EvalTestCase(input="Query", output="Answer", cost_usd=0.01)
    result = await checker.evaluate(test_case)
    assert result.score == 0.8
    assert result.passed is True
