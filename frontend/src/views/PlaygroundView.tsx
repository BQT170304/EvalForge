import React, { useState } from 'react';
import { EvaluationResponse, MetricInfo, SingleEvaluationRequest } from '../types';
import { PLAYGROUND_TEMPLATES } from '../data/mockData';
import { api } from '../services/api';
import { MetricResultCard } from '../components/MetricResultCard';
import { RadarChart } from '../components/RadarChart';
import {
  Zap,
  CheckCircle2,
  XCircle,
  Clock,
  DollarSign,
  Plus,
  Trash2,
  Code2,
  Sliders,
  Sparkles,
  Layers,
  Copy,
  Check,
} from 'lucide-react';

interface PlaygroundViewProps {
  metricsCatalog: MetricInfo[];
}

export const PlaygroundView: React.FC<PlaygroundViewProps> = ({ metricsCatalog }) => {
  // Initial state loaded from Template 0
  const initialTemplate = PLAYGROUND_TEMPLATES[0];

  const [inputQuery, setInputQuery] = useState(initialTemplate.data.input);
  const [modelOutput, setModelOutput] = useState(initialTemplate.data.output);
  const [expectedOutput, setExpectedOutput] = useState(initialTemplate.data.expected_output || '');
  const [contextChunks, setContextChunks] = useState<string[]>(initialTemplate.data.context || []);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(initialTemplate.data.metrics);
  const [thresholds, setThresholds] = useState<Record<string, number>>(
    initialTemplate.data.thresholds || {}
  );
  const [parameters, setParameters] = useState<Record<string, Record<string, unknown>>>(
    initialTemplate.data.parameters || {}
  );

  const [loading, setLoading] = useState(false);
  const [evalResult, setEvalResult] = useState<EvaluationResponse | null>(null);
  const [showJsonRaw, setShowJsonRaw] = useState(false);
  const [activeCategoryFilter, setActiveCategoryFilter] = useState<string>('all');
  const [copied, setCopied] = useState(false);

  // Group metrics by category
  const categories = [
    'all',
    'deterministic',
    'heuristic',
    'llm_judge',
    'rag',
    'agent',
    'safety',
  ];

  const filteredMetrics =
    activeCategoryFilter === 'all'
      ? metricsCatalog
      : metricsCatalog.filter(
          (m) => m.category.toLowerCase() === activeCategoryFilter.toLowerCase()
        );

  const handleApplyTemplate = (templateIndex: number) => {
    const t = PLAYGROUND_TEMPLATES[templateIndex];
    setInputQuery(t.data.input);
    setModelOutput(t.data.output);
    setExpectedOutput(t.data.expected_output || '');
    setContextChunks(t.data.context || []);
    setSelectedMetrics(t.data.metrics);
    setThresholds(t.data.thresholds || {});
    setParameters(t.data.parameters || {});
    setEvalResult(null);
  };

  const handleToggleMetric = (metricName: string) => {
    if (selectedMetrics.includes(metricName)) {
      setSelectedMetrics(selectedMetrics.filter((m) => m !== metricName));
    } else {
      setSelectedMetrics([...selectedMetrics, metricName]);
      const def = metricsCatalog.find((m) => m.name === metricName);
      if (def && thresholds[metricName] === undefined) {
        setThresholds({ ...thresholds, [metricName]: def.default_threshold });
      }
    }
  };

  const handleThresholdChange = (metricName: string, val: number) => {
    setThresholds({
      ...thresholds,
      [metricName]: val,
    });
  };

  const handleAddContextChunk = () => {
    setContextChunks([...contextChunks, '']);
  };

  const handleUpdateContextChunk = (index: number, val: string) => {
    const updated = [...contextChunks];
    updated[index] = val;
    setContextChunks(updated);
  };

  const handleRemoveContextChunk = (index: number) => {
    setContextChunks(contextChunks.filter((_, i) => i !== index));
  };

  const handleRunEvaluation = async () => {
    if (!inputQuery.trim() || !modelOutput.trim() || selectedMetrics.length === 0) {
      alert('Please provide prompt input, model output, and at least one metric.');
      return;
    }

    setLoading(true);
    const payload: SingleEvaluationRequest = {
      input: inputQuery,
      output: modelOutput,
      expected_output: expectedOutput.trim() ? expectedOutput : undefined,
      context: contextChunks.filter((c) => c.trim().length > 0),
      metrics: selectedMetrics,
      thresholds,
      parameters,
    };

    try {
      const res = await api.evaluateSingle(payload);
      setEvalResult(res);
    } catch (err: any) {
      alert(`Evaluation failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyJson = () => {
    if (evalResult) {
      navigator.clipboard.writeText(JSON.stringify(evalResult, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Prepare radar data from evalResult
  const radarData = evalResult
    ? evalResult.results.map((r) => ({
        label: r.metric_name,
        value: r.score,
        threshold: r.threshold,
      }))
    : [];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Template Quick Switcher */}
      <div className="rounded-xl bg-[#091433] border border-[#162a5c] p-3 flex items-center justify-between gap-4 overflow-x-auto">
        <div className="flex items-center gap-2 shrink-0">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-semibold text-slate-200">Pre-built Scenarios:</span>
        </div>
        <div className="flex items-center gap-2">
          {PLAYGROUND_TEMPLATES.map((t, idx) => (
            <button
              key={idx}
              onClick={() => handleApplyTemplate(idx)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-[#0e1f4d] hover:bg-blue-600 hover:text-white text-slate-300 border border-[#1c397c] transition-all shrink-0"
            >
              {t.name}
            </button>
          ))}
        </div>
      </div>

      {/* Main 2-Column Evaluation Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Inputs & Metric Selection (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          {/* Inputs Card */}
          <div className="rounded-2xl bg-[#0a1535] border border-[#172d62] p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-400" />
              <span>Evaluation Inputs</span>
            </h3>

            {/* User Prompt / Input */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                User Query / Prompt <span className="text-rose-400">*</span>
              </label>
              <textarea
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                rows={2}
                placeholder="Enter prompt or user question..."
                className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-slate-100 text-xs font-mono focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {/* Model Output to be Evaluated */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                LLM Output / Candidate Response <span className="text-rose-400">*</span>
              </label>
              <textarea
                value={modelOutput}
                onChange={(e) => setModelOutput(e.target.value)}
                rows={3}
                placeholder="Enter the LLM output to evaluate..."
                className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-slate-100 text-xs font-mono focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {/* Expected Ground Truth Output */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center justify-between">
                <span>Expected Ground Truth (Optional)</span>
                <span className="text-[10px] text-slate-400 font-mono">Used for BLEU, ROUGE, BERTScore</span>
              </label>
              <textarea
                value={expectedOutput}
                onChange={(e) => setExpectedOutput(e.target.value)}
                rows={2}
                placeholder="Target reference output (optional)..."
                className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-slate-100 text-xs font-mono focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {/* Retrieved Context Chunks (RAG) */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                  <span>Knowledge Context Chunks ({contextChunks.length})</span>
                  <span className="text-[10px] text-slate-400 font-mono">Required for RAG Triad & Faithfulness</span>
                </label>
                <button
                  onClick={handleAddContextChunk}
                  className="flex items-center gap-1 text-xs text-blue-400 hover:text-cyan-300 font-medium transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Chunk</span>
                </button>
              </div>

              {contextChunks.length === 0 ? (
                <div className="p-3 rounded-xl bg-[#060e24] border border-dashed border-[#1a346f] text-center text-xs text-slate-400">
                  No context chunks added. RAG metrics will assume contextless inference.
                </div>
              ) : (
                contextChunks.map((chunk, idx) => (
                  <div key={idx} className="flex gap-2 items-start">
                    <textarea
                      value={chunk}
                      onChange={(e) => handleUpdateContextChunk(idx, e.target.value)}
                      rows={2}
                      placeholder={`Retrieved Context Chunk #${idx + 1}...`}
                      className="flex-1 px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-slate-100 text-xs font-mono focus:outline-none focus:border-blue-500 transition-colors"
                    />
                    <button
                      onClick={() => handleRemoveContextChunk(idx)}
                      className="p-2 rounded-lg bg-navy-950 hover:bg-rose-950/80 text-slate-400 hover:text-rose-400 border border-navy-800 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Metric Selector & Threshold Tuning Card */}
          <div className="rounded-2xl bg-[#0a1535] border border-[#172d62] p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-cyan-400" />
                  <span>Metrics Selection & Thresholds</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Select checks to execute in parallel ({selectedMetrics.length} selected)
                </p>
              </div>

              <div className="flex items-center gap-1 bg-[#060e24] p-1 rounded-lg border border-[#1a346f]">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setActiveCategoryFilter(cat)}
                    className={`px-2 py-1 rounded text-[10px] font-mono capitalize transition-all ${
                      activeCategoryFilter === cat
                        ? 'bg-blue-600 text-white font-semibold shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* Metrics Chips Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-72 overflow-y-auto pr-1">
              {filteredMetrics.map((metric) => {
                const isSelected = selectedMetrics.includes(metric.name);
                const currentThreshold = thresholds[metric.name] ?? metric.default_threshold;

                return (
                  <div
                    key={metric.name}
                    className={`p-2.5 rounded-xl border transition-all ${
                      isSelected
                        ? 'bg-[#0e214d] border-blue-500/60 shadow-[0_0_10px_rgba(59,130,246,0.2)]'
                        : 'bg-[#060e24] border-[#162d61] hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <label className="flex items-start gap-2 cursor-pointer flex-1">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleMetric(metric.name)}
                          className="mt-0.5 rounded bg-navy-950 border-navy-700 text-blue-600 focus:ring-blue-500"
                        />
                        <div>
                          <div className="font-mono text-xs font-semibold text-slate-200">
                            {metric.name}
                          </div>
                          <div className="text-[10px] text-slate-400 line-clamp-1">
                            {metric.description}
                          </div>
                        </div>
                      </label>

                      <span className="text-[9px] px-1.5 py-0.5 rounded font-mono uppercase bg-navy-950 text-slate-400 border border-navy-800">
                        {metric.category}
                      </span>
                    </div>

                    {/* Threshold slider when metric is selected */}
                    {isSelected && (
                      <div className="mt-2 pt-2 border-t border-navy-700/60 flex items-center justify-between gap-2">
                        <span className="text-[10px] text-slate-400 font-mono">Threshold:</span>
                        <input
                          type="range"
                          min="0.1"
                          max="1.0"
                          step="0.05"
                          value={currentThreshold}
                          onChange={(e) =>
                            handleThresholdChange(metric.name, parseFloat(e.target.value))
                          }
                          className="w-24 h-1 bg-navy-950 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                        />
                        <span className="text-[10px] font-mono font-bold text-cyan-300 w-8 text-right">
                          {(currentThreshold * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Run Button */}
            <div className="pt-3 border-t border-[#172d62] flex items-center justify-between">
              <div className="text-xs text-slate-400">
                <span>{selectedMetrics.length} metrics configured</span>
              </div>

              <button
                onClick={handleRunEvaluation}
                disabled={loading}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-semibold text-sm shadow-glow transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Evaluating In Parallel...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 fill-current" />
                    <span>Execute Evaluation</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Live Results & Radar Profile (5 cols) */}
        <div className="lg:col-span-5 space-y-5">
          {!evalResult && !loading && (
            <div className="h-full min-h-[480px] rounded-2xl bg-[#0a1535] border border-dashed border-[#172d62] flex flex-col items-center justify-center p-8 text-center">
              <div className="w-16 h-16 rounded-2xl bg-[#0e214d] border border-blue-800/60 flex items-center justify-center text-blue-400 mb-4 shadow-glow-sm">
                <Zap className="w-8 h-8" />
              </div>
              <h4 className="text-base font-bold text-white mb-1">Playground Awaiting Execution</h4>
              <p className="text-xs text-slate-400 max-w-sm">
                Select your desired metrics on the left and click <strong>Execute Evaluation</strong> to run
                instant parallel checks and view the live radar profile.
              </p>
            </div>
          )}

          {loading && (
            <div className="h-full min-h-[480px] rounded-2xl bg-[#0a1535] border border-[#172d62] flex flex-col items-center justify-center p-8 text-center space-y-4">
              <div className="w-16 h-16 rounded-full border-4 border-blue-600 border-t-cyan-400 animate-spin flex items-center justify-center shadow-glow" />
              <div>
                <h4 className="text-base font-bold text-white">Evaluating Test Case</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Executing deterministic, NLP, and LLM judge pipelines in parallel...
                </p>
              </div>
            </div>
          )}

          {evalResult && !loading && (
            <div className="space-y-4">
              {/* Overall Banner */}
              <div
                className={`p-5 rounded-2xl border transition-all ${
                  evalResult.overall_passed
                    ? 'bg-gradient-to-br from-[#082035] via-[#091f3c] to-[#0a1535] border-emerald-500/50 shadow-[0_0_20px_rgba(16,185,129,0.2)]'
                    : 'bg-gradient-to-br from-[#270e1c] via-[#210e1f] to-[#0a1535] border-rose-500/50 shadow-[0_0_20px_rgba(244,63,94,0.2)]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                        evalResult.overall_passed
                          ? 'bg-emerald-950 border border-emerald-600 text-emerald-400'
                          : 'bg-rose-950 border border-rose-600 text-rose-400'
                      }`}
                    >
                      {evalResult.overall_passed ? (
                        <CheckCircle2 className="w-6 h-6" />
                      ) : (
                        <XCircle className="w-6 h-6" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-base font-bold text-white">
                          {evalResult.overall_passed ? 'EVALUATION PASSED' : 'ASSERTIONS FAILED'}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-navy-950 text-slate-300 border border-navy-800">
                          {evalResult.eval_id}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 mt-0.5">
                        {evalResult.results.filter((r) => r.passed).length} of{' '}
                        {evalResult.results.length} metrics met or exceeded threshold
                      </p>
                    </div>
                  </div>

                  <div className="text-right font-mono">
                    <div className="text-2xl font-black text-white">
                      {Math.round(evalResult.average_score * 100)}%
                    </div>
                    <span className="text-[10px] text-slate-400 uppercase">Avg Score</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-4 pt-3 border-t border-navy-800/80">
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
                    <Clock className="w-3.5 h-3.5 text-blue-400" />
                    <span>Total Latency: {evalResult.latency_ms}ms</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
                    <DollarSign className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Total Cost: ${evalResult.total_cost_usd.toFixed(4)}</span>
                  </div>
                </div>
              </div>

              {/* Radar Profile Card */}
              {radarData.length >= 3 && (
                <div className="p-4 rounded-2xl bg-[#0a1535] border border-[#172d62]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-white">Evaluation Radar Profile</span>
                    <span className="text-[10px] font-mono text-slate-400">Score vs Required SLA</span>
                  </div>
                  <RadarChart data={radarData} size={250} />
                </div>
              )}

              {/* Individual Metric Result Cards */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-400 px-1">
                  <span>Metric Breakdown ({evalResult.results.length})</span>
                  <button
                    onClick={() => setShowJsonRaw(!showJsonRaw)}
                    className="flex items-center gap-1 text-blue-400 hover:text-cyan-300 transition-colors"
                  >
                    <Code2 className="w-3.5 h-3.5" />
                    <span>{showJsonRaw ? 'Hide JSON' : 'View Raw JSON'}</span>
                  </button>
                </div>

                {showJsonRaw && (
                  <div className="relative p-3 rounded-xl bg-navy-950 border border-navy-800 text-[11px] font-mono text-slate-300 max-h-60 overflow-y-auto">
                    <button
                      onClick={handleCopyJson}
                      className="absolute top-2 right-2 p-1.5 rounded bg-[#102047] hover:bg-blue-600 text-slate-300 hover:text-white transition-colors"
                      title="Copy JSON"
                    >
                      {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                    <pre>{JSON.stringify(evalResult, null, 2)}</pre>
                  </div>
                )}

                {evalResult.results.map((r, idx) => (
                  <MetricResultCard key={idx} result={r} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
