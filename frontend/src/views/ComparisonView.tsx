import React from 'react';
import { Experiment } from '../types';
import { api } from '../services/api';
import {
  GitCompare,
  Trophy,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';

interface ComparisonViewProps {
  experiments: Experiment[];
  selectedExpIds: string[];
  onSelectExps: (ids: string[]) => void;
}

export const ComparisonView: React.FC<ComparisonViewProps> = ({
  experiments,
  selectedExpIds,
  onSelectExps,
}) => {
  // If fewer than 2 selected, pick first two by default
  const activeIds =
    selectedExpIds.length >= 2
      ? selectedExpIds
      : experiments.slice(0, 2).map((e) => e.id);

  const comparison = api.compareExperiments(experiments, activeIds);
  const { experiments: comparedExps, metrics_comparison, winner_id } = comparison;

  const winner = comparedExps.find((e) => e.id === winner_id);

  const handleToggleExp = (id: string) => {
    if (activeIds.includes(id)) {
      if (activeIds.length <= 2) {
        alert('You must compare at least 2 experiments.');
        return;
      }
      onSelectExps(activeIds.filter((i) => i !== id));
    } else {
      if (activeIds.length >= 3) {
        alert('Maximum of 3 experiments can be compared simultaneously.');
        return;
      }
      onSelectExps([...activeIds, id]);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Banner & Selector */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-5 rounded-2xl bg-[#0a1535] border border-[#172d62]">
        <div>
          <div className="flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-cyan-400" />
            <h3 className="text-base font-bold text-white">Model & Prompt Regression Comparator</h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Compare pass rates, hallucination tolerance, and operational costs side-by-side
          </p>
        </div>

        {/* Experiment multi-selector dropdown or buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-mono text-slate-400">Comparing:</span>
          {experiments.map((exp) => {
            const isComparing = activeIds.includes(exp.id);
            return (
              <button
                key={exp.id}
                onClick={() => handleToggleExp(exp.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-mono transition-all border ${
                  isComparing
                    ? 'bg-blue-600 text-white border-blue-400 shadow-glow-sm'
                    : 'bg-[#060e24] text-slate-400 border-[#1a346f] hover:text-slate-200'
                }`}
              >
                {exp.prompt_version || exp.name.slice(0, 16)}
              </button>
            );
          })}
        </div>
      </div>

      {/* Winner Spotlight Card */}
      {winner && (
        <div className="p-5 rounded-2xl bg-gradient-to-r from-[#0d2745] via-[#0b203c] to-[#071329] border border-cyan-500/40 shadow-glow-cyan flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center text-slate-950 font-bold shadow-lg">
              <Trophy className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-semibold text-cyan-300 uppercase tracking-wider">
                  Top Performing Candidate
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-700">
                  {winner.pass_rate}% Pass Rate
                </span>
              </div>
              <h4 className="text-lg font-bold text-white mt-0.5">{winner.name}</h4>
              <p className="text-xs text-slate-300">
                Prompt Version: <strong className="font-mono text-cyan-300">{winner.prompt_version}</strong> | Model: <strong className="font-mono text-slate-200">{winner.target_model}</strong>
              </p>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-6 font-mono text-right">
            <div>
              <div className="text-xs text-slate-400">Total Cost</div>
              <div className="text-base font-bold text-white">${winner.total_cost_usd.toFixed(4)}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Duration</div>
              <div className="text-base font-bold text-white">{winner.duration_seconds}s</div>
            </div>
          </div>
        </div>
      )}

      {/* Side-by-Side Experiment Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {comparedExps.map((exp, idx) => {
          const isWinner = exp.id === winner_id;
          return (
            <div
              key={exp.id}
              className={`p-5 rounded-2xl border transition-all ${
                isWinner
                  ? 'bg-[#0b1b3d] border-cyan-500/60 shadow-[0_0_15px_rgba(6,182,212,0.2)]'
                  : 'bg-[#0a1535] border-[#172d62]'
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-3">
                <div>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-navy-950 text-slate-400 border border-navy-800">
                    Candidate #{idx + 1}
                  </span>
                  <h4 className="font-bold text-sm text-white mt-1">{exp.name}</h4>
                </div>
                {isWinner && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                    WINNER
                  </span>
                )}
              </div>

              {/* Pass Rate Gauge */}
              <div className="p-3 rounded-xl bg-[#060e24] border border-[#172d62] mb-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-400 font-mono">Pass Rate</span>
                  <span className="text-lg font-bold font-mono text-white">{exp.pass_rate}%</span>
                </div>
                <div className="h-2 w-full bg-navy-950 rounded-full overflow-hidden border border-navy-800">
                  <div
                    className={`h-full ${
                      isWinner
                        ? 'bg-gradient-to-r from-blue-500 to-cyan-400 shadow-[0_0_10px_rgba(56,189,248,0.5)]'
                        : 'bg-gradient-to-r from-slate-600 to-blue-600'
                    }`}
                    style={{ width: `${exp.pass_rate || 0}%` }}
                  />
                </div>
              </div>

              {/* Key metadata */}
              <div className="space-y-1.5 text-xs font-mono text-slate-300">
                <div className="flex justify-between py-1 border-b border-navy-800/60">
                  <span className="text-slate-400">Target Model:</span>
                  <span className="text-white">{exp.target_model || 'gpt-4o'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-navy-800/60">
                  <span className="text-slate-400">Prompt Version:</span>
                  <span className="text-cyan-300">{exp.prompt_version || 'v1.0'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-navy-800/60">
                  <span className="text-slate-400">Passed / Failed:</span>
                  <span>
                    <span className="text-emerald-400">{exp.passed_entries}</span> /{' '}
                    <span className="text-rose-400">{exp.failed_entries}</span>
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-navy-800/60">
                  <span className="text-slate-400">Cost USD:</span>
                  <span>${exp.total_cost_usd.toFixed(4)}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Duration:</span>
                  <span>{exp.duration_seconds}s</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Metric-by-Metric Delta Comparison Matrix */}
      <div className="rounded-2xl bg-[#0a1535] border border-[#172d62] p-5">
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-white">Metric-by-Metric Score Delta Matrix</h4>
          <p className="text-xs text-slate-400">
            Compare granular quality shifts across all evaluated metrics
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#070f26] text-[10px] uppercase font-mono text-slate-400 border-y border-[#172d62]">
              <tr>
                <th className="py-3 px-4">Metric Name</th>
                {comparedExps.map((e) => (
                  <th key={e.id} className="py-3 px-4">
                    {e.prompt_version || e.name}
                  </th>
                ))}
                <th className="py-3 px-4 text-right">Delta Shift</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#172d62]/60 font-mono">
              {Object.entries(metrics_comparison).map(([metricName, item]) => {
                const scoresList = comparedExps.map((e) => item.scores[e.id] ?? 0);
                const first = scoresList[0] || 0;
                const last = scoresList[scoresList.length - 1] || 0;
                const diff = Math.round((last - first) * 1000) / 10;

                return (
                  <tr key={metricName} className="hover:bg-[#0c193e] transition-colors">
                    <td className="py-3 px-4 font-semibold text-white">{metricName}</td>
                    {scoresList.map((sc, i) => (
                      <td key={i} className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-100">{(sc * 100).toFixed(1)}%</span>
                        </div>
                      </td>
                    ))}
                    <td className="py-3 px-4 text-right">
                      {comparedExps.length >= 2 && (
                        <span
                          className={`inline-flex items-center gap-1 font-bold ${
                            diff > 0
                              ? 'text-emerald-400'
                              : diff < 0
                              ? 'text-rose-400'
                              : 'text-slate-400'
                          }`}
                        >
                          {diff > 0 ? (
                            <>
                              <TrendingUp className="w-3.5 h-3.5" />
                              +{diff}%
                            </>
                          ) : diff < 0 ? (
                            <>
                              <TrendingDown className="w-3.5 h-3.5" />
                              {diff}%
                            </>
                          ) : (
                            '0.0%'
                          )}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
