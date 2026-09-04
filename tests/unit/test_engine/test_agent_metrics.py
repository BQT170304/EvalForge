"""Unit tests for agent and multi-agent cooperation metrics in EvalForge."""

import pytest

from evalforge.engine.base import EvalTestCase
from evalforge.engine.metrics.agent.coordination_failure import CoordinationFailureRate
from evalforge.engine.metrics.agent.coordination_overhead import CoordinationOverhead
from evalforge.engine.metrics.agent.knowledge_alignment import KnowledgeAlignment
from evalforge.engine.metrics.agent.loop_detection import LoopDetection
from evalforge.engine.metrics.agent.task_completion import TaskCompletionRate
from evalforge.engine.metrics.agent.trajectory import TrajectoryOptimality


@pytest.mark.asyncio
async def test_loop_detection_no_loops():
    metric = LoopDetection()
    test_case = EvalTestCase(
        input="Search query",
        output="Result",
        trajectory=[
            {"name": "search_db", "args": {"query": "weather"}},
            {"name": "format_weather", "args": {"temp": 22}},
        ],
    )
    result = await metric.evaluate(test_case)
    assert result.score == 1.0
    assert result.passed is True
    assert result.details["loops_detected"] == 0


@pytest.mark.asyncio
async def test_loop_detection_consecutive_repeats():
    metric = LoopDetection(threshold=0.9, max_repeat_allowed=1)
    test_case = EvalTestCase(
        input="Search query",
        output="Stuck in loop",
        trajectory=[
            {"name": "search_db", "args": {"query": "weather"}},
            {"name": "search_db", "args": {"query": "weather"}},
            {"name": "search_db", "args": {"query": "weather"}},
        ],
    )
    result = await metric.evaluate(test_case)
    assert result.score < 0.9
    assert result.passed is False
    assert result.details["loops_detected"] > 0


@pytest.mark.asyncio
async def test_coordination_overhead_zero_overhead():
    metric = CoordinationOverhead()
    test_case = EvalTestCase(
        input="Task",
        output="Result",
        metadata={},
    )
    result = await metric.evaluate(test_case)
    assert result.score == 1.0
    assert result.passed is True


@pytest.mark.asyncio
async def test_coordination_overhead_with_messages():
    metric = CoordinationOverhead(threshold=0.5, max_acceptable_messages=10)
    test_case = EvalTestCase(
        input="Task",
        output="Result",
        metadata={
            "agent_messages": ["Hello Agent B", "Task received", "Here is result"],
            "coordination_tokens": 150,
        },
    )
    result = await metric.evaluate(test_case)
    assert result.score > 0.6
    assert result.passed is True
    assert result.details["message_count"] == 3


@pytest.mark.asyncio
async def test_task_completion_exact_match():
    metric = TaskCompletionRate()
    test_case = EvalTestCase(
        input="What is 2+2?",
        output="4",
        expected_output="4",
    )
    result = await metric.evaluate(test_case)
    assert result.score == 1.0
    assert result.passed is True
    assert result.details["method"] == "exact_match"


@pytest.mark.asyncio
async def test_trajectory_optimality_direct():
    metric = TrajectoryOptimality()
    test_case = EvalTestCase(
        input="Direct question",
        output="Direct answer",
        trajectory=[],
    )
    result = await metric.evaluate(test_case)
    assert result.score == 1.0
    assert result.passed is True


@pytest.mark.asyncio
async def test_knowledge_alignment_single_agent():
    metric = KnowledgeAlignment()
    test_case = EvalTestCase(
        input="Query",
        output="Consistent response",
    )
    result = await metric.evaluate(test_case)
    assert result.score == 1.0
    assert result.passed is True


@pytest.mark.asyncio
async def test_coordination_failure_single_agent():
    metric = CoordinationFailureRate()
    test_case = EvalTestCase(
        input="Task",
        output="Result",
        trajectory=[{"name": "fetch"}],
    )
    result = await metric.evaluate(test_case)
    assert result.score == 1.0
    assert result.passed is True
