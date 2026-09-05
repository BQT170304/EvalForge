# Observability Setup (Grafana Cloud + Langfuse, both free tier)

EvalForge exports OpenTelemetry traces, metrics, and logs to Grafana Cloud,
and LLM-generation spans (judge model calls, synthetic generation) to
Langfuse Cloud. Both are optional — with the env vars below unset, the app
runs normally and just skips exporting.

## 1. Grafana Cloud (free tier)

1. Sign up at https://grafana.com/auth/sign-up/create-user (free tier
   includes Tempo traces, Mimir metrics, and Loki logs).
2. In your Grafana Cloud stack, go to **Connections → Add new connection →
   OpenTelemetry (OTLP)**.
3. Copy the **OTLP endpoint URL** shown there — it looks like
   `https://otlp-gateway-prod-xx-xxxx.grafana.net/otlp`. This is your
   `EVALFORGE_GRAFANA_OTLP_ENDPOINT` (no trailing `/v1/traces` etc. — the
   app appends the per-signal path itself).
4. On the same page, copy the **Instance ID** (a numeric stack ID) — this is
   `EVALFORGE_GRAFANA_OTLP_INSTANCE_ID`.
5. Generate an **API token** with at least `metrics:write`, `logs:write`,
   and `traces:write` scopes (**Administration → API Keys** or the
   generate-token button on the OTLP connection page) — this is
   `EVALFORGE_GRAFANA_OTLP_API_KEY`.

## 2. Langfuse Cloud (free tier)

1. Sign up at https://cloud.langfuse.com.
2. Create a new project.
3. Go to **Project Settings → API Keys** and create a new key pair.
4. Copy the **Public Key** into `LANGFUSE_PUBLIC_KEY` and the **Secret Key**
   into `LANGFUSE_SECRET_KEY`. Leave `LANGFUSE_HOST` as the default
   `https://cloud.langfuse.com` unless you're self-hosting.

## 3. Fill in `.env`

```bash
EVALFORGE_GRAFANA_OTLP_ENDPOINT=https://otlp-gateway-prod-xx-xxxx.grafana.net/otlp
EVALFORGE_GRAFANA_OTLP_INSTANCE_ID=123456
EVALFORGE_GRAFANA_OTLP_API_KEY=glc_your_token_here

LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com
```

## 4. Verify

1. Start the stack: `docker-compose up -d --build` (or
   `uv run uvicorn evalforge.main:app --reload` locally).
2. Send a request to `POST /api/v1/evaluate` with any metric.
3. **Grafana Cloud:** open your stack → **Explore** → select the Tempo
   data source → search by `service.name = evalforge`. You should see a
   trace with an `evalforge.metric.evaluate` span. Switch the data source
   to Loki and search `{service_name="evalforge"}` for the same request's
   logs (they'll share a `trace_id`). Switch to Mimir/Prometheus and query
   `evalforge_eval_requests_total` for the counter.
4. **Langfuse:** open your project's **Traces** tab — if the metric you
   ran included an LLM-judge call, you'll see an `evalforge.llm.complete`
   generation with the model, token usage, and cost. Metrics that don't
   call an LLM (e.g. `length_checker`) won't appear here — only Grafana
   receives those, by design.
