"""Global test fixtures and database overrides."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from evalforge.api.deps import get_db_session
from evalforge.main import app


@pytest.fixture(autouse=True)
def override_db_session():
    """Overrides get_db_session dependency with a mock AsyncSession for fast, isolated API tests."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    async def _mock_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield mock_session

    app.dependency_overrides[get_db_session] = _mock_get_db
    yield
    app.dependency_overrides.pop(get_db_session, None)
