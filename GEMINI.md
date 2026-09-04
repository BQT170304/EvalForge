# GEMINI.md - EvalForge Project Guide

> **Project:** EvalForge (AI / LLM / Agent Evaluation Microservice)  
> **Repository:** https://github.com/BQT170304/EvalForge.git  
> **Python Version:** >= 3.12 (Managed with `uv`)

---

## 1. Project Overview

**EvalForge** is a production-grade evaluation service designed for AI, LLM applications, RAG pipelines, and multi-agent systems. It integrates deterministic checks, heuristic NLP metrics, LLM-as-a-Judge, RAG triads, and multi-agent cooperation analysis into a unified async evaluation pipeline.

### Core Architecture & Tech Stack
- **Framework & API:** FastAPI, Uvicorn, Gunicorn, Pydantic v2, Pydantic Settings
- **Task Queue & Async Execution:** Celery, Redis
- **Database & Storage:** PostgreSQL with `pgvector`, SQLAlchemy 2.0 (`asyncpg`), Alembic
- **Evaluation Engines & NLP:** DeepEval, RAGAS, LiteLLM, NLTK, ROUGE, BERTScore, Sentence Transformers, Presidio (PII)
- **Observability:** OpenTelemetry GenAI standards, Structlog, pluggable tracing
- **Package & Virtualenv Management:** `uv`

---

## 2. Directory Structure

```
d:/Vibe/AI Eval/
├── evalforge/                  # Main application package
│   ├── api/                    # FastAPI routes & dependency injection
│   │   ├── deps.py             # Auth (API key) and DB session dependencies
│   │   └── v1/                 # API Version 1 endpoints (evaluate, metrics, health, etc.)
│   ├── config.py               # Global settings via Pydantic BaseSettings
│   ├── db/                     # Database engine & session management (AsyncSession)
│   ├── engine/                 # Core Evaluation Engine
│   │   ├── base.py             # Base classes: EvalForgeMetric, EvalTestCase, MetricResult
│   │   ├── orchestrator.py     # EvaluationOrchestrator for batch/parallel execution
│   │   ├── registry.py         # MetricRegistry for metric discovery & instantiation
│   │   ├── metrics/            # Native metric implementations
│   │   │   ├── deterministic/  # JSON schema, Regex, Length, Latency, Cost, PII
│   │   │   └── heuristic/      # BLEU, ROUGE, BERTScore, Semantic Similarity
│   │   └── wrappers/           # Dynamic wrappers for external frameworks (DeepEval, RAGAS)
│   ├── models/                 # SQLAlchemy DB models and Pydantic schemas
│   │   ├── db.py               # PostgreSQL schema models
│   │   └── schemas.py          # Request/Response DTO models
│   ├── tasks/                  # Celery tasks & worker configuration
│   └── main.py                 # FastAPI application entrypoint & lifespan
├── tests/                      # Pytest suite
│   ├── unit/                   # Unit tests (deterministic, heuristic, registry, etc.)
│   └── integration/            # API and async task integration tests
├── docker-compose.yaml         # Multi-container setup (API, Celery, Postgres, Redis)
├── Dockerfile                  # Application container image
├── pyproject.toml              # Build config, dependencies, Ruff & Mypy settings
└── uv.lock                     # Locked dependency tree
```

---

## 3. Development Commands & Workflows

### Environment & Package Management (`uv`)
```bash
# Sync all dependencies (including dev)
uv sync

# Add a new dependency
uv add <package_name>

# Add a development-only dependency
uv add --dev <package_name>
```

### Running the API & Services
```bash
# Run local FastAPI development server
uv run uvicorn evalforge.main:app --reload --port 8000

# Start Celery worker locally
uv run celery -A evalforge.tasks.celery_app worker --loglevel=info

# Full stack via Docker Compose
docker-compose up -d --build
```

### Linting, Formatting, and Type Checking
```bash
# Lint code with Ruff
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Type checking with Mypy
uv run mypy evalforge
```

### Testing
```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest tests/unit

# Run with verbose output
uv run pytest -v
```

---

