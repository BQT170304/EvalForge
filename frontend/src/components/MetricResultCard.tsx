import React, { useState } from 'react';
import { MetricScoreResponse } from '../types';
import { CheckCircle2, XCircle, Clock, DollarSign, ChevronDown, ChevronUp, Layers } from 'lucide-react';

interface MetricResultCardProps {
  result: MetricScoreResponse;
}

export const MetricResultCard: React.FC<MetricResultCardProps> = ({ result }) => {
  const [expanded, setExpanded] = useState(false);

  const getCategoryColor = (category: string) => {
    switch (category.toLowerCase()) {
      case 'deterministic':
        return 'bg-blue-950/80 text-blue-300 border-blue-800/60';
      case 'heuristic':
        return 'bg-indigo-950/80 text-indigo-300 border-indigo-800/60';
      case 'llm_judge':
        return 'bg-purple-950/80 text-purple-300 border-purple-800/60';
      case 'rag':
        return 'bg-cyan-950/80 text-cyan-300 border-cyan-800/60';
      case 'agent':
        return 'bg-teal-950/80 text-teal-300 border-teal-800/60';
      case 'safety':
        return 'bg-amber-950/80 text-amber-300 border-amber-800/60';
      default:
        return 'bg-slate-900 text-slate-300 border-slate-700';
    }
  };

  const getSourceBadge = (source: string) => {
    switch (source.toLowerCase()) {
      case 'deepeval':
        return 'bg-blue-900/40 text-blue-300 border border-blue-700/40';
      case 'ragas':
        return 'bg-cyan-900/40 text-cyan-300 border border-cyan-700/40';
      case 'builtin':
        return 'bg-slate-800 text-slate-300 border border-slate-700';
      default:
        return 'bg-blue-950 text-blue-400 border border-blue-800/50';
    }
  };

  const scorePercentage = Math.round(result.score * 100);
  const thresholdPercentage = Math.round(result.threshold * 100);

  return (
    <div
      className={`rounded-xl transition-all duration-200 border ${
        result.passed
          ? 'bg-[#0a1532]/90 border-blue-900/60 hover:border-blue-500/50 hover:shadow-glow-sm'
          : 'bg-[#150e20]/90 border-rose-900/60 hover:border-rose-500/50'
      }`}
    >
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className="font-mono font-semibold text-slate-100 text-sm">
                {result.metric_name}
              </span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full border font-medium uppercase tracking-wider ${getCategoryColor(
                  result.category
                )}`}
              >
                {result.category}
              </span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${getSourceBadge(
                  result.source
                )}`}
              >
                {result.source}
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-1 line-clamp-2">{result.reason}</p>
          </div>

          <div className="flex flex-col items-end">
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                result.passed
                  ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 shadow-[0_0_10px_rgba(16,185,129,0.15)]'
                  : 'bg-rose-950/80 text-rose-400 border border-rose-800/80 shadow-[0_0_10px_rgba(244,63,94,0.15)]'
              }`}
            >
              {result.passed ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>PASSED</span>
                </>
              ) : (
                <>
                  <XCircle className="w-3.5 h-3.5" />
                  <span>FAILED</span>
                </>
              )}
            </div>
            <div className="text-right mt-1.5 font-mono">
              <span className="text-lg font-bold text-slate-100">{scorePercentage}%</span>
              <span className="text-[10px] text-slate-400 ml-1">/ {thresholdPercentage}%</span>
            </div>
          </div>
        </div>

        {/* Score progress bar */}
        <div className="mt-3 relative pt-1">
          <div className="h-2 w-full bg-navy-950 rounded-full overflow-hidden border border-navy-700/50 relative">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                result.passed
                  ? 'bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-400 shadow-[0_0_12px_rgba(56,189,248,0.5)]'
                  : 'bg-gradient-to-r from-rose-700 to-rose-500'
              }`}
              style={{ width: `${Math.min(scorePercentage, 100)}%` }}
            />
          </div>
          {/* Threshold indicator notch */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-amber-400/90 z-10"
            style={{ left: `${thresholdPercentage}%` }}
            title={`Threshold: ${thresholdPercentage}%`}
          />
        </div>

        {/* Footer info: Latency & Cost */}
        <div className="flex items-center justify-between text-[11px] text-slate-400 mt-3 pt-2.5 border-t border-navy-800/70">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1 font-mono">
              <Clock className="w-3 h-3 text-slate-400" />
              {result.latency_ms.toFixed(0)} ms
            </span>
            <span className="flex items-center gap-1 font-mono">
              <DollarSign className="w-3 h-3 text-slate-400" />
              ${result.cost_usd.toFixed(4)}
            </span>
          </div>

          {result.details && Object.keys(result.details).length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-blue-400 hover:text-blue-300 font-medium transition-colors"
            >
              <Layers className="w-3 h-3" />
              <span>Details</span>
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          )}
        </div>

        {/* Expanded raw details JSON view */}
        {expanded && result.details && (
          <div className="mt-3 p-2.5 rounded-lg bg-navy-950 border border-navy-800 text-[11px] font-mono text-slate-300 overflow-x-auto">
            <pre>{JSON.stringify(result.details, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
};
