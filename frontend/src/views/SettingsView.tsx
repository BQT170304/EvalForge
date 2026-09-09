import React, { useState } from 'react';
import { ApiSettings, getApiSettings, saveApiSettings } from '../services/api';
import { SystemHealth } from '../types';
import {
  Settings,
  Server,
  Radio,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Eye,
  EyeOff,
  Palette,
  Activity,
} from 'lucide-react';

interface SettingsViewProps {
  health: SystemHealth;
  onRefreshHealth: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ health, onRefreshHealth }) => {
  const [settings, setSettings] = useState<ApiSettings>(getApiSettings());
  const [showKey, setShowKey] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; msg: string } | null>(null);

  const handleSave = () => {
    saveApiSettings(settings);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
    onRefreshHealth();
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      saveApiSettings(settings);
      const res = await fetch(`${settings.baseUrl.replace(/\/+$/, '')}/health`, {
        headers: {
          'X-API-Key': settings.apiKey,
        },
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        const json = await res.json();
        setTestResult({
          success: true,
          msg: `Connected to ${json.service || 'EvalForge'} (v${json.version || '0.1.0'}) in ${json.environment || 'development'} mode`,
        });
      } else {
        setTestResult({
          success: false,
          msg: `Backend responded with HTTP ${res.status}. Check your API Key or prefix.`,
        });
      }
    } catch (err: any) {
      setTestResult({
        success: false,
        msg: `Unable to reach ${settings.baseUrl}. If backend is not running, enable Simulation Mode below.`,
      });
    } finally {
      setTesting(false);
      onRefreshHealth();
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div>
        <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
          <Settings className="w-5 h-5 text-blue-400" />
          <span>Microservice Configuration & Connection</span>
        </h3>
        <p className="text-xs text-slate-400">
          Configure API connection endpoints, authentication headers, and runtime environment
        </p>
      </div>

      {/* Connection & Auth Card */}
      <div className="rounded-2xl bg-[#0a1535] border border-[#172d62] p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-[#172d62] pb-4">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-cyan-400" />
            <h4 className="text-sm font-semibold text-white">FastAPI Backend Connection</h4>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                health.status === 'healthy' ? 'bg-emerald-400 shadow-[0_0_8px_#10b981]' : 'bg-amber-400'
              }`}
            />
            <span className="text-slate-300">
              {health.status === 'healthy' ? 'Online' : 'Offline / Preview'}
            </span>
          </div>
        </div>

        {/* Base URL */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            API Base URL / Endpoint Prefix
          </label>
          <input
            type="text"
            value={settings.baseUrl}
            onChange={(e) => setSettings({ ...settings, baseUrl: e.target.value })}
            placeholder="/api/v1 or http://localhost:8080/api/v1"
            className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-xs font-mono text-white focus:outline-none focus:border-blue-500"
          />
          <p className="text-[11px] text-slate-400 mt-1">
            Default: <code className="text-blue-300">/api/v1</code> (via Vite dev proxy) or direct host <code className="text-blue-300">http://localhost:8080/api/v1</code>
          </p>
        </div>

        {/* API Key */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center justify-between">
            <span>X-API-Key Header</span>
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="text-[11px] text-blue-400 hover:text-blue-300 flex items-center gap-1 font-mono"
            >
              {showKey ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
              <span>{showKey ? 'Hide' : 'Show'}</span>
            </button>
          </label>
          <div className="relative">
            <input
              type={showKey ? 'text' : 'password'}
              value={settings.apiKey}
              onChange={(e) => setSettings({ ...settings, apiKey: e.target.value })}
              placeholder="dev-key-change-me"
              className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-xs font-mono text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Matches <code className="text-blue-300">EVALFORGE_API_KEY</code> configured in backend .env
          </p>
        </div>

        {/* Simulation / Force Mock Toggle */}
        <div className="p-4 rounded-xl bg-[#060e24] border border-[#152a5c] flex items-center justify-between gap-4">
          <div>
            <div className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-cyan-400" />
              <span>Simulation / Demo Mode</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Enable offline mock execution if running without active Redis, PostgreSQL, or LLM judge credentials.
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer shrink-0">
            <input
              type="checkbox"
              checked={settings.forceMock}
              onChange={(e) => setSettings({ ...settings, forceMock: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-navy-950 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600 border border-navy-700"></div>
          </label>
        </div>

        {/* Test Connection Results */}
        {testResult && (
          <div
            className={`p-3 rounded-xl border text-xs flex items-center gap-2 ${
              testResult.success
                ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300'
                : 'bg-amber-950/40 border-amber-800 text-amber-300'
            }`}
          >
            {testResult.success ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            ) : (
              <XCircle className="w-4 h-4 shrink-0 text-amber-400" />
            )}
            <span>{testResult.msg}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-3 border-t border-[#172d62]">
          <button
            onClick={handleTestConnection}
            disabled={testing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#0e214d] hover:bg-[#142d66] text-xs font-mono text-cyan-300 border border-cyan-500/30 transition-colors"
          >
            {testing ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Activity className="w-3.5 h-3.5" />
            )}
            <span>Test API Connectivity</span>
          </button>

          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-glow transition-all"
          >
            {savedSuccess ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                <span>Settings Saved!</span>
              </>
            ) : (
              <span>Save Configuration</span>
            )}
          </button>
        </div>
      </div>

      {/* Theme Customizer & Design Info */}
      <div className="rounded-2xl bg-[#0a1535] border border-[#172d62] p-6 space-y-4">
        <div className="flex items-center gap-2 border-b border-[#172d62] pb-3">
          <Palette className="w-4 h-4 text-blue-400" />
          <h4 className="text-sm font-semibold text-white">Visual Theme & Aesthetics</h4>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-200">Main Color Palette</div>
            <p className="text-[11px] text-slate-400">
              Dark theme with dark blue tones (#060d1f / #0a1535) and vibrant electric cyan accents.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-[#060d1f] border border-blue-500 shadow-glow-sm" title="Deep Navy Void #060d1f" />
            <div className="w-6 h-6 rounded-full bg-[#0a1535] border border-blue-700" title="Card Navy #0a1535" />
            <div className="w-6 h-6 rounded-full bg-[#2563eb] border border-blue-400" title="Brand Blue #2563eb" />
            <div className="w-6 h-6 rounded-full bg-[#38bdf8] border border-cyan-400" title="Electric Cyan #38bdf8" />
          </div>
        </div>
      </div>
    </div>
  );
};
