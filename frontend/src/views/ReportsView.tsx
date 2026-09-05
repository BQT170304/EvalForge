import React, { useEffect, useState } from 'react';
import { Experiment } from '../types';
import { api } from '../services/api';
import {
  FileText,
  Download,
  Copy,
  Check,
  RefreshCw,
} from 'lucide-react';

interface ReportsViewProps {
  experiments: Experiment[];
  selectedExpId?: string;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  experiments,
  selectedExpId,
}) => {
  const [currentExpId, setCurrentExpId] = useState<string>(
    selectedExpId || (experiments.length > 0 ? experiments[0].id : '')
  );
  const [reportMarkdown, setReportMarkdown] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (selectedExpId) {
      setCurrentExpId(selectedExpId);
    }
  }, [selectedExpId]);

  useEffect(() => {
    if (currentExpId) {
      fetchReport(currentExpId);
    }
  }, [currentExpId]);

  const fetchReport = async (id: string) => {
    setLoading(true);
    try {
      const md = await api.getExperimentReport(id);
      setReportMarkdown(md);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(reportMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const exp = experiments.find((e) => e.id === currentExpId);
    const filename = `EvalForge_Report_${exp?.name.replace(/\s+/g, '_') || 'Run'}.md`;
    const blob = new Blob([reportMarkdown], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const currentExp = experiments.find((e) => e.id === currentExpId);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header Controls */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-400" />
            <span>Evaluation Reports & Executive Summaries</span>
          </h3>
          <p className="text-xs text-slate-400">
            Export audit-ready compliance and accuracy logs for production deployments
          </p>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <select
            value={currentExpId}
            onChange={(e) => setCurrentExpId(e.target.value)}
            className="flex-1 md:w-72 px-3 py-2 rounded-xl bg-[#0a1535] border border-[#172d62] text-xs font-mono text-white focus:outline-none focus:border-blue-500"
          >
            {experiments.map((exp) => (
              <option key={exp.id} value={exp.id}>
                {exp.name} ({exp.pass_rate}%)
              </option>
            ))}
          </select>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#0e214d] hover:bg-blue-600 text-slate-200 hover:text-white text-xs font-medium border border-blue-800 transition-colors shrink-0"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-glow transition-all shrink-0"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download .MD</span>
          </button>
        </div>
      </div>

      {/* Report Container */}
      <div className="rounded-2xl bg-[#0a1535] border border-[#172d62] p-6">
        {loading ? (
          <div className="py-24 flex flex-col items-center justify-center text-slate-400 space-y-3">
            <RefreshCw className="w-8 h-8 text-blue-400 animate-spin" />
            <p className="text-xs">Generating formatted Markdown report...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Quick Summary Strip */}
            {currentExp && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl bg-[#060e24] border border-[#162d61]">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Dataset</div>
                  <div className="text-xs font-bold text-white mt-0.5 truncate">
                    {currentExp.dataset_name || currentExp.dataset_id}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Pass Rate</div>
                  <div className="text-xs font-bold text-emerald-400 mt-0.5 font-mono">
                    {currentExp.pass_rate}% Passed
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Total Cases</div>
                  <div className="text-xs font-bold text-cyan-300 mt-0.5 font-mono">
                    {currentExp.total_entries} test cases
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Judge Model</div>
                  <div className="text-xs font-bold text-purple-300 mt-0.5 font-mono">
                    {currentExp.judge_model || 'gpt-4o'}
                  </div>
                </div>
              </div>
            )}

            {/* Markdown Text / Code Render */}
            <div className="p-6 rounded-xl bg-[#060d22] border border-[#142654] font-mono text-xs text-slate-200 whitespace-pre-wrap leading-relaxed overflow-x-auto shadow-inner">
              {reportMarkdown}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
