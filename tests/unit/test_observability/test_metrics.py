"""Tests for observability metric instrument definitions."""

from evalforge.observability import metrics


def test_instruments_record_without_raising():
    metrics.eval_requests_total.add(1, {"metric_name": "bleu"})
    metrics.eval_latency_ms.record(12.3, {"metric_name": "bleu"})
    metrics.eval_cost_usd_total.add(0.002, {"metric_name": "llm_judge"})
    metrics.metric_failures_total.add(1, {"metric_name": "rouge"})
