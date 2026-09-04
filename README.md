# ⚔️ EvalForge

> **Production-Grade AI / LLM / Agent Evaluation Service**  
> Standalone evaluation microservice that bridges deterministic assertions, heuristic NLP, LLM-as-a-Judge (DeepEval), RAG triaging (RAGAS), and cooperative multi-agent evaluation into one async pipeline.

---

## 🌟 Key Highlights

- **5-Layer Evaluation Engine**: Deterministic checks, Heuristic NLP (BLEU, ROUGE, BERTScore), LLM-as-a-Judge, RAG Triad, and Multi-Agent Cooperation metrics.
- **Framework-First Architecture**: Powered by **DeepEval** and **RAGAS** for battle-tested metrics while maintaining custom agent metrics & full independence.
- **Result Caching**: Metric results are cached (in-memory, Redis-backed when available), so repeated evaluations of identical inputs cost nothing.
- **Async Execution**: Non-blocking evaluation using **Celery** + **Redis** + **PostgreSQL**.
- **Modern Tech Stack**: Python 3.12+, FastAPI, SQLAlchemy 2.0 (asyncpg), Pydantic v2, Docker Compose.

---

## 🚀 Quickstart (Docker Compose)

```bash
# 1. Clone & setup environment
cp .env.example .env

# 2. Spin up PostgreSQL, Redis, FastAPI API, and Celery Workers
#    The api container runs `alembic upgrade head` before serving.
docker-compose up -d --build

# 3. Check health
curl http://localhost:8080/api/v1/health
```

### Running locally (without Docker)

```bash
uv sync
alembic upgrade head                      # requires a reachable Postgres
uv run uvicorn evalforge.main:app --reload --port 8080
```

Schema changes go through Alembic — never `create_all`:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

---

## 📊 API Quick Demo

### Evaluate Single LLM Output

```bash
curl -X POST "http://localhost:8080/api/v1/evaluate" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev-key-change-me" \
     -d '{
       "input": "What is the capital of France?",
       "output": "Paris is the capital of France.",
       "expected_output": "The capital of France is Paris.",
       "context": ["France is a European nation whose capital and largest city is Paris."],
       "metrics": ["length_checker", "bleu_score", "rouge_score"]
     }'
```

---

## 📚 Metrics Catalog

| Category | Metric | Source |
| :--- | :--- | :--- |
| **Deterministic** | `json_schema`, `regex_matcher`, `length_checker`, `latency_checker`, `cost_checker`, `pii_scanner` | Built-in |
| **Heuristic** | `semantic_similarity`, `bleu_score`, `rouge_score`, `bert_score` | NLP Custom |
| **LLM-as-a-Judge** | `faithfulness`, `answer_relevancy`, `hallucination`, `coherence`, `g_eval`, `toxicity`, `bias` | DeepEval |
| **RAG Triad** | `context_recall`, `context_precision`, `answer_similarity` | RAGAS |
| **Agent / Multi-Agent** | `task_completion`, `trajectory_optimality`, `loop_detection`, `coordination_overhead`, `knowledge_alignment` | Custom |

---

## 🧪 Testing

```bash
uv run pytest              # full suite
uv run pytest tests/unit   # fast loop, no services required
```

---

## 🗺️ Roadmap

Not built yet — the settings keys exist in `config.py`, the code does not:

- **Observability adapters** — Langfuse, LangSmith, Arize Phoenix, Datadog; OpenTelemetry
  GenAI instrumentation at the LLM client boundary, and pushing scores back to the
  monitoring backend.
- **CI/CD regression gating** — run a golden dataset on every PR and fail on regression.
