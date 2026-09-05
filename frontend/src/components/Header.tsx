import React from 'react';
import { ActiveTab, SystemHealth } from '../types';
import { Key, Shield, Zap, RefreshCw } from 'lucide-react';

interface HeaderProps {
  activeTab: ActiveTab;
  health: SystemHealth;
  onRefreshHealth: () => void;
  onOpenSettings: () => void;
  onLaunchPlayground: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  health,
  onRefreshHealth,
  onOpenSettings,
  onLaunchPlayground,
}) => {
  const getTabTitle = (tab: ActiveTab) => {
    switch (tab) {
      case 'overview':
        return { title: 'Observability & Metrics Overview', subtitle: 'Live health, evaluation throughput, and quality radar' };
      case 'playground':
        return { title: 'Evaluation Playground', subtitle: 'Synchronous interactive evaluation across 25+ deterministic & LLM metrics' };
      case 'datasets':
        return { title: 'Datasets & Ground Truth', subtitle: 'Manage curated test cases, context collections, and synthetic sample generation' };
      case 'experiments':
        return { title: 'Experiments & Benchmark Runs', subtitle: 'Track regression runs, pass rates, and metric trajectories across prompt versions' };
      case 'compare':
        return { title: 'Experiment Diff & Model Comparator', subtitle: 'Side-by-side benchmark comparison between models or prompt versions' };
      case 'catalog':
        return { title: 'Metrics Catalog', subtitle: 'Full registry of deterministic, heuristic, LLM judge, RAG, and agent metrics' };
      case 'reports':
        return { title: 'Evaluation Reports', subtitle: 'Executive summaries, compliance logs, and markdown exports' };
      case 'settings':
        return { title: 'Settings & Microservice Config', subtitle: 'API endpoint URLs, authentication headers, and environment parameters' };
    }
  };

  const { title, subtitle } = getTabTitle(activeTab);

  return (
    <header className="h-16 bg-[#070f26]/80 backdrop-blur-md border-b border-[#152754] px-6 flex items-center justify-between shrink-0 sticky top-0 z-20">
      <div>
        <h1 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
          {title}
        </h1>
        <p className="text-xs text-slate-400">{subtitle}</p>
      </div>

      <div className="flex items-center gap-3">
        {/* Quick Launch Playground button */}
        {activeTab !== 'playground' && (
          <button
            onClick={onLaunchPlayground}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white transition-all shadow-[0_0_12px_rgba(37,99,235,0.35)]"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>New Eval</span>
          </button>
        )}

        {/* Backend health pill */}
        <div
          onClick={onRefreshHealth}
          title="Click to re-verify backend connectivity"
          className="cursor-pointer flex items-center gap-2 px-2.5 py-1 rounded-lg text-xs font-mono bg-[#0c183a] border border-[#1b3470] hover:border-blue-500 transition-colors"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              health.status === 'healthy' ? 'bg-emerald-400 shadow-[0_0_6px_#10b981]' : 'bg-amber-400 shadow-[0_0_6px_#f59e0b]'
            }`}
          />
          <span className="text-slate-300">
            {health.is_mock ? 'Mock Mode' : 'Connected'}
          </span>
          <RefreshCw className="w-3 h-3 text-slate-400 hover:text-white" />
        </div>

        {/* API Key settings button */}
        <button
          onClick={onOpenSettings}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs bg-[#0c183a] hover:bg-[#122252] border border-[#1b3470] text-slate-300 hover:text-white transition-colors"
          title="Manage API Key and Endpoints"
        >
          <Key className="w-3.5 h-3.5 text-blue-400" />
          <span className="hidden sm:inline">API Key</span>
        </button>

        {/* Environment Badge */}
        <span className="hidden md:inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-blue-950 text-blue-300 border border-blue-800">
          <Shield className="w-3 h-3 text-cyan-400" />
          {health.environment}
        </span>
      </div>
    </header>
  );
};
