"""Dataset management service providing CRUD, semantic versioning, and entry querying."""

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from evalforge.models.db import DatasetEntryModel, DatasetModel

logger = structlog.get_logger(__name__)


class DatasetManager:
    """Manages evaluation datasets, version snapshots, and test case entries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_dataset(
        self,
        name: str,
        description: str | None = None,
        version: str = "1.0.0",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        initial_entries: list[dict[str, Any]] | None = None,
    ) -> DatasetModel:
        """Creates a new dataset with optional initial entries."""
        dataset_id = uuid.uuid4()
        now = datetime.now(UTC)

        dataset = DatasetModel(
            id=dataset_id,
            name=name,
            version=version,
            description=description,
            tags=tags or [],
            metadata_=metadata or {},
            entry_count=len(initial_entries) if initial_entries else 0,
            created_at=now,
            updated_at=now,
        )
        self.db.add(dataset)

        if initial_entries:
            for entry_data in initial_entries:
                entry = DatasetEntryModel(
                    id=uuid.uuid4(),
                    dataset_id=dataset_id,
                    input=entry_data["input"],
                    expected_output=entry_data.get("expected_output"),
                    context=entry_data.get("context"),
                    metadata_=entry_data.get("metadata", {}),
                    tool_calls=entry_data.get("tool_calls"),
                    trajectory=entry_data.get("trajectory"),
                    created_at=now,
                )
                self.db.add(entry)

        await self.db.flush()
        logger.info("dataset_created", dataset_id=str(dataset_id), name=name, version=version)
        return dataset

    async def get_dataset(
        self, dataset_id: uuid.UUID, include_entries: bool = True
    ) -> DatasetModel | None:
        """Retrieves dataset by ID with optional eager loading of entries."""
        stmt = select(DatasetModel).where(DatasetModel.id == dataset_id)
        if include_entries:
            stmt = stmt.options(selectinload(DatasetModel.entries))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_dataset_by_name_and_version(
        self, name: str, version: str, include_entries: bool = True
    ) -> DatasetModel | None:
        """Retrieves a dataset by name and specific version."""
        stmt = (
            select(DatasetModel)
            .where(DatasetModel.name == name)
            .where(DatasetModel.version == version)
        )
        if include_entries:
            stmt = stmt.options(selectinload(DatasetModel.entries))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_datasets(
        self, tag: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[DatasetModel]:
        """Lists datasets with optional tag filtering."""
        stmt = (
            select(DatasetModel)
            .order_by(DatasetModel.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        datasets = list(result.scalars().all())

        if tag:
            datasets = [d for d in datasets if tag in d.tags]

        return datasets

    async def add_entries(
        self, dataset_id: uuid.UUID, entries_data: list[dict[str, Any]]
    ) -> list[DatasetEntryModel]:
        """Appends new test case entries to an existing dataset."""
        dataset = await self.get_dataset(dataset_id, include_entries=False)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        now = datetime.now(UTC)
        created_entries: list[DatasetEntryModel] = []

        for ed in entries_data:
            entry = DatasetEntryModel(
                id=uuid.uuid4(),
                dataset_id=dataset_id,
                input=ed["input"],
                expected_output=ed.get("expected_output"),
                context=ed.get("context"),
                metadata_=ed.get("metadata", {}),
                tool_calls=ed.get("tool_calls"),
                trajectory=ed.get("trajectory"),
                created_at=now,
            )
            self.db.add(entry)
            created_entries.append(entry)

        # Update count and timestamp
        dataset.entry_count += len(entries_data)
        dataset.updated_at = now
        await self.db.flush()

        logger.info(
            "dataset_entries_added",
            dataset_id=str(dataset_id),
            count=len(entries_data),
            new_total=dataset.entry_count,
        )
        return created_entries

    async def create_version_snapshot(
        self, dataset_id: uuid.UUID, new_version: str, description: str | None = None
    ) -> DatasetModel:
        """Clones a dataset into a new version snapshot for immutable experiment tracking."""
        source = await self.get_dataset(dataset_id, include_entries=True)
        if not source:
            raise ValueError(f"Source dataset {dataset_id} not found")

        entries_copy = [
            {
                "input": e.input,
                "expected_output": e.expected_output,
                "context": e.context,
                "metadata": e.metadata_,
                "tool_calls": e.tool_calls,
                "trajectory": e.trajectory,
            }
            for e in source.entries
        ]

        snapshot = await self.create_dataset(
            name=source.name,
            version=new_version,
            description=description or f"Snapshot created from v{source.version}",
            tags=source.tags.copy(),
            metadata=source.metadata_.copy(),
            initial_entries=entries_copy,
        )
        return snapshot
