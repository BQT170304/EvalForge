"""Comprehensive unit tests for heuristic NLP metrics in EvalForge."""

import pytest

from evalforge.engine.base import EvalTestCase
from evalforge.engine.metrics.heuristic.bleu_score import BLEUScore
from evalforge.engine.metrics.heuristic.rouge_score import ROUGEScore


@pytest.mark.asyncio
async def test_bleu_score_exact_match():
    metric = BLEUScore(threshold=0.8)
    test_case = EvalTestCase(
        input="Translate",
        output="The quick brown fox jumps over the lazy dog",
        expected_output="The quick brown fox jumps over the lazy dog",
    )
    result = await metric.evaluate(test_case)
    assert result.score > 0.9
    assert result.passed is True


@pytest.mark.asyncio
async def test_bleu_score_missing_expected():
    metric = BLEUScore()
    test_case = EvalTestCase(input="Translate", output="Some output")
    result = await metric.evaluate(test_case)
    assert result.score == 0.0
    assert result.passed is False
    assert "Missing expected_output" in result.reason


@pytest.mark.asyncio
async def test_rouge_score():
    metric = ROUGEScore(variant="rougeL", threshold=0.5)
    test_case = EvalTestCase(
        input="Summarize",
        output="AI evaluation systems measure correctness and safety.",
        expected_output="AI evaluation frameworks evaluate correctness and safety in LLMs.",
    )
    result = await metric.evaluate(test_case)
    assert result.score > 0.5
    assert result.passed is True
    assert "rouge1" in result.details
