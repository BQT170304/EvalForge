"""Integration tests for Phase 2 API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from evalforge.main import app


@pytest.mark.asyncio
async def test_list_metrics_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/metrics")
        assert response.status_code == 200
        metrics = response.json()
        assert len(metrics) >= 10
        metric_names = [m["name"] for m in metrics]

        # Verify deterministic metrics
        assert "json_schema_validator" in metric_names or "JsonSchemaValidator" in metric_names
        # Verify heuristic metrics
        assert "BLEUScore" in metric_names or "bleu_score" in metric_names
        # Verify agent metrics
        assert "task_completion" in metric_names
        assert "loop_detection" in metric_names
        assert "coordination_overhead" in metric_names
        # Verify safety metrics
        assert "prompt_injection_resistance" in metric_names
        assert "pii_leakage" in metric_names


@pytest.mark.asyncio
async def test_batch_evaluate_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "test_cases": [
                {
                    "input": "What is 2+2?",
                    "output": "4",
                    "expected_output": "4",
                    "metrics": ["length_checker"],
                },
                {
                    "input": "Summarize",
                    "output": "A brief summary sentence.",
                    "expected_output": "A brief summary sentence.",
                    "metrics": ["length_checker", "BLEUScore"],
                },
            ]
        }
        response = await client.post("/api/v1/evaluate/batch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["overall_passed"] is True
        assert data[1]["overall_passed"] is True
