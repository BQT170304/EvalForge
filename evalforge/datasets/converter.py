"""Dataset format converter for interoperability with DeepEval and RAGAS."""

from typing import Any

from deepeval.dataset import EvaluationDataset
from deepeval.test_case import LLMTestCase

from evalforge.engine.base import EvalTestCase
from evalforge.models.db import DatasetEntryModel, DatasetModel


class DatasetConverter:
    """Provides bidirectional conversion between EvalForge models and external evaluation datasets."""

    @staticmethod
    def to_deepeval_dataset(dataset: DatasetModel) -> EvaluationDataset:
        """Converts an EvalForge DatasetModel into a DeepEval EvaluationDataset."""
        test_cases: list[LLMTestCase] = []
        for entry in dataset.entries:
            tc = LLMTestCase(
                input=entry.input,
                actual_output="",  # Placeholder to be filled during evaluation
                expected_output=entry.expected_output,
                retrieval_context=entry.context,
                context=entry.context,
                additional_metadata=entry.metadata_,
            )
            test_cases.append(tc)

        return EvaluationDataset(test_cases=test_cases)

    @staticmethod
    def entry_to_eval_test_case(
        entry: DatasetEntryModel,
        actual_output: str = "",
        latency_ms: float = 0.0,
        cost_usd: float = 0.0,
    ) -> EvalTestCase:
        """Converts a DatasetEntryModel to an EvalTestCase."""
        return EvalTestCase(
            input=entry.input,
            output=actual_output,
            expected_output=entry.expected_output,
            context=entry.context,
            metadata=entry.metadata_,
            tool_calls=entry.tool_calls,
            trajectory=entry.trajectory,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
        )

    @staticmethod
    def from_deepeval_cases(test_cases: list[LLMTestCase]) -> list[dict[str, Any]]:
        """Converts a list of DeepEval LLMTestCase objects to EvalForge entry dictionaries."""
        entries: list[dict[str, Any]] = []
        for tc in test_cases:
            entries.append(
                {
                    "input": tc.input,
                    "expected_output": tc.expected_output,
                    "context": tc.retrieval_context or tc.context or [],
                    "metadata": tc.additional_metadata or {},
                }
            )
        return entries
