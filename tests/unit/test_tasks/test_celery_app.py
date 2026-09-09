"""Tests for Celery worker observability init hook."""

from evalforge.tasks.celery_app import _init_worker_observability


def test_init_worker_observability_runs_without_error():
    _init_worker_observability()
