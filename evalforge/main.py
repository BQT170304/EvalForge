"""FastAPI application entry point.

Creates and configures the FastAPI application with middleware,
exception handlers, and API routes.
"""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from evalforge import __version__
from evalforge.api.v1.router import api_v1_router
from evalforge.config import get_settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    settings = get_settings()
    logger.info(
        "Starting EvalForge",
        version=__version__,
        env=settings.env.value,
        debug=settings.debug,
    )
    yield
    logger.info("Shutting down EvalForge")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.project_name,
        description=(
            "Production-grade AI/LLM/Agent Evaluation Service. "
            "Evaluates LLM outputs using deterministic checks, heuristic metrics, "
            "LLM-as-a-Judge (via DeepEval), RAG metrics (via RAGAS), "
            "and custom agent cooperation metrics."
        ),
        version=__version__,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # --- Middleware ---

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request timing middleware
    @app.middleware("http")
    async def add_timing_header(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        start_time = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        return response

    # --- Exception Handlers ---

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred." if not settings.debug else str(exc),
            },
        )

    # --- Routes ---
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    # --- Frontend SPA Static Mount ---
    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        assets_dir = frontend_dist / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        api_prefix = settings.api_v1_prefix.lstrip("/")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str) -> Response:
            if full_path.startswith(api_prefix):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            target = frontend_dist / full_path
            if target.is_file():
                return FileResponse(str(target))
            index_file = frontend_dist / "index.html"
            if index_file.is_file():
                return FileResponse(str(index_file))
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

    return app


# Application instance for uvicorn
app = create_app()
