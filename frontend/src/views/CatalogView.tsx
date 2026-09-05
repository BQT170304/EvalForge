import React, { useState } from 'react';
import { MetricInfo } from '../types';
import {
  BookOpen,
  Search,
  Zap,
} from 'lucide-react';

interface CatalogViewProps {
  metrics: MetricInfo[];
  onTestMetricInPlayground: (metricName: string) => void;
}

export const CatalogView: React.FC<CatalogViewProps> = ({
  metrics,
  onTestMetricInPlayground,
}) => {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const categories = [
    'all',
    'deterministic',
    'heuristic',
    'llm_judge',
    'rag',
    'agent',
    'safety',
  ];

  const filtered = metrics.filter((m) => {
    const matchesSearch =
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.description.toLowerCase().includes(search.toLowerCase());
    const matchesCat =
      selectedCategory === 'all' || m.category.toLowerCase() === selectedCategory.toLowerCase();
    return matchesSearch && matchesCat;
  });

  const getCategoryBadgeClass = (category: string) => {
    switch (category.toLowerCase()) {
      case 'deterministic':
        return 'bg-blue-950 text-blue-300 border-blue-800';
      case 'heuristic':
        return 'bg-indigo-950 text-indigo-300 border-indigo-800';
      case 'llm_judge':
        return 'bg-purple-950 text-purple-300 border-purple-800';
      case 'rag':
        return 'bg-cyan-950 text-cyan-300 border-cyan-800';
      case 'agent':
        return 'bg-teal-950 text-teal-300 border-teal-800';
      case 'safety':
        return 'bg-amber-950 text-amber-300 border-amber-800';
      default:
        return 'bg-slate-900 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header & Search */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-blue-400" />
            <span>Metrics Registry & Documentation</span>
          </h3>
          <p className="text-xs text-slate-400">
            Comprehensive catalog of built-in, DeepEval, RAGAS, and custom agent evaluation metrics
          </p>
        </div>

        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search metric name or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-xl bg-[#0a1535] border border-[#172d62] text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Category Filter Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-mono capitalize transition-all shrink-0 ${
              selectedCategory === cat
                ? 'bg-blue-600 text-white font-semibold shadow-glow-sm border border-blue-400'
                : 'bg-[#0a1535] text-slate-400 border border-[#172d62] hover:text-white'
            }`}
          >
            {cat} {cat === 'all' ? `(${metrics.length})` : ''}
          </button>
        ))}
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((metric) => (
          <div
            key={metric.name}
            className="p-5 rounded-2xl bg-[#0a1535] border border-[#172d62] hover:border-blue-500/60 hover:shadow-glow-sm transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <span className="font-mono text-sm font-bold text-white">
                  {metric.name}
                </span>
                <span
                  className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-full border font-semibold ${getCategoryBadgeClass(
                    metric.category
                  )}`}
                >
                  {metric.category}
                </span>
              </div>

              <p className="text-xs text-slate-300 line-clamp-3 mb-4">
                {metric.description}
              </p>

              {/* Requirements tags */}
              <div className="space-y-1.5 text-[11px] font-mono text-slate-400 mb-4">
                <div className="flex items-center justify-between py-1 border-t border-navy-800/60">
                  <span>Engine Source:</span>
                  <span className="text-slate-200 capitalize">{metric.source}</span>
                </div>
                <div className="flex items-center justify-between py-1 border-t border-navy-800/60">
                  <span>Default Threshold:</span>
                  <span className="text-cyan-300 font-bold">
                    {(metric.default_threshold * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center justify-between py-1 border-t border-navy-800/60">
                  <span>Requires Context:</span>
                  <span className={metric.requires_context ? 'text-cyan-300 font-semibold' : 'text-slate-500'}>
                    {metric.requires_context ? 'Yes (RAG)' : 'No'}
                  </span>
                </div>
                <div className="flex items-center justify-between py-1 border-t border-navy-800/60">
                  <span>Requires Ground Truth:</span>
                  <span className={metric.requires_expected_output ? 'text-indigo-300 font-semibold' : 'text-slate-500'}>
                    {metric.requires_expected_output ? 'Yes' : 'No'}
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={() => onTestMetricInPlayground(metric.name)}
              className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-[#0e214d] hover:bg-blue-600 text-blue-300 hover:text-white text-xs font-semibold border border-blue-800/60 transition-colors"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Test in Playground</span>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
