import React, { useState } from 'react';
import { Dataset, Experiment, ExperimentCreate, MetricInfo } from '../types';
import { api } from '../services/api';
import {
  FlaskConical,
  Plus,
  FileText,
  GitCompare,
} from 'lucide-react';

interface ExperimentsViewProps {
  experiments: Experiment[];
  datasets: Dataset[];
  metricsCatalog: MetricInfo[];
  onRefresh: () => void;
  onViewReport: (expId: string) => void;
  onCompare: (expIds: string[]) => void;
}

export const ExperimentsView: React.FC<ExperimentsViewProps> = ({
  experiments,
  datasets,
  metricsCatalog,
  onRefresh,
  onViewReport,
  onCompare,
}) => {
  const [selectedExp, setSelectedExp] = useState<Experiment | null>(
    experiments.length > 0 ? experiments[0] : null
  );
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);

  // New Experiment Form
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [datasetId, setDatasetId] = useState(datasets[0]?.id || '');
  const [judgeModel, setJudgeModel] = useState('gpt-4o');
  const [targetModel, setTargetModel] = useState('gpt-4o-mini');
  const [promptVersion, setPromptVersion] = useState('v2.1-grounded');
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([
    'faithfulness',
    'answer_relevancy',
    'context_precision',
    'hallucination',
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleToggleCompareSelection = (id: string) => {
    if (selectedForCompare.includes(id)) {
      setSelectedForCompare(selectedForCompare.filter((i) => i !== id));
    } else {
      if (selectedForCompare.length >= 3) {
        alert('You can compare at most 3 experiments at a time.');
        return;
      }
      setSelectedForCompare([...selectedForCompare, id]);
    }
  };

  const handleTriggerCompare = () => {
    if (selectedForCompare.length < 2) {
      alert('Please select at least 2 experiments to compare.');
      return;
    }
    onCompare(selectedForCompare);
  };

  const handleCreateExperiment = async () => {
    if (!name.trim() || !datasetId || selectedMetrics.length === 0) {
      alert('Please provide an experiment name, dataset, and at least one metric.');
      return;
    }

    setIsSubmitting(true);
    const payload: ExperimentCreate = {
      name,
      description,
      dataset_id: datasetId,
      judge_model: judgeModel,
      target_model: targetModel,
      prompt_version: promptVersion,
      metrics: selectedMetrics,
    };

    try {
      const exp = await api.createExperiment(payload);
      setShowCreateModal(false);
      setName('');
      setDescription('');
      onRefresh();
      setSelectedExp(exp);
    } catch (err: any) {
      alert(`Failed to create experiment: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-blue-400" />
            <span>Benchmark Experiments & Regressions</span>
          </h3>
          <p className="text-xs text-slate-400">
            Batch evaluation runs tracking regression trends and prompt updates across versioned datasets
          </p>
        </div>

        <div className="flex items-center gap-3">
          {selectedForCompare.length >= 2 && (
            <button
              onClick={handleTriggerCompare}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-glow-cyan transition-all"
            >
              <GitCompare className="w-4 h-4" />
              <span>Compare Selected ({selectedForCompare.length})</span>
            </button>
          )}

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-glow transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Experiment</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Experiments Table + Selected Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Table List (7 cols) */}
        <div className="lg:col-span-7 rounded-2xl bg-[#0a1535] border border-[#172d62] overflow-hidden">
          <div className="p-4 border-b border-[#172d62] flex items-center justify-between">
            <span className="text-xs font-semibold text-white">All Experiment Runs</span>
            <span className="text-[11px] text-slate-400 font-mono">
              {experiments.length} runs recorded
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-[#070f26] text-[10px] uppercase font-mono text-slate-400 border-b border-[#172d62]">
                <tr>
                  <th className="py-2.5 px-3 w-8">Diff</th>
                  <th className="py-2.5 px-3">Experiment</th>
                  <th className="py-2.5 px-3">Model / Prompt</th>
                  <th className="py-2.5 px-3">Pass Rate</th>
                  <th className="py-2.5 px-3">Cost</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#172d62]/60">
                {experiments.map((exp) => {
                  const isSelected = selectedExp?.id === exp.id;
                  const isCheckedForCompare = selectedForCompare.includes(exp.id);

                  return (
                    <tr
                      key={exp.id}
                      onClick={() => setSelectedExp(exp)}
                      className={`cursor-pointer transition-colors ${
                        isSelected ? 'bg-[#0f2354]' : 'hover:bg-[#0c1a42]'
                      }`}
                    >
                      <td className="py-3 px-3" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isCheckedForCompare}
                          onChange={() => handleToggleCompareSelection(exp.id)}
                          className="rounded bg-navy-950 border-navy-700 text-cyan-500 focus:ring-cyan-400"
                        />
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-semibold text-white">{exp.name}</div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {exp.dataset_name || exp.dataset_id}
                        </div>
                      </td>
                      <td className="py-3 px-3 font-mono text-[11px]">
                        <div className="text-slate-200">{exp.target_model || 'gpt-4o'}</div>
                        <div className="text-blue-400 text-[10px]">{exp.prompt_version || 'v1.0'}</div>
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-14 h-1.5 bg-navy-950 rounded-full overflow-hidden border border-navy-800">
                            <div
                              className="h-full bg-gradient-to-r from-blue-500 to-cyan-400"
                              style={{ width: `${exp.pass_rate || 0}%` }}
                            />
                          </div>
                          <span className="font-mono font-bold text-white">
                            {exp.pass_rate || 0}%
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-3 font-mono text-[11px] text-slate-300">
                        ${exp.total_cost_usd.toFixed(4)}
                      </td>
                      <td className="py-3 px-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => onViewReport(exp.id)}
                          className="px-2 py-1 rounded text-[11px] bg-[#0c1a40] hover:bg-blue-600 text-blue-300 hover:text-white border border-[#1a3572] transition-colors"
                          title="Generate Markdown Report"
                        >
                          Report
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Experiment Drilldown (5 cols) */}
        <div className="lg:col-span-5">
          {selectedExp ? (
            <div className="rounded-2xl bg-[#0a1535] border border-[#172d62] p-5 space-y-5">
              <div className="flex items-start justify-between border-b border-[#172d62] pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-white text-base">{selectedExp.name}</h4>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                      {selectedExp.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{selectedExp.description}</p>
                </div>

                <button
                  onClick={() => onViewReport(selectedExp.id)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-glow-sm transition-all"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Report</span>
                </button>
              </div>

              {/* Stat badges */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 rounded-xl bg-[#060e24] border border-[#152a5c] text-center">
                  <span className="text-[10px] text-slate-400 uppercase font-mono">Pass Rate</span>
                  <div className="text-xl font-bold font-mono text-white mt-0.5">
                    {selectedExp.pass_rate}%
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-[#060e24] border border-[#152a5c] text-center">
                  <span className="text-[10px] text-slate-400 uppercase font-mono">Cases</span>
                  <div className="text-xl font-bold font-mono text-cyan-300 mt-0.5">
                    {selectedExp.passed_entries} / {selectedExp.total_entries}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-[#060e24] border border-[#152a5c] text-center">
                  <span className="text-[10px] text-slate-400 uppercase font-mono">Cost (USD)</span>
                  <div className="text-xl font-bold font-mono text-emerald-400 mt-0.5">
                    ${selectedExp.total_cost_usd.toFixed(4)}
                  </div>
                </div>
              </div>

              {/* Metric Breakdown Progress Bars */}
              <div className="space-y-3">
                <span className="text-xs font-semibold text-slate-300">
                  Aggregate Metric Scores
                </span>

                {selectedExp.summary_scores &&
                  Object.entries(selectedExp.summary_scores).map(([metric, score]) => {
                    const pct = Math.round(score * 100);
                    return (
                      <div
                        key={metric}
                        className="p-3 rounded-xl bg-[#060e24] border border-[#152a5c] space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-xs font-mono">
                          <span className="font-semibold text-slate-200">{metric}</span>
                          <span className="font-bold text-cyan-300">{pct}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-navy-950 rounded-full overflow-hidden border border-navy-800">
                          <div
                            className="h-full bg-gradient-to-r from-blue-600 via-blue-400 to-cyan-400"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>

              {/* Execution Metadata */}
              <div className="pt-3 border-t border-[#172d62] text-[11px] font-mono text-slate-400 space-y-1">
                <div>Judge Model: <span className="text-slate-200">{selectedExp.judge_model || 'gpt-4o'}</span></div>
                <div>Target Model: <span className="text-slate-200">{selectedExp.target_model || 'gpt-4o'}</span></div>
                <div>Prompt Version: <span className="text-blue-300">{selectedExp.prompt_version || 'v1.0'}</span></div>
                <div>Executed at: {new Date(selectedExp.created_at).toLocaleString()}</div>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[400px] rounded-2xl bg-[#0a1535] border border-dashed border-[#172d62] flex items-center justify-center p-8 text-slate-400 text-xs">
              Select an experiment on the left to inspect metric distributions.
            </div>
          )}
        </div>
      </div>

      {/* New Experiment Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl bg-[#0a1535] border border-[#1b3674] p-6 space-y-4 shadow-glow">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <FlaskConical className="w-4 h-4 text-blue-400" />
              <span>Launch New Benchmark Experiment</span>
            </h3>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Experiment Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Prompt v3.0 CoT Reasoning Benchmark"
                className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Target Dataset</label>
                <select
                  value={datasetId}
                  onChange={(e) => setDatasetId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-xs text-white focus:outline-none focus:border-blue-500"
                >
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.entry_count} cases)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Prompt Version</label>
                <input
                  type="text"
                  value={promptVersion}
                  onChange={(e) => setPromptVersion(e.target.value)}
                  placeholder="v2.1-grounded"
                  className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Judge Model</label>
                <select
                  value={judgeModel}
                  onChange={(e) => setJudgeModel(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-xs text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="gpt-4o">gpt-4o (OpenAI)</option>
                  <option value="claude-3-5-sonnet">claude-3-5-sonnet (Anthropic)</option>
                  <option value="gemini-1.5-pro">gemini-1.5-pro (Google)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Target Model</label>
                <input
                  type="text"
                  value={targetModel}
                  onChange={(e) => setTargetModel(e.target.value)}
                  placeholder="gpt-4o-mini"
                  className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Evaluation Metrics ({selectedMetrics.length} active)
              </label>
              <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto p-1 bg-[#060e24] rounded-xl border border-[#1a346f]">
                {metricsCatalog.map((m) => {
                  const isSel = selectedMetrics.includes(m.name);
                  return (
                    <button
                      key={m.name}
                      type="button"
                      onClick={() =>
                        setSelectedMetrics(
                          isSel ? selectedMetrics.filter((x) => x !== m.name) : [...selectedMetrics, m.name]
                        )
                      }
                      className={`text-[11px] font-mono px-2 py-1 rounded-lg border transition-all ${
                        isSel
                          ? 'bg-blue-600 text-white border-blue-400'
                          : 'bg-navy-950 text-slate-400 border-navy-800 hover:text-slate-200'
                      }`}
                    >
                      {m.name}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#172d62]">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateExperiment}
                disabled={isSubmitting}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white shadow-glow transition-all disabled:opacity-50"
              >
                {isSubmitting ? 'Enqueuing Run...' : 'Execute Experiment'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
