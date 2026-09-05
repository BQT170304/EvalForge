import React from 'react';
import { ActiveTab, SystemHealth } from '../types';
import {
  LayoutDashboard,
  Zap,
  Database,
  FlaskConical,
  GitCompare,
  BookOpen,
  FileText,
  Settings,
  Server,
  Radio,
} from 'lucide-react';

interface SidebarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  health: SystemHealth;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, health }) => {
  const navItems = [
    { id: 'overview' as ActiveTab, label: 'Overview', icon: LayoutDashboard, badge: undefined },
    { id: 'playground' as ActiveTab, label: 'Playground', icon: Zap, badge: 'Live' },
    { id: 'datasets' as ActiveTab, label: 'Datasets', icon: Database, badge: undefined },
    { id: 'experiments' as ActiveTab, label: 'Experiments', icon: FlaskConical, badge: undefined },
    { id: 'compare' as ActiveTab, label: 'Compare', icon: GitCompare, badge: 'New' },
    { id: 'catalog' as ActiveTab, label: 'Metrics Catalog', icon: BookOpen, badge: '25' },
    { id: 'reports' as ActiveTab, label: 'Reports', icon: FileText, badge: undefined },
    { id: 'settings' as ActiveTab, label: 'Settings', icon: Settings, badge: undefined },
  ];

  return (
    <aside className="w-64 bg-[#070f26] border-r border-[#152754] flex flex-col justify-between shrink-0 select-none">
      <div>
        {/* Logo and Brand */}
        <div className="p-5 border-b border-[#152754]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-900 flex items-center justify-center shadow-[0_0_18px_rgba(37,99,235,0.45)] border border-blue-400/30">
              <span className="text-xl">⚔️</span>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold tracking-tight text-white text-lg">EvalForge</span>
                <span className="text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-700/50">
                  AI EVAL
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Enterprise AI Quality Microservice</p>
            </div>
          </div>
        </div>

        {/* Navigation links */}
        <div className="px-3 py-4 space-y-1">
          <div className="px-3 pb-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider font-mono">
            Platform
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-gradient-to-r from-blue-900/90 to-blue-800/60 text-white border border-blue-500/40 shadow-[0_0_15px_rgba(59,130,246,0.25)]'
                    : 'text-slate-300 hover:text-white hover:bg-[#0e1b3d] border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-cyan-400' : 'text-slate-400 group-hover:text-blue-400'
                    }`}
                  />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded-full ${
                      isActive
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                        : 'bg-navy-800 text-slate-400 border border-navy-700'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Footer System Status */}
      <div className="p-3 m-3 rounded-xl bg-[#0b1638] border border-[#1a3068]">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Radio
              className={`w-3.5 h-3.5 ${
                health.status === 'healthy'
                  ? 'text-emerald-400 animate-pulse'
                  : 'text-amber-400'
              }`}
            />
            <span className="text-xs font-medium text-slate-200">
              {health.status === 'healthy' ? 'Core Service Active' : 'Offline / Preview'}
            </span>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            {health.latency_ms ? `${health.latency_ms}ms` : 'Local'}
          </span>
        </div>

        <div className="text-[11px] text-slate-400 flex items-center justify-between border-t border-navy-700/60 pt-2">
          <span className="flex items-center gap-1">
            <Server className="w-3 h-3 text-slate-400" />
            FastAPI + Celery
          </span>
          <span className="font-mono text-[10px] text-blue-300">v{health.version}</span>
        </div>
      </div>
    </aside>
  );
};
