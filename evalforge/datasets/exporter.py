"""Dataset exporter supporting CSV, JSONL, and JSON formats."""

import csv
import io
import json
from typing import Literal

from evalforge.models.db import DatasetModel


class DatasetExporter:
    """Serializes dataset entries into common distribution formats."""

    @classmethod
    def export(cls, dataset: DatasetModel, format: Literal["json", "jsonl", "csv"] = "json") -> str:
        """Exports dataset entries in the requested format."""
        if format == "jsonl":
            return cls.to_jsonl(dataset)
        elif format == "csv":
            return cls.to_csv(dataset)
        return cls.to_json(dataset)

    @staticmethod
    def to_json(dataset: DatasetModel) -> str:
        data = {
            "name": dataset.name,
            "version": dataset.version,
            "description": dataset.description,
            "entry_count": len(dataset.entries),
            "entries": [
                {
                    "input": e.input,
                    "expected_output": e.expected_output,
                    "context": e.context,
                    "metadata": e.metadata_,
                    "tool_calls": e.tool_calls,
                    "trajectory": e.trajectory,
                }
                for e in dataset.entries
            ],
        }
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def to_jsonl(dataset: DatasetModel) -> str:
        lines = []
        for e in dataset.entries:
            row = {
                "input": e.input,
                "expected_output": e.expected_output,
                "context": e.context,
                "metadata": e.metadata_,
                "tool_calls": e.tool_calls,
                "trajectory": e.trajectory,
            }
            lines.append(json.dumps(row, default=str))
        return "\n".join(lines)

    @staticmethod
    def to_csv(dataset: DatasetModel) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["input", "expected_output", "context", "metadata"],
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for e in dataset.entries:
            writer.writerow(
                {
                    "input": e.input,
                    "expected_output": e.expected_output or "",
                    "context": json.dumps(e.context or []),
                    "metadata": json.dumps(e.metadata_ or {}),
                }
            )
        return output.getvalue()
