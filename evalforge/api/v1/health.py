"""Health check and system status endpoints."""

from fastapi import APIRouter

from evalforge import __version__
from evalforge.config import get_settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check")
async def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "healthy",
        "service": settings.project_name,
        "version": __version__,
        "environment": settings.env.value,
    }
