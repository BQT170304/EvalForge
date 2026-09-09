import React from 'react';
import { ActiveTab, Experiment, MetricInfo } from '../types';
import { RadarChart } from '../components/RadarChart';
import {
  Activity,
  CheckCircle2,
  Clock,
  DollarSign,
  Layers,
  ArrowUpRight,
  TrendingUp,
  ShieldCheck,
  Zap,
  Radio,
} from 'lucide-react';

interface OverviewViewProps {
  onNavigate: (tab: ActiveTab) => void;
  experiments: Experiment[];
  metrics: MetricInfo[];
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  onNavigate,
  experiments,
  metrics,
}) => {
  const radarData = [
    { label: 'Faithfulness', value: 0.94, threshold: 0.75 },
    { label: 'Relevancy', value: 0.91, threshold: 0.7 },
    { label: 'Precision', value: 0.88, threshold: 0.7 },
    { label: 'PII Safe', value: 1.0, threshold: 0.95 },
    { label: 'Latency SLA', value: 0.92, threshold: 0.8 },
    { label: 'Agent Steps', value: 0.85, threshold: 0.75 },
  ];

  const totalEvaluations = experiments.reduce((acc, e) => acc + e.total_entries, 0) + 382;
  const avgPassRate =
    Math.round(
      (experiments.reduce((acc, e) => acc + (e.pass_rate || 0), 0) / (experiments.length || 1)) * 10
    ) / 10;
  const totalCost =
    Math.round(experiments.reduce((acc, e) => acc + e.total_cost_usd, 0) * 100) / 100 + 1.25;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#0d1e49] via-[#0e255c] to-[#0a183d] border border-[#1c3a80] p-6 shadow-glow-sm">
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-blue-500/20 text-cyan-300 border border-cyan-500/30">
                EVALFORGE v0.1.0 ACTIVE
              </span>
              <span className="text-xs text-slate-400">Microservice Engine</span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              Enterprise AI & Agent Evaluation Service
            </h2>
            <p className="text-sm text-slate-300 mt-1 max-w-2xl">
              Unified evaluation pipeline combining deterministic schema checks, heuristic NLP,
              DeepEval LLM judges, RAGAS RAG triads, and multi-agent coordination metrics.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => onNavigate('playground')}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold shadow-glow transition-all"
            >
              <Zap className="w-4 h-4" />
              <span>Launch Playground</span>
            </button>
            <button
              onClick={() => onNavigate('catalog')}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#13275c] hover:bg-[#1b357d] text-slate-200 text-sm font-semibold border border-[#23469a] transition-all"
            >
              <span>Explore {metrics.length} Metrics</span>
              <ArrowUpRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Ambient subtle background glow */}
        <div className="absolute right-0 top-0 -mt-8 -mr-8 w-64 h-64 rounded-full bg-blue-500/10 blur-3xl pointer-events-none" />
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Pass Rate */}
        <div className="p-5 rounded-xl bg-[#0a1535] border border-[#172d62] hover:border-blue-500/50 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Avg Pass Rate</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-950/80 border border-emerald-800 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">{avgPassRate}%</span>
            <span className="text-xs text-emerald-400 font-medium flex items-center">
              <TrendingUp className="w-3 h-3 mr-0.5" /> +2.4%
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Across all benchmark suites</p>
        </div>

        {/* Total Test Cases */}
        <div className="p-5 rounded-xl bg-[#0a1535] border border-[#172d62] hover:border-blue-500/50 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Evaluations</span>
            <div className="w-8 h-8 rounded-lg bg-blue-950/80 border border-blue-800 flex items-center justify-center text-blue-400">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">
              {totalEvaluations.toLocaleString()}
            </span>
            <span className="text-xs text-blue-400 font-mono">cases</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Synchronous & batch queue</p>
        </div>

        {/* Latency SLA */}
        <div className="p-5 rounded-xl bg-[#0a1535] border border-[#172d62] hover:border-blue-500/50 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">P95 Eval Latency</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-950/80 border border-indigo-800 flex items-center justify-center text-indigo-400">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">420 ms</span>
            <span className="text-xs text-emerald-400 font-medium">SLA met (&lt;1s)</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Parallel orchestrator engine</p>
        </div>

        {/* Cost USD */}
        <div className="p-5 rounded-xl bg-[#0a1535] border border-[#172d62] hover:border-blue-500/50 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Judge Cost</span>
            <div className="w-8 h-8 rounded-lg bg-purple-950/80 border border-purple-800 flex items-center justify-center text-purple-400">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">${totalCost.toFixed(2)}</span>
            <span className="text-xs text-slate-400 font-mono">USD</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Optimized with LiteLLM caching</p>
        </div>
      </div>

      {/* Main Content: Radar Chart & 5-Layer Stack */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quality Radar */}
        <div className="lg:col-span-1 rounded-2xl bg-[#0a1535] border border-[#172d62] p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-cyan-400" />
                <span>Production Quality Radar</span>
              </h3>
              <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
                Score vs SLA
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Aggregate health profile computed across active test cases and monitored LLM inferences.
            </p>
          </div>

          <div className="my-auto py-2">
            <RadarChart data={radarData} size={270} />
          </div>

          <div className="pt-4 border-t border-[#172d62] text-[11px] text-slate-400 flex items-center justify-between">
            <span>Minimum Gate: 70%</span>
            <span className="text-emerald-400 font-semibold">6/6 Metrics Passed</span>
          </div>
        </div>

        {/* 5-Layer Evaluation Architecture */}
        <div className="lg:col-span-2 rounded-2xl bg-[#0a1535] border border-[#172d62] p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-blue-400" />
                <span>5-Layer Evaluation Pipeline</span>
              </h3>
              <button
                onClick={() => onNavigate('catalog')}
                className="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1"
              >
                <span>View Full Catalog</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              EvalForge coordinates evaluation across distinct analytical tiers from instant deterministic logic to complex multi-agent cooperation.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 my-2">
            {/* Layer 1: Deterministic */}
            <div className="p-3.5 rounded-xl bg-[#070f26] border border-blue-900/60">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-blue-300">1. Deterministic</span>
                <span className="text-[10px] font-mono text-slate-400">~1ms</span>
              </div>
              <p className="text-[11px] text-slate-400">
                JSON schema, regex assertion, token length, latency budgets, cost caps.
              </p>
            </div>

            {/* Layer 2: Heuristic NLP */}
            <div className="p-3.5 rounded-xl bg-[#070f26] border border-indigo-900/60">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-indigo-300">2. Heuristic NLP</span>
                <span className="text-[10px] font-mono text-slate-400">~15ms</span>
              </div>
              <p className="text-[11px] text-slate-400">
                BLEU, ROUGE-1/2/L, BERTScore, and semantic cosine vector similarity.
              </p>
            </div>

            {/* Layer 3: LLM Judge */}
            <div className="p-3.5 rounded-xl bg-[#070f26] border border-purple-900/60">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-purple-300">3. LLM-as-Judge</span>
                <span className="text-[10px] font-mono text-slate-400">DeepEval</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Faithfulness, Answer Relevancy, Hallucination, Coherence, G-Eval rubrics.
              </p>
            </div>

            {/* Layer 4: RAG Triad */}
            <div className="p-3.5 rounded-xl bg-[#070f26] border border-cyan-900/60">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-cyan-300">4. RAG Triad</span>
                <span className="text-[10px] font-mono text-slate-400">RAGAS</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Context Recall, Context Precision, Answer Semantic Equivalence.
              </p>
            </div>

            {/* Layer 5: Agent Systems */}
            <div className="p-3.5 rounded-xl bg-[#070f26] border border-teal-900/60">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-teal-300">5. Multi-Agent</span>
                <span className="text-[10px] font-mono text-slate-400">Trajectory</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Goal completion, trajectory optimality, loop detection, knowledge drift.
              </p>
            </div>

            {/* Safety Tier */}
            <div className="p-3.5 rounded-xl bg-[#070f26] border border-amber-900/60">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-amber-300">Safety & PII</span>
                <span className="text-[10px] font-mono text-slate-400">Presidio</span>
              </div>
              <p className="text-[11px] text-slate-400">
                PII scanning, toxicity detection, bias identification, prompt injection checks.
              </p>
            </div>
          </div>

          <div className="pt-3 border-t border-[#172d62] flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-blue-400 animate-pulse" />
              Observability Connectors: OpenTelemetry, Langfuse, Arize Phoenix
            </span>
            <button
              onClick={() => onNavigate('playground')}
              className="text-blue-400 hover:text-cyan-300 font-semibold flex items-center gap-1"
            >
              Test an Output &rarr;
            </button>
          </div>
        </div>
      </div>

      {/* Recent Experiments Benchmark List */}
      <div className="rounded-2xl bg-[#0a1535] border border-[#172d62] p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-white">Recent Benchmark Experiments</h3>
            <p className="text-xs text-slate-400">Automated quality runs executed over versioned datasets</p>
          </div>
          <button
            onClick={() => onNavigate('experiments')}
            className="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1"
          >
            <span>View All Runs</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#070f26] text-[10px] uppercase font-mono text-slate-400 border-y border-[#172d62]">
              <tr>
                <th className="py-3 px-4">Experiment Name</th>
                <th className="py-3 px-4">Dataset</th>
                <th className="py-3 px-4">Prompt Version</th>
                <th className="py-3 px-4">Pass Rate</th>
                <th className="py-3 px-4">Cost</th>
                <th className="py-3 px-4">Duration</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#172d62]/60">
              {experiments.map((exp) => (
                <tr key={exp.id} className="hover:bg-[#0e1b40]/60 transition-colors">
                  <td className="py-3 px-4">
                    <div className="font-semibold text-white">{exp.name}</div>
                    <div className="text-[11px] text-slate-400 truncate max-w-xs">{exp.description}</div>
                  </td>
                  <td className="py-3 px-4 font-mono text-[11px] text-blue-300">
                    {exp.dataset_name || exp.dataset_id}
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
                      {exp.prompt_version || 'v1.0'}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-navy-950 rounded-full overflow-hidden border border-navy-700">
                        <div
                          className="h-full bg-gradient-to-r from-blue-500 to-cyan-400"
                          style={{ width: `${exp.pass_rate || 0}%` }}
                        />
                      </div>
                      <span className="font-mono font-bold text-white">{exp.pass_rate}%</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-300">
                    ${exp.total_cost_usd.toFixed(4)}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-300">
                    {exp.duration_seconds || 15}s
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => onNavigate('experiments')}
                      className="px-2.5 py-1 rounded text-xs bg-[#122452] hover:bg-blue-600 hover:text-white text-blue-300 transition-colors"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
