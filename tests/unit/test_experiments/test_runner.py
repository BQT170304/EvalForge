"""Unit tests for experiment comparator and reporter."""

import uuid

from evalforge.models.db import (
    ExperimentModel,
    ExperimentStatus,
)


def test_experiment_models_structure():
    exp_id = uuid.uuid4()
    dataset_id = uuid.uuid4()
    exp = ExperimentModel(
        id=exp_id,
        name="baseline_run",
        dataset_id=dataset_id,
        dataset_version="1.0.0",
        metrics_config=[{"name": "bleu_score", "threshold": 0.7}],
        status=ExperimentStatus.COMPLETED.value,
        pass_rate=0.85,
        total_entries=10,
        passed_entries=8,
        failed_entries=2,
        total_cost_usd=0.02,
    )
    assert exp.id == exp_id
    assert exp.name == "baseline_run"
    assert exp.pass_rate == 0.85
