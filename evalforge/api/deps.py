"""FastAPI dependencies and middleware utilities."""

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from evalforge.config import Settings, get_settings
from evalforge.db.session import get_db_session

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

__all__ = ["get_db_session", "verify_api_key"]


async def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_header)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> str:
    """Verify that incoming request provides a valid API Key.

    Bypassed in development mode if debug=True or default dev key is matched.
    """
    if settings.is_development and not api_key:
        return "dev-user"

    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Provide a valid 'X-API-Key' header.",
        )
    return api_key
