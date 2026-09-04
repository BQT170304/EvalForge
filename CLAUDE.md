# CLAUDE.md — EvalForge

Async evaluation service for LLM / RAG / multi-agent outputs. FastAPI + Celery + Postgres(pgvector) + Redis, Python 3.12, managed with `uv`.

Shared project guide (stack, commands, conventions, docstring rules): @GEMINI.md

Below is the delta — things GEMINI.md gets wrong or omits.

## Commands

```bash
uv sync                                  # deps (incl. dev)
uv run pytest tests/unit                 # fast loop; integration needs Postgres+Redis
uv run ruff check --fix . && uv run ruff format .
uv run mypy evalforge                    # strict mode — must stay clean
uv run uvicorn evalforge.main:app --reload
alembic upgrade head                     # schema; needs a reachable Postgres
docker-compose up -d --build             # full stack
```

Lint + mypy + unit tests before calling anything done.

## Module map (current — GEMINI.md's tree predates `datasets/`, `experiments/`, `utils/`, agent & safety metrics)

```
evalforge/
├── api/v1/          evaluate, metrics, datasets, experiments, reports, health
├── engine/
│   ├── base.py      EvalForgeMetric, EvalTestCase, MetricResult, MetricCategory/Source
│   ├── registry.py  MetricRegistry singleton — @MetricRegistry.register("name")
│   ├── orchestrator.py  batch/parallel execution
│   ├── metrics/     deterministic/ heuristic/ agent/ safety/
│   └── wrappers/    deepeval_wrapper, ragas_wrapper
├── datasets/        manager, importer, exporter, converter, generator
├── experiments/     runner, comparator, reporter
├── tasks/           celery_app + evaluation_tasks, experiment_tasks
├── utils/           llm_client (LiteLLM), embeddings, caching
└── models/          db.py (SQLAlchemy), schemas.py (Pydantic DTOs)

alembic/             env.py reuses evalforge.db.session.get_engine + Settings
└── versions/        0001_baseline.py — snapshot of models/db.py
```

## Gotchas

- **Registration is import-driven.** `MetricRegistry` only knows metrics whose module got imported. A new metric file must be imported from its package `__init__.py`, which is in turn imported by `engine/metrics/__init__.py`. Otherwise it silently doesn't exist.
- **`register` overwrites `cls.name`** with the registered key and only warns on duplicates — a name collision is a silent shadow, not an error.
- **DB dependency is `evalforge.db.session.get_db_session`** (GEMINI.md says `get_db`).
- **Auth bypass in dev:** `verify_api_key` returns `"dev-user"` when `settings.is_development` and no `X-API-Key` header. Don't rely on that path in tests that assert auth.
- **Metric failures must not kill a batch.** Wrap third-party engine errors (DeepEval / RAGAS / LiteLLM) into a failed `MetricResult` with a reason instead of raising.
- **Heavy models are singletons.** Sentence transformers / BERTScore live in `utils/embeddings.py` — never instantiate per test case.
- **Schema is Alembic's, not `create_all`'s.** `init_db()` is gone; the api container runs `alembic upgrade head` before uvicorn. After changing `models/db.py`, generate a revision — the baseline was rendered from metadata against an empty DB, so it has never been applied to a real Postgres by this repo's history.
- **Every evaluation goes through the cache.** `orchestrator.evaluate` keys on metric name + full test case + metric kwargs. Failed results are deliberately not cached. A metric whose score depends on anything outside `EvalTestCase` will serve stale results.
- **Duplicate metric aliases are intentional.** `bleu_score` / `BLEUScore` etc. register the same class twice; the last decorator wins for `cls.name`, so `MetricResult.metric_name` reports the CamelCase alias whichever key you asked for.
- `.env` is gitignored; `.env.example` is the contract. Update it when adding a setting.
