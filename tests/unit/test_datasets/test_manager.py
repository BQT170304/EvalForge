"""Unit tests for dataset importer, exporter, and converter."""

import json

from evalforge.datasets.converter import DatasetConverter
from evalforge.datasets.exporter import DatasetExporter
from evalforge.datasets.importer import DatasetImporter
from evalforge.models.db import DatasetEntryModel, DatasetModel


def test_import_from_jsonl():
    jsonl_content = '{"input": "What is AI?", "expected_output": "Artificial Intelligence", "context": ["CS doc"]}\n{"input": "2+2", "expected_output": "4"}'
    entries = DatasetImporter.import_from_jsonl(jsonl_content)
    assert len(entries) == 2
    assert entries[0]["input"] == "What is AI?"
    assert entries[0]["expected_output"] == "Artificial Intelligence"
    assert entries[0]["context"] == ["CS doc"]
    assert entries[1]["input"] == "2+2"


def test_import_from_csv():
    csv_content = (
        'input,expected_output,context\n"Query 1","Answer 1","[""doc""]"\n"Query 2","Answer 2","[]"'
    )
    entries = DatasetImporter.import_from_csv(csv_content)
    assert len(entries) == 2
    assert entries[0]["input"] == "Query 1"
    assert entries[0]["expected_output"] == "Answer 1"


def test_import_from_json():
    json_data = json.dumps(
        [
            {"question": "Who was Alan Turing?", "answer": "Mathematician and computer scientist."},
            {"prompt": "Calculate pi", "target": "3.14159"},
        ]
    )
    entries = DatasetImporter.import_from_json(json_data)
    assert len(entries) == 2
    assert entries[0]["input"] == "Who was Alan Turing?"
    assert entries[0]["expected_output"] == "Mathematician and computer scientist."
    assert entries[1]["input"] == "Calculate pi"
    assert entries[1]["expected_output"] == "3.14159"


def test_export_to_json_and_jsonl():
    dataset = DatasetModel(
        name="test_dataset",
        version="1.0.0",
        description="A test set",
        tags=["test"],
    )
    dataset.entries = [
        DatasetEntryModel(
            input="Test question",
            expected_output="Test answer",
            context=["Context 1"],
            metadata_={"difficulty": "easy"},
        )
    ]

    json_export = DatasetExporter.to_json(dataset)
    parsed = json.loads(json_export)
    assert parsed["name"] == "test_dataset"
    assert len(parsed["entries"]) == 1

    jsonl_export = DatasetExporter.to_jsonl(dataset)
    assert "Test question" in jsonl_export


def test_dataset_converter_entry_to_eval_test_case():
    entry = DatasetEntryModel(
        input="What is RAG?",
        expected_output="Retrieval-Augmented Generation",
        context=["RAG context"],
        metadata_={"domain": "AI"},
    )
    tc = DatasetConverter.entry_to_eval_test_case(
        entry, actual_output="RAG is Retrieval-Augmented Generation"
    )
    assert tc.input == "What is RAG?"
    assert tc.output == "RAG is Retrieval-Augmented Generation"
    assert tc.expected_output == "Retrieval-Augmented Generation"
    assert tc.context == ["RAG context"]
