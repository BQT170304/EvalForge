export type MetricCategory =
  | 'deterministic'
  | 'heuristic'
  | 'llm_judge'
  | 'rag'
  | 'agent'
  | 'safety';

export type MetricSource = 'deepeval' | 'ragas' | 'custom' | 'builtin';

export interface MetricInfo {
  name: string;
  category: MetricCategory;
  source: MetricSource;
  default_threshold: number;
  description: string;
  requires_context: boolean;
  requires_expected_output: boolean;
  requires_tools: boolean;
}

export interface MetricScoreResponse {
  metric_name: string;
  category: string;
  source: string;
  score: number;
  passed: boolean;
  threshold: number;
  reason: string;
  details?: Record<string, any>;
  cost_usd: number;
  latency_ms: number;
}

export interface SingleEvaluationRequest {
  input: string;
  output: string;
  expected_output?: string;
  context?: string[];
  metrics: string[];
  thresholds?: Record<string, number>;
  parameters?: Record<string, Record<string, unknown>>;
  metadata?: Record<string, unknown>;
  trace_id?: string;
  source_service?: string;
}

export interface EvaluationResponse {
  eval_id: string;
  status: 'completed' | 'failed' | 'pending' | 'running';
  overall_passed: boolean;
  average_score: number;
  total_cost_usd: number;
  latency_ms: number;
  results: MetricScoreResponse[];
  metadata?: Record<string, any>;
  created_at: string;
}

export interface DatasetEntry {
  id: string;
  dataset_id: string;
  input: string;
  expected_output?: string;
  context?: string[];
  metadata?: Record<string, any>;
  created_at: string;
}

export interface Dataset {
  id: string;
  name: string;
  version: string;
  description?: string;
  schema_version?: string;
  tags: string[];
  entry_count: number;
  created_at: string;
  updated_at: string;
  entries?: DatasetEntry[];
}

export interface DatasetCreate {
  name: string;
  version?: string;
  description?: string;
  tags?: string[];
  metadata?: Record<string, any>;
  entries?: Array<{
    input: string;
    expected_output?: string;
    context?: string[];
    metadata?: Record<string, any>;
  }>;
}

export interface Experiment {
  id: string;
  name: string;
  description?: string;
  dataset_id: string;
  dataset_name?: string;
  dataset_version: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  pass_rate?: number;
  summary_scores?: Record<string, number>;
  total_cost_usd: number;
  duration_seconds?: number;
  total_entries: number;
  passed_entries: number;
  failed_entries: number;
  judge_model?: string;
  target_model?: string;
  prompt_version?: string;
  metrics?: string[];
  thresholds?: Record<string, number>;
  created_at: string;
  completed_at?: string;
}

export interface ExperimentCreate {
  name: string;
  description?: string;
  dataset_id: string;
  dataset_version?: string;
  metrics: string[];
  thresholds?: Record<string, number>;
  judge_model?: string;
  target_model?: string;
  prompt_version?: string;
}

export interface ExperimentComparison {
  experiments: Experiment[];
  metrics_comparison: Record<
    string,
    {
      metric_name: string;
      scores: Record<string, number>;
      delta?: number;
    }
  >;
  winner_id?: string;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'disconnected';
  service: string;
  version: string;
  environment: string;
  latency_ms?: number;
  is_mock?: boolean;
}

export type ActiveTab =
  | 'overview'
  | 'playground'
  | 'datasets'
  | 'experiments'
  | 'compare'
  | 'catalog'
  | 'reports'
  | 'settings';
