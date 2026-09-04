"""Dataset importer supporting CSV, JSONL, JSON, and Langfuse dataset formats."""

import csv
import io
import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DatasetImporter:
    """Parses and normalizes dataset files into standard EvalForge entry formats."""

    @classmethod
    def import_from_jsonl(cls, content: str | bytes) -> list[dict[str, Any]]:
        """Imports entries from a JSONL string or byte stream."""
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        entries: list[dict[str, Any]] = []
        for line_num, line in enumerate(content.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(cls._normalize_entry(data))
            except Exception as e:
                logger.warning("jsonl_import_line_error", line=line_num, error=str(e))

        return entries

    @classmethod
    def import_from_csv(cls, content: str | bytes) -> list[dict[str, Any]]:
        """Imports entries from a CSV formatted string or byte stream."""
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        f = io.StringIO(content)
        reader = csv.DictReader(f)
        entries: list[dict[str, Any]] = []

        for row in reader:
            entries.append(cls._normalize_entry(row))

        return entries

    @classmethod
    def import_from_json(cls, content: str | bytes) -> list[dict[str, Any]]:
        """Imports entries from a standard JSON array or Langfuse dataset export."""
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        data = json.loads(content)

        # Handle Langfuse export format (items: [...])
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            data = data["items"]
        elif isinstance(data, dict) and "test_cases" in data:
            data = data["test_cases"]

        if not isinstance(data, list):
            raise ValueError("Expected a JSON array of test cases")

        return [cls._normalize_entry(item) for item in data if isinstance(item, dict)]

    @classmethod
    def _normalize_entry(cls, item: dict[str, Any]) -> dict[str, Any]:
        """Normalizes diverse column naming conventions into the standard schema."""
        # Detect input
        input_text = (
            item.get("input")
            or item.get("query")
            or item.get("prompt")
            or item.get("question")
            or ""
        )

        # Detect expected output
        expected = (
            item.get("expected_output")
            or item.get("expected")
            or item.get("ground_truth")
            or item.get("answer")
            or item.get("target")
            or item.get("reference")
        )

        # Detect context
        context = item.get("context") or item.get("retrieval_context") or item.get("contexts")
        if isinstance(context, str):
            try:
                context = json.loads(context)
            except Exception:
                context = [context]
        elif context is None:
            context = []

        # Metadata
        metadata = item.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {"raw": metadata}

        return {
            "input": str(input_text),
            "expected_output": str(expected) if expected is not None else None,
            "context": context if isinstance(context, list) else [str(context)],
            "metadata": metadata if isinstance(metadata, dict) else {},
            "tool_calls": item.get("tool_calls"),
            "trajectory": item.get("trajectory"),
        }
