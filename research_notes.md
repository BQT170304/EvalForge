# AI/LLM/Agent Evaluation System — Research Notes

> **Date:** 2026-08-22  
> **Purpose:** Evidence comprehensive knowledge for building a production-grade LLM/Agent evaluation system

---

## 1. Landscape Overview — Current State of LLM Evaluation (2026)

### 1.1 Industry Shift: From "Vibe Checks" to Structured Quality Assurance

The evaluation landscape has matured from ad-hoc "looks good to me" checks to **multi-layered, automated quality pipelines**. Key trends:

- **Offline + Online evaluation** are now treated as distinct but complementary disciplines
- **CI/CD-integrated gating** — evaluation runs block merges/deploys when regressions occur
- **LLM-as-a-Judge** is the dominant scaling strategy for nuanced evaluation
- **Agent-specific evaluation** (tool use, multi-step reasoning, cooperation) is now a critical frontier
- **Regulatory compliance** (EU AI Act, NIST AI RMF) demands audit trails and safety testing

### 1.2 Key Evaluation Frameworks Comparison

| Framework | Type | Best For | Key Differentiator |
|:---|:---|:---|:---|
| **DeepEval** | OSS (Python) | CI/CD regression testing | `pytest` integration, rich built-in metrics |
| **RAGAS** | OSS (Python) | RAG pipeline evaluation | Faithfulness/relevancy metrics, context-aware |
| **Promptfoo** | OSS (CLI) | Red teaming & security | YAML-driven, adversarial testing focus |
| **Braintrust** | SaaS | End-to-end dev loops | Fast experiment tracking, dashboard |
| **LangSmith** | Proprietary | LangChain ecosystem | Deep LangGraph integration |
| **Arize Phoenix** | Source-available | Notebook-first eval | Pre-built LLM-as-Judge templates |
| **Langfuse** | OSS (MIT) | Self-hosted observability | OTel-native, full self-host parity |
| **MLflow** | OSS | Open standards lifecycle | Vendor-neutral, broad ecosystem |
| **Giskard** | OSS/SaaS | EU AI Act compliance | Regulatory focus |
| **LangWatch** | SaaS | Agent simulations | Multi-turn/voice testing |

---

## 2. Evaluation Metrics — Comprehensive Taxonomy

### 2.1 Deterministic (Code-Based) Metrics
- **Format Validation:** JSON schema, regex, output structure checks
- **Latency & Cost:** p50/p95/p99 response time, token cost per request
- **String Matching:** BLEU, ROUGE, exact match, Levenshtein distance
- **PII Detection:** Regex/NER-based scanning for sensitive data leakage

### 2.2 Heuristic & Embedding-Based Metrics
- **Semantic Similarity:** Cosine similarity of embeddings (input↔output, output↔reference)
- **BERTScore:** Token-level semantic matching using contextual embeddings
- **Perplexity:** Model confidence in generated text

### 2.3 LLM-as-a-Judge Metrics (RAG-Specific)
- **Faithfulness (Groundedness):** `supported_claims / total_claims` — are claims backed by context?
- **Answer Relevancy:** Semantic alignment of answer to original query
- **Context Relevancy:** Quality of retrieved documents vs. query intent
- **Context Recall:** Coverage of ground-truth in retrieved context
- **Hallucination Score:** Inverse of faithfulness, measures fabricated information

### 2.4 LLM-as-a-Judge Metrics (General)
- **Coherence:** Logical flow and internal consistency
- **Helpfulness:** Practical utility of the response
- **Toxicity / Harmfulness:** Safety assessment via rubric
- **G-Eval:** Natural-language criteria evaluation (custom rubrics)
- **Answer Correctness:** Factual accuracy against known ground truth

### 2.5 Agent-Specific Metrics
- **Task Completion Rate:** Did the agent achieve the goal?
- **Tool Selection Accuracy:** Correct tool chosen for the right step
- **Tool Argument Correctness:** Parameters passed correctly to tools
- **Trajectory Optimality:** Was the path taken the most efficient?
- **Action Advancement:** Do actions move toward the goal vs. looping?
- **Coordination Overhead:** Communication cost in multi-agent setups
- **Knowledge Alignment:** Are cooperating agents aligned on shared context?
- **Coordination Failure Rate:** Miscoordination, conflicts, redundant work

### 2.6 Safety & Guardrail Metrics
- **Prompt Injection Resistance:** Susceptibility to goal hijacking
- **Jailbreak Resistance:** Ability to maintain safety boundaries
- **PII Leakage Rate:** Frequency of exposing sensitive data
- **Bias Detection:** Demographic/cultural bias in outputs
- **Refusal Appropriateness:** Correct refusal of harmful requests

---

## 3. Evaluation Techniques

### 3.1 Three-Layer Evaluation Architecture
1. **Layer 1 — Deterministic:** Code assertions, regex, schema validation, latency thresholds
2. **Layer 2 — Heuristic/Statistical:** Semantic similarity, ROUGE/BLEU, embedding distance
3. **Layer 3 — LLM-as-a-Judge:** Custom rubrics evaluated by a stronger model

