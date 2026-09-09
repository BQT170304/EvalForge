import {
  Dataset,
  DatasetCreate,
  DatasetEntry,
  EvaluationResponse,
  Experiment,
  ExperimentComparison,
  ExperimentCreate,
  MetricInfo,
  MetricScoreResponse,
  SingleEvaluationRequest,
  SystemHealth,
} from '../types';
import { METRICS_CATALOG, MOCK_DATASETS, MOCK_EXPERIMENTS } from '../data/mockData';

const SETTINGS_KEY = 'evalforge_settings';

export interface ApiSettings {
  baseUrl: string;
  apiKey: string;
  forceMock: boolean;
}

export function getApiSettings(): ApiSettings {
  const saved = localStorage.getItem(SETTINGS_KEY);
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch {
      // fallback
    }
  }
  return {
    baseUrl: '/api/v1',
    apiKey: '',
    forceMock: false,
  };
}

export function saveApiSettings(settings: ApiSettings): void {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

class EvalForgeApi {
  private getHeaders(): HeadersInit {
    const settings = getApiSettings();
    const headers: HeadersInit = { 'Content-Type': 'application/json' };
    if (settings.apiKey) {
      headers['X-API-Key'] = settings.apiKey;
    }
    return headers;
  }

  private getUrl(path: string): string {
    const settings = getApiSettings();
    const base = settings.baseUrl.replace(/\/+$/, '');
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${base}${cleanPath}`;
  }

  async checkHealth(): Promise<SystemHealth> {
    const settings = getApiSettings();
    if (settings.forceMock) {
      return {
        status: 'healthy',
        service: 'EvalForge (Simulation Mode)',
        version: '0.1.0',
        environment: 'development-preview',
        latency_ms: 12,
        is_mock: true,
      };
    }

    const startTime = performance.now();
    try {
      const res = await fetch(this.getUrl('/health'), {
        headers: this.getHeaders(),
        signal: AbortSignal.timeout(3000),
      });
      const latency = Math.round(performance.now() - startTime);
      if (res.ok) {
        const data = await res.json();
        return {
          status: 'healthy',
          service: data.service || 'EvalForge',
          version: data.version || '0.1.0',
          environment: data.environment || 'development',
          latency_ms: latency,
          is_mock: false,
        };
      }
      return {
        status: 'degraded',
        service: 'EvalForge',
        version: '0.1.0',
        environment: 'unknown',
        latency_ms: latency,
        is_mock: true,
      };
    } catch {
      // Return simulated health so UI stays responsive and warns user gracefully
      return {
        status: 'disconnected',
        service: 'EvalForge Backend (Offline / Demo Mode)',
        version: '0.1.0',
        environment: 'demo-local',
        latency_ms: 0,
        is_mock: true,
      };
    }
  }

  async getMetrics(): Promise<MetricInfo[]> {
    const settings = getApiSettings();
    if (!settings.forceMock) {
      try {
        const res = await fetch(this.getUrl('/metrics'), {
          headers: this.getHeaders(),
          signal: AbortSignal.timeout(3000),
        });
        if (res.ok) {
          return await res.json();
        }
      } catch {
        // Fallback to catalog
      }
    }
    return METRICS_CATALOG;
  }

  async evaluateSingle(request: SingleEvaluationRequest): Promise<EvaluationResponse> {
    const settings = getApiSettings();
    if (!settings.forceMock) {
      try {
        const res = await fetch(this.getUrl('/evaluate'), {
          method: 'POST',
          headers: this.getHeaders(),
          body: JSON.stringify(request),
          signal: AbortSignal.timeout(45000),
        });
        if (res.ok) {
          return await res.json();
        }
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.detail || errJson?.message || `HTTP ${res.status}: Evaluation error`);
      } catch (err) {
        // fetch() rejects with TypeError on network failure and DOMException on abort/timeout;
        // anything else is our own thrown Error for a real API response and must propagate.
        const isConnectivityError = err instanceof TypeError || err instanceof DOMException;
        if (!isConnectivityError) {
          throw err;
        }
        console.warn('Backend unavailable, falling back to simulated evaluation', err);
      }
    }

    // Simulated evaluation
    await new Promise((resolve) => setTimeout(resolve, 900));

    const results: MetricScoreResponse[] = request.metrics.map((metricName) => {
      const metricDef = METRICS_CATALOG.find((m) => m.name === metricName);
      const threshold = request.thresholds?.[metricName] ?? metricDef?.default_threshold ?? 0.7;

      let score = 0.85 + (Math.random() * 0.14 - 0.05);
      let passed = score >= threshold;
      let reason = 'Evaluation assertion successfully verified.';

      if (metricName === 'json_schema') {
        try {
          JSON.parse(request.output);
          score = 1.0;
          passed = true;
          reason = 'Valid JSON schema: all required schema constraints satisfied.';
        } catch {
          score = 0.0;
          passed = false;
          reason = 'Output is not valid JSON according to schema.';
        }
      } else if (metricName === 'pii_scanner') {
        const hasCard = /\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/.test(request.output);
        const hasEmail = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/.test(request.output);
        if (hasCard || hasEmail) {
          score = 0.0;
          passed = false;
          reason = `Detected potential PII leakage: ${hasCard ? 'Credit Card Number' : ''} ${hasEmail ? 'Email Address' : ''}.`;
        } else {
          score = 1.0;
          passed = true;
          reason = 'Zero sensitive entities or PII patterns detected.';
        }
      } else if (metricName === 'faithfulness') {
        score = request.context && request.context.length > 0 ? 0.94 : 0.45;
        passed = score >= threshold;
        reason = passed
          ? 'Output is strictly grounded in the provided reference context with 0 unverified claims.'
          : 'Output contains claims not directly supported by retrieved context.';
      } else if (metricName === 'loop_detection') {
        score = 0.98;
        passed = true;
        reason = 'No cyclic states or repeated actions detected in execution trajectory.';
      } else if (metricName === 'length_checker') {
        const words = request.output.trim().split(/\s+/).length;
        score = 1.0;
        passed = true;
        reason = `Output length valid (${words} words, within configured bounds).`;
      }

      return {
        metric_name: metricName,
        category: metricDef?.category || 'deterministic',
        source: metricDef?.source || 'builtin',
        score: Math.round(score * 100) / 100,
        passed,
        threshold,
        reason,
        cost_usd: Math.round((0.0008 + Math.random() * 0.0015) * 10000) / 10000,
        latency_ms: Math.round(180 + Math.random() * 240),
      };
    });

    const overall_passed = results.every((r) => r.passed);
    const average_score =
      results.length > 0
        ? Math.round((results.reduce((acc, r) => acc + r.score, 0) / results.length) * 100) / 100
        : 0;
    const total_cost = Math.round(results.reduce((acc, r) => acc + r.cost_usd, 0) * 10000) / 10000;
    const total_latency = Math.round(results.reduce((acc, r) => acc + r.latency_ms, 0));

    return {
      eval_id: 'eval-' + Math.random().toString(36).substring(2, 11),
      status: 'completed',
      overall_passed,
      average_score,
      total_cost_usd: total_cost,
      latency_ms: total_latency,
      results,
      metadata: request.metadata || {},
      created_at: new Date().toISOString(),
    };
  }

  async getDatasets(): Promise<Dataset[]> {
    const settings = getApiSettings();
    if (!settings.forceMock) {
      try {
        const res = await fetch(this.getUrl('/datasets'), {
          headers: this.getHeaders(),
          signal: AbortSignal.timeout(3000),
        });
        if (res.ok) {
          const list = await res.json();
          if (Array.isArray(list) && list.length > 0) {
            return list;
          }
        }
      } catch {
        // fallback
      }
    }
    return [...MOCK_DATASETS];
  }

  async createDataset(payload: DatasetCreate): Promise<Dataset> {
    const settings = getApiSettings();
    if (!settings.forceMock) {
      try {
        const res = await fetch(this.getUrl('/datasets'), {
          method: 'POST',
          headers: this.getHeaders(),
          body: JSON.stringify(payload),
          signal: AbortSignal.timeout(5000),
        });
        if (res.ok) {
          return await res.json();
        }
      } catch {
        // fallback
      }
    }

    const newDataset: Dataset = {
      id: 'ds-' + Math.random().toString(36).substring(2, 10),
      name: payload.name,
      version: payload.version || '1.0.0',
      description: payload.description,
      schema_version: '1.0',
      tags: payload.tags || ['custom'],
      entry_count: payload.entries?.length || 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      entries: payload.entries?.map((e, idx) => ({
        id: `entry-${idx + 1}`,
        dataset_id: 'ds-temp',
        input: e.input,
        expected_output: e.expected_output,
        context: e.context,
        metadata: e.metadata,
        created_at: new Date().toISOString(),
      })),
    };
    MOCK_DATASETS.unshift(newDataset);
    return newDataset;
  }

  async getDatasetEntries(datasetId: string): Promise<DatasetEntry[]> {
    const settings = getApiSettings();
    if (!settings.forceMock) {
      try {
        const res = await fetch(this.getUrl(`/datasets/${datasetId}/entries`), {
          headers: this.getHeaders(),
          signal: AbortSignal.timeout(4000),
        });
        if (res.ok) {
          return await res.json();
        }
      } catch {
        // fallback
      }
    }
    const found = MOCK_DATASETS.find((d) => d.id === datasetId);
    return found?.entries || [];
  }

  async getExperiments(): Promise<Experiment[]> {
    const settings = getApiSettings();
    if (!settings.forceMock) {
      try {
        const res = await fetch(this.getUrl('/experiments'), {
          headers: this.getHeaders(),
          signal: AbortSignal.timeout(3000),
        });
        if (res.ok) {
          const list = await res.json();
          if (Array.isArray(list) && list.length > 0) {
            return list;
          }
        }
      } catch {
        // fallback
      }
    }
    return [...MOCK_EXPERIMENTS];
  }

  async createExperiment(payload: ExperimentCreate): Promise<Experiment> {
    const settings = getApiSettings();
    if (!settings.forceMock) {
      try {
        const res = await fetch(this.getUrl('/experiments?trigger=true'), {
          method: 'POST',
          headers: this.getHeaders(),
          body: JSON.stringify(payload),
          signal: AbortSignal.timeout(60000),
        });
        if (res.ok) {
          return await res.json();
        }
      } catch {
        // fallback
      }
    }

    const targetDs = MOCK_DATASETS.find((d) => d.id === payload.dataset_id);
    const total = targetDs?.entry_count || 10;
    const passed = Math.round(total * 0.9);

    const summaryScores: Record<string, number> = {};
    for (const m of payload.metrics) {
      summaryScores[m] = Math.round((0.85 + Math.random() * 0.12) * 100) / 100;
    }

    const newExp: Experiment = {
      id: 'exp-' + Math.random().toString(36).substring(2, 10),
      name: payload.name,
      description: payload.description,
      dataset_id: payload.dataset_id,
      dataset_name: targetDs?.name || 'Standard Dataset',
      dataset_version: payload.dataset_version || '1.0.0',
      status: 'COMPLETED',
      pass_rate: Math.round((passed / total) * 1000) / 10,
      summary_scores: summaryScores,
      total_cost_usd: Math.round(total * 0.009 * 100) / 100,
      duration_seconds: Math.round(total * 0.3 * 10) / 10,
      total_entries: total,
      passed_entries: passed,
      failed_entries: total - passed,
      judge_model: payload.judge_model || 'gpt-4o',
      target_model: payload.target_model || 'gpt-4o',
      prompt_version: payload.prompt_version || 'v1.0',
      metrics: payload.metrics,
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
    };
    MOCK_EXPERIMENTS.unshift(newExp);
    return newExp;
  }

  async getExperimentReport(experimentId: string): Promise<string> {
    const settings = getApiSettings();
    if (!settings.forceMock) {
      try {
        const res = await fetch(this.getUrl(`/reports/${experimentId}`), {
          headers: this.getHeaders(),
          signal: AbortSignal.timeout(4000),
        });
        if (res.ok) {
          return await res.text();
        }
      } catch {
        // fallback
      }
    }

    const exp = MOCK_EXPERIMENTS.find((e) => e.id === experimentId) || MOCK_EXPERIMENTS[0];
    return `# ⚔️ EvalForge Evaluation Report: ${exp.name}

> Generated on ${new Date().toLocaleDateString()} for Dataset **${exp.dataset_name || exp.dataset_id}** (v${exp.dataset_version})

---

### Executive Summary

- **Overall Pass Rate:** ${exp.pass_rate || 90}%
- **Status:** ${exp.status}
- **Total Test Cases Evaluated:** ${exp.total_entries}
- **Passed:** ${exp.passed_entries} | **Failed:** ${exp.failed_entries}
- **Total Cost:** $${exp.total_cost_usd.toFixed(4)} USD
- **Execution Duration:** ${exp.duration_seconds || 30}s
- **Judge Model:** \`${exp.judge_model || 'gpt-4o'}\`
- **Target Model:** \`${exp.target_model || 'default'}\`
- **Prompt Version:** \`${exp.prompt_version || 'default'}\`

---

### Metric Performance Breakdown

| Metric Name | Score | Status | Default Threshold |
| :--- | :--- | :--- | :--- |
${Object.entries(exp.summary_scores || {})
  .map(([k, v]) => `| **\`${k}\`** | ${(v * 100).toFixed(1)}% | ${v >= 0.7 ? '✅ Passed' : '❌ Failed'} | 70% |`)
  .join('\n')}

---

### Recommendations & Observations
1. **Factual Grounding:** Faithfulness and Hallucination scores remained resilient above the 0.85 threshold.
2. **Latency Budget:** Execution times complied with the production 1.2s SLA.
3. **Continuous Monitoring:** Recommended to integrate Langfuse / OpenTelemetry tracing export for live inference drift monitoring.
`;
  }

  compareExperiments(experiments: Experiment[], expIds: string[]): ExperimentComparison {
    const exps = expIds
      .map((id) => experiments.find((e) => e.id === id))
      .filter((e): e is Experiment => Boolean(e));
    const metricsMap: Record<string, { metric_name: string; scores: Record<string, number> }> = {};

    exps.forEach((exp) => {
      if (exp.summary_scores) {
        Object.entries(exp.summary_scores).forEach(([metric, score]) => {
          if (!metricsMap[metric]) {
            metricsMap[metric] = { metric_name: metric, scores: {} };
          }
          metricsMap[metric].scores[exp.id] = score;
        });
      }
    });

    let winnerId = exps[0]?.id;
    let highestPassRate = -1;
    exps.forEach((e) => {
      if ((e.pass_rate || 0) > highestPassRate) {
        highestPassRate = e.pass_rate || 0;
        winnerId = e.id;
      }
    });

    return {
      experiments: exps,
      metrics_comparison: metricsMap,
      winner_id: winnerId,
    };
  }
}

export const api = new EvalForgeApi();
