# ⚔️ EvalForge

> **Production-Grade AI / LLM / Agent Evaluation Service**  
> Standalone evaluation microservice that bridges deterministic assertions, heuristic NLP, LLM-as-a-Judge (DeepEval), RAG triaging (RAGAS), and cooperative multi-agent evaluation with bidirectional observability monitoring.

---

## 🌟 Key Highlights

- **5-Layer Evaluation Engine**: Deterministic checks, Heuristic NLP (BLEU, ROUGE, BERTScore), LLM-as-a-Judge, RAG Triad, and Multi-Agent Cooperation metrics.
- **Framework-First Architecture**: Powered by **DeepEval** and **RAGAS** for battle-tested metrics while maintaining custom agent metrics & full independence.
- **Bidirectional Observability**: Pluggable adapters for **Langfuse**, **LangSmith**, **Arize Phoenix**, **Datadog**, and OpenTelemetry GenAI standards.
- **Async Execution**: Non-blocking evaluation using **Celery** + **Redis** + **PostgreSQL**.
- **Modern Tech Stack**: Python 3.12+, FastAPI, SQLAlchemy 2.0 (asyncpg), Pydantic v2, Docker Compose.

---

## 🚀 Quickstart (Docker Compose)

```bash
# 1. Clone & setup environment
cp .env.example .env

# 2. Spin up PostgreSQL, Redis, FastAPI API, and Celery Workers
docker-compose up -d --build

# 3. Check health
curl http://localhost:8080/api/v1/health

# 4. Build the frontend and open the Web UI Dashboard
# The Docker image does not build the frontend yet — build it locally first
# (see "Building Frontend for Production" below), then it is served at:
# http://localhost:8080/
```

---

## 💻 Web UI Frontend (Dark Blue Theme)

EvalForge includes a modern single-page dashboard designed with a rich dark blue aesthetic (`#060d1f` / `#0a1535`):

- **Observability Overview**: Real-time pass rates, P95 latencies, cost tracking, 5-layer pipeline breakdown, and interactive quality radar.
- **Evaluation Playground**: Interactive test cases with customizable metric thresholds, regex/schema parameter tuning, RAG context chunks, and live score radar.
- **Datasets & Ground Truth**: Versioned test cases inspector, import/export JSON, and synthetic test case generator.
- **Experiments & Regressions**: Automated benchmark history, pass rate tracking, and prompt versioning.
- **Model / Prompt Comparator**: Side-by-side metric diff matrix and winner spotlight.
- **Metrics Catalog**: Searchable registry of all 25+ deterministic, NLP, LLM judge, RAG triad, and multi-agent metrics.
- **Evaluation Reports**: Formatted Markdown reports with copy/export capabilities.

### Running Frontend in Development Mode
```bash
cd frontend
npm install
npm run dev
# Access Vite dev server at: http://localhost:5173
```

### Building Frontend for Production
```bash
cd frontend
npm run build
# Built into frontend/dist and served directly by FastAPI at http://localhost:8080/
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
# Run unit & integration test suite
pytest -v
```