## 4. Key Design Patterns & Guidelines

### A. Implementing & Registering Metrics
All metrics subclass `EvalForgeMetric` from [`evalforge/engine/base.py`](file:///d:/Vibe/AI%20Eval/evalforge/engine/base.py) and implement the asynchronous `evaluate(self, test_case: EvalTestCase) -> MetricResult` method.

To register a metric:
```python
from evalforge.engine.base import EvalForgeMetric, EvalTestCase, MetricResult, MetricCategory, MetricSource
from evalforge.engine.registry import MetricRegistry

@MetricRegistry.register("my_custom_metric")
class MyCustomMetric(EvalForgeMetric):
    name = "my_custom_metric"
    category = MetricCategory.DETERMINISTIC
    source = MetricSource.CUSTOM

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        # Compute metric score and reason
        score = 1.0 if test_case.output else 0.0
        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=score >= self.threshold,
            threshold=self.threshold,
            reason="Validation passed" if score == 1.0 else "Output was empty",
            source=self.source,
        )
```

### B. Wrapped Framework Metrics (DeepEval & RAGAS)
- When defining wrapped metrics in `evalforge/engine/wrappers/`, define `name` and `category` as class-level attributes within the class body to preserve full static type visibility and compatibility with `MetricRegistry.list_all()`.
- Avoid namespace collisions with outer wrapper parameters by naming arguments uniquely (e.g. `metric_name`, `metric_category`).

### C. Database & Async Sessions
- Use asynchronous SQLAlchemy sessions (`AsyncSession`) provided by `evalforge.db.session.get_db`.
- Database models reside in `evalforge.models.db` and inherit from declarative base.

### D. Coding Conventions & Standards
- **Python 3.12+ Idioms**: Utilize modern type syntax (`X | Y` instead of `Union[X, Y]`, `list[str]` instead of `typing.List[str]`).
- **Strict Typing**: All function/method signatures and return types MUST have explicit type annotations. Keep `mypy` strict mode happy.
- **Async Purity**: Never invoke blocking I/O (e.g. synchronous HTTP calls or long file reads) inside async coroutines without `asyncio.to_thread` or Celery task offloading.
- **Linting & Formatting**: Follow Ruff rules (`ruff check .`, `ruff format .`) configured for 100 character line lengths.

### E. Docstrings Guidelines
- **Format**: Use concise **Google-style** or standard PEP 257 docstrings for all modules, classes, and public functions.
- **Content**:
  - Start with a clear, one-line summary describing the purpose.
  - Document `Args`, `Returns`, and `Raises` only where parameters, output schemas, or failure modes are non-trivial.
  - Focus on the *intent*, *preconditions*, and *domain behavior* rather than echoing obvious parameter names.
  - Example:
    ```python
    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        """Evaluates whether the output matches the expected schema.

        Args:
            test_case: Standardized test case containing input, output, and context.

        Returns:
            MetricResult: Evaluation score, pass/fail status, and diagnostic reason.

        Raises:
            MetricExecutionError: If schema parsing fails unexpectedly.
        """
    ```

### F. Concise & Optimized Code Practices
- **Guard Clauses & Early Returns**: Avoid deeply nested `if/else` ladders. Validate inputs and return early.
- **Resource Reuse**: Never re-instantiate heavy objects (e.g., `SentenceTransformer`, embedding models, database engines) inside per-sample loops. Initialize them as singleton or module-level resources.
- **Async Concurrency**: Leverage `asyncio.gather` with semaphores/chunking for batch test case evaluations to maximize throughput without overloading external APIs.
- **Zero Redundant Copies**: Stream or pass references for large prompt contexts/trajectories; avoid unnecessary string duplications and in-memory buffering.
- **Robust Error Isolation**: Catch and wrap third-party engine failures (DeepEval, RAGAS, LiteLLM) in structured `MetricResult` outputs with error reasons rather than terminating batch pipelines.
- **Structured Logging**: Use `structlog` with structured key-value pairs (e.g. `logger.info("metric_evaluated", metric=self.name, latency_ms=latency)`) instead of raw formatted strings.

