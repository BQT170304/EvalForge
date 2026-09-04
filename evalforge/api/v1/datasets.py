"""Dataset management API routes."""

import uuid
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from evalforge.api.deps import get_db_session, verify_api_key
from evalforge.datasets.exporter import DatasetExporter
from evalforge.datasets.generator import SyntheticDataGenerator
from evalforge.datasets.importer import DatasetImporter
from evalforge.datasets.manager import DatasetManager
from evalforge.models.schemas import (
    DatasetCreate,
    DatasetEntryCreate,
    DatasetEntryResponse,
    DatasetResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/datasets", tags=["Datasets"])


class SyntheticGenerateRequest(BaseModel):
    domain_description: str = Field(
        ..., description="Overview of the application or evaluation domain"
    )
    num_samples: int = Field(5, ge=1, le=50, description="Number of synthetic samples to create")
    context_docs: list[str] | None = Field(None, description="Optional knowledge context chunks")
    seed_examples: list[dict[str, str]] | None = Field(
        None, description="Optional seed prompt examples"
    )


class VersionSnapshotRequest(BaseModel):
    new_version: str = Field(..., description="Target semantic version string (e.g. 1.1.0)")
    description: str | None = Field(None, description="Snapshot note or changelog")


@router.post(
    "",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new dataset",
)
async def create_dataset(
    payload: DatasetCreate,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> DatasetResponse:
    manager = DatasetManager(db)
    initial_entries = [e.model_dump() for e in payload.entries] if payload.entries else None

    dataset = await manager.create_dataset(
        name=payload.name,
        description=payload.description,
        version=payload.version,
        tags=payload.tags,
        metadata=payload.metadata,
        initial_entries=initial_entries,
    )
    return DatasetResponse(
        id=dataset.id,
        name=dataset.name,
        version=dataset.version,
        description=dataset.description,
        schema_version=dataset.schema_version,
        tags=dataset.tags,
        entry_count=dataset.entry_count,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


@router.get(
    "",
    response_model=list[DatasetResponse],
    summary="List all evaluation datasets",
)
async def list_datasets(
    tag: str | None = Query(None, description="Filter by tag"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> list[DatasetResponse]:
    manager = DatasetManager(db)
    datasets = await manager.list_datasets(tag=tag, limit=limit, offset=offset)
    return [
        DatasetResponse(
            id=d.id,
            name=d.name,
            version=d.version,
            description=d.description,
            schema_version=d.schema_version,
            tags=d.tags,
            entry_count=d.entry_count,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in datasets
    ]


@router.get(
    "/{dataset_id}",
    summary="Get dataset details and test cases",
)
async def get_dataset(
    dataset_id: uuid.UUID,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id, include_entries=True)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    return {
        "id": dataset.id,
        "name": dataset.name,
        "version": dataset.version,
        "description": dataset.description,
        "schema_version": dataset.schema_version,
        "tags": dataset.tags,
        "entry_count": dataset.entry_count,
        "metadata": dataset.metadata_,
        "created_at": dataset.created_at,
        "updated_at": dataset.updated_at,
        "entries": [
            {
                "id": e.id,
                "input": e.input,
                "expected_output": e.expected_output,
                "context": e.context,
                "metadata": e.metadata_,
                "tool_calls": e.tool_calls,
                "trajectory": e.trajectory,
                "created_at": e.created_at,
            }
            for e in dataset.entries
        ],
    }


@router.post(
    "/{dataset_id}/entries",
    response_model=list[DatasetEntryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add test cases to an existing dataset",
)
async def add_dataset_entries(
    dataset_id: uuid.UUID,
    entries: list[DatasetEntryCreate],
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> list[DatasetEntryResponse]:
    manager = DatasetManager(db)
    entries_data = [e.model_dump() for e in entries]
    try:
        created = await manager.add_entries(dataset_id, entries_data)
        return [
            DatasetEntryResponse(
                id=c.id,
                dataset_id=c.dataset_id,
                input=c.input,
                expected_output=c.expected_output,
                context=c.context,
                metadata=c.metadata_,
                created_at=c.created_at,
            )
            for c in created
        ]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/{dataset_id}/snapshot",
    response_model=DatasetResponse,
    summary="Create an immutable version snapshot of a dataset",
)
async def create_dataset_snapshot(
    dataset_id: uuid.UUID,
    payload: VersionSnapshotRequest,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> DatasetResponse:
    manager = DatasetManager(db)
    try:
        snapshot = await manager.create_version_snapshot(
            dataset_id=dataset_id,
            new_version=payload.new_version,
            description=payload.description,
        )
        return DatasetResponse(
            id=snapshot.id,
            name=snapshot.name,
            version=snapshot.version,
            description=snapshot.description,
            schema_version=snapshot.schema_version,
            tags=snapshot.tags,
            entry_count=snapshot.entry_count,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/{dataset_id}/generate",
    summary="Generate and append synthetic test cases using LLM",
)
async def generate_synthetic_data(
    dataset_id: uuid.UUID,
    payload: SyntheticGenerateRequest,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    generator = SyntheticDataGenerator()
    try:
        cases = await generator.generate_test_cases(
            domain_description=payload.domain_description,
            num_samples=payload.num_samples,
            context_docs=payload.context_docs,
            seed_examples=payload.seed_examples,
        )
        manager = DatasetManager(db)
        created = await manager.add_entries(dataset_id, cases)
        return {
            "generated_count": len(created),
            "dataset_id": str(dataset_id),
            "entries_added": [str(c.id) for c in created],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synthetic generation failed: {e!s}",
        ) from e


@router.post(
    "/import",
    response_model=DatasetResponse,
    summary="Import dataset from CSV, JSON, or JSONL file",
)
async def import_dataset(
    file: UploadFile = File(...),
    name: str = Query(..., description="Dataset name"),
    version: str = Query("1.0.0", description="Dataset initial version"),
    description: str | None = Query(None, description="Dataset description"),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> DatasetResponse:
    content = await file.read()
    filename = file.filename or "data.json"

    if filename.endswith(".jsonl"):
        entries = DatasetImporter.import_from_jsonl(content)
    elif filename.endswith(".csv"):
        entries = DatasetImporter.import_from_csv(content)
    else:
        entries = DatasetImporter.import_from_json(content)

    manager = DatasetManager(db)
    dataset = await manager.create_dataset(
        name=name,
        version=version,
        description=description or f"Imported from {filename}",
        initial_entries=entries,
    )
    return DatasetResponse(
        id=dataset.id,
        name=dataset.name,
        version=dataset.version,
        description=dataset.description,
        schema_version=dataset.schema_version,
        tags=dataset.tags,
        entry_count=dataset.entry_count,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


@router.get(
    "/{dataset_id}/export",
    summary="Export dataset to JSON, JSONL, or CSV format",
)
async def export_dataset(
    dataset_id: uuid.UUID,
    format: Literal["json", "jsonl", "csv"] = Query("json", description="Export format"),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id, include_entries=True)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    content = DatasetExporter.export(dataset, format=format)

    media_types = {
        "json": "application/json",
        "jsonl": "application/x-ndjson",
        "csv": "text/csv",
    }
    return Response(
        content=content,
        media_type=media_types.get(format, "text/plain"),
        headers={
            "Content-Disposition": f'attachment; filename="{dataset.name}_v{dataset.version}.{format}"'
        },
    )