### 3.2 Evaluation Scope Levels (For Agents)
1. **Span-level:** Individual component validation (retrieval, tool call, generation)
2. **Task-level:** End-to-end task success measurement
3. **Trajectory-level:** Quality of the agent's decision chain

### 3.3 Advanced Techniques
- **Claim-Level Verification:** Decompose output → verify each claim against context
- **Self-Evaluation:** LLM critiques its own output before serving
- **Game-Theoretic Modeling:** Nash equilibrium, Pareto optimality for multi-agent
- **Behavioral Economics Games:** Stag Hunt, Public Goods as cooperation diagnostics
- **Milestone-based KPIs:** Track progress checkpoints (MultiAgentBench approach)
- **Human-in-the-Loop (HITL):** Expert review for high-stakes/edge cases
- **Red Teaming (Automated):** Adversarial simulators generating attack vectors at scale
- **Regression-from-Production:** Convert production failures → permanent test cases

---

## 4. Monitoring Service Integration Landscape

### 4.1 Service Comparison

| Service | Self-Host | OTel Support | API for External Eval | License |
|:---|:---|:---|:---|:---|
| **Langfuse** | ✅ Full parity | ✅ Native | ✅ Rich REST/SDK | MIT |
| **LangSmith** | Enterprise only | ❌ Proprietary | ✅ REST API | Proprietary |
| **Arize Phoenix** | ✅ Free/Local | ✅ OpenInference | ✅ REST API | ELv2 |
| **Datadog LLM** | ❌ Cloud only | ✅ Via OTel Collector | ✅ REST API | Proprietary |
| **W&B Weave** | ❌ Cloud | Partial | ✅ Python SDK | Proprietary |
| **Grafana + Tempo** | ✅ | ✅ Native | ✅ Via OTel | OSS |
| **Honeycomb** | ❌ Cloud | ✅ Native | ✅ REST API | Proprietary |

### 4.2 OpenTelemetry GenAI Semantic Conventions
- **Status:** Development (as of v1.42.0, June 2026)
- **Repository:** `open-telemetry/semantic-conventions-genai`
- **Key Attributes:** `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons`
- **Best Practice:** Instrument at the boundary (wrap LLM client calls), use abstraction layer to protect dashboards from breaking changes

### 4.3 Integration Patterns
1. **OTel Collector Fan-Out:** Instrument once → export to multiple backends
2. **Webhook-based:** POST traces to external evaluation endpoint
3. **Polling-based:** Periodically fetch new traces from monitoring service API
4. **Bidirectional Score Push:** Evaluate externally → push scores back to monitoring service

---

## 5. Key Benchmarks for Agent Cooperation

| Benchmark | Focus | Scoring Method |
|:---|:---|:---|
| **MultiAgentBench** | Cooperative + adversarial multi-agent | Milestone-based KPIs |
| **SWE-bench** | Software engineering tasks | Docker-based test harness |
| **GAIA** | General assistant tasks | Exact-match factual answers |
| **AgentBench** | Broad agent capabilities | Multi-environment scoring |
| **SOTOPIA-π** | Social intelligence | Social interaction rubrics |
| **BattleAgentBench** | Competition + cooperation | Game-theoretic metrics |

---

## 6. Dataset Management Best Practices

### 6.1 Golden Dataset Composition
- Representative production traffic (real queries)
- Curated edge cases (null values, injections, multi-turn complexity)
- Failure replays (previously broken scenarios)
- Synthetic supplements (for coverage gaps)

### 6.2 Versioning Strategy
- Treat datasets as **first-class versioned artifacts** (like code)
- Link dataset version ↔ model version ↔ prompt version per experiment
- Schema enforcement: `input`, `expected_output`, `context`, `metadata`
- Automated CI/CD runs against current golden set on every PR

### 6.3 Synthetic Data Generation
- **Context-grounded:** Feed actual docs/prompts, not generic queries
- **Multi-column:** Generate full eval rows (input, expected, persona, context)
- **Iterative refinement:** Generate → review → adjust → regenerate
- **Quality > Quantity:** 100 verified examples > 1,000 noisy ones

---

## 7. Cost & Performance Optimization

| Strategy | Impact | Technique |
|:---|:---|:---|
| **Model Routing** | Cost ↓ 50-80% | Route simple evals to smaller judge models |
| **Batch API** | Cost ↓ ~50% | OpenAI/Anthropic batch endpoints for offline evals |
| **Semantic Caching** | Latency ↓, Cost ↓ | Cache similar eval results, reuse scores |
| **Prompt Caching** | Cost ↓ 30-50% | Cache system prompts / long prefixes |
| **Async Processing** | Latency ↓ (user) | Offload eval to background workers |
| **Continuous Batching** | Throughput ↑ | Group requests dynamically (vLLM-style) |
| **Quantized Judges** | Cost ↓ 60-80% | Use 4-bit AWQ models as judges for non-critical evals |
