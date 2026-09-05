import React, { useState } from 'react';
import { Dataset, DatasetCreate } from '../types';
import { api } from '../services/api';
import {
  Database,
  Plus,
  Search,
  Download,
  Tag,
  Calendar,
  Sparkles,
} from 'lucide-react';

interface DatasetsViewProps {
  datasets: Dataset[];
  onRefresh: () => void;
}

export const DatasetsView: React.FC<DatasetsViewProps> = ({ datasets, onRefresh }) => {
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(
    datasets.length > 0 ? datasets[0] : null
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showSyntheticModal, setShowSyntheticModal] = useState(false);

  // New dataset form state
  const [newName, setNewName] = useState('');
  const [newVersion, setNewVersion] = useState('1.0.0');
  const [newDescription, setNewDescription] = useState('');
  const [newTags, setNewTags] = useState('production, rag, evaluation');

  // Synthetic generation form state
  const [domainDescription, setDomainDescription] = useState('Enterprise customer support QA with refund and account security policies');
  const [sampleCount, setSampleCount] = useState(5);
  const [generating, setGenerating] = useState(false);

  const filteredDatasets = datasets.filter(
    (d) =>
      d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleCreateDataset = async () => {
    if (!newName.trim()) {
      alert('Please provide a dataset name.');
      return;
    }

    const payload: DatasetCreate = {
      name: newName.trim(),
      version: newVersion.trim() || '1.0.0',
      description: newDescription.trim() || undefined,
      tags: newTags.split(',').map((t) => t.trim()).filter(Boolean),
      entries: [
        {
          input: 'Sample query for newly created benchmark dataset',
          expected_output: 'Expected target answer verified by domain expert',
          context: ['Grounding reference chunk 1'],
        },
      ],
    };

    try {
      const created = await api.createDataset(payload);
      setShowCreateModal(false);
      setNewName('');
      setNewDescription('');
      onRefresh();
      setSelectedDataset(created);
    } catch (err: any) {
      alert(`Failed to create dataset: ${err.message}`);
    }
  };

  const handleGenerateSynthetic = async () => {
    setGenerating(true);
    // Simulate or call synthetic generator
    setTimeout(() => {
      setGenerating(false);
      setShowSyntheticModal(false);
      alert(`Synthesized ${sampleCount} golden test cases for: ${domainDescription}`);
    }, 1500);
  };

  const handleExportJson = (dataset: Dataset) => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(dataset, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${dataset.name.toLowerCase().replace(/\s+/g, '_')}_v${dataset.version}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top action row */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search datasets or tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-[#0a1535] border border-[#172d62] text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={() => setShowSyntheticModal(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#0f214d] hover:bg-[#152e69] text-cyan-300 text-xs font-semibold border border-cyan-500/30 transition-all shadow-glow-sm"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>Generate Synthetic Data</span>
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-glow transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Dataset</span>
          </button>
        </div>
      </div>

      {/* 2-Column Layout: Dataset Cards on Left, Entry Inspector on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Dataset List (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="text-xs font-mono text-slate-400 uppercase tracking-wider px-1">
            Registered Datasets ({filteredDatasets.length})
          </div>

          {filteredDatasets.map((dataset) => {
            const isSelected = selectedDataset?.id === dataset.id;
            return (
              <div
                key={dataset.id}
                onClick={() => setSelectedDataset(dataset)}
                className={`p-4 rounded-xl border cursor-pointer transition-all duration-150 ${
                  isSelected
                    ? 'bg-[#0d1e49] border-blue-500/80 shadow-[0_0_15px_rgba(59,130,246,0.25)]'
                    : 'bg-[#0a1535] border-[#172d62] hover:bg-[#0e1d45] hover:border-blue-700/60'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="font-semibold text-sm text-white">{dataset.name}</h4>
                    <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">
                      {dataset.description || 'No description provided.'}
                    </p>
                  </div>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 shrink-0">
                    v{dataset.version}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 flex-wrap mt-3">
                  {dataset.tags.map((tag) => (
                    <span
                      key={tag}
                      className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-navy-950 text-slate-300 border border-navy-800 flex items-center gap-1"
                    >
                      <Tag className="w-2.5 h-2.5 text-blue-400" />
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="mt-3 pt-2.5 border-t border-navy-800/80 flex items-center justify-between text-[11px] text-slate-400">
                  <span className="font-mono text-slate-300">
                    {dataset.entry_count} test cases
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-slate-400" />
                    {new Date(dataset.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Dataset Details & Test Cases (7 cols) */}
        <div className="lg:col-span-7">
          {selectedDataset ? (
            <div className="rounded-2xl bg-[#0a1535] border border-[#172d62] p-5 space-y-4">
              <div className="flex items-start justify-between gap-3 border-b border-[#172d62] pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white">{selectedDataset.name}</h3>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                      v{selectedDataset.version}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-1">{selectedDataset.description}</p>
                </div>

                <button
                  onClick={() => handleExportJson(selectedDataset)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0e1d44] hover:bg-blue-600 hover:text-white text-xs font-mono text-blue-300 border border-[#1d3774] transition-colors shrink-0"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Export JSON</span>
                </button>
              </div>

              {/* Entries count & list */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-slate-200">
                    Test Cases / Ground Truth Pairs ({selectedDataset.entries?.length || selectedDataset.entry_count})
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    ID: {selectedDataset.id}
                  </span>
                </div>

                <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                  {selectedDataset.entries && selectedDataset.entries.length > 0 ? (
                    selectedDataset.entries.map((entry, idx) => (
                      <div
                        key={entry.id || idx}
                        className="p-3.5 rounded-xl bg-[#060e24] border border-[#162d61] space-y-2 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-blue-400">
                            #{idx + 1}
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {entry.context?.length ? `${entry.context.length} Context Chunks` : 'No Context'}
                          </span>
                        </div>

                        <div>
                          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">
                            Input Prompt:
                          </div>
                          <div className="font-mono text-slate-200 bg-navy-950 p-2 rounded-lg border border-navy-800">
                            {entry.input}
                          </div>
                        </div>

                        {entry.expected_output && (
                          <div>
                            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">
                              Expected Output (Ground Truth):
                            </div>
                            <div className="font-mono text-emerald-300 bg-emerald-950/30 p-2 rounded-lg border border-emerald-900/50">
                              {entry.expected_output}
                            </div>
                          </div>
                        )}

                        {entry.context && entry.context.length > 0 && (
                          <div>
                            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">
                              Grounding Context:
                            </div>
                            <div className="font-mono text-cyan-200/90 bg-cyan-950/20 p-2 rounded-lg border border-cyan-900/40 text-[11px]">
                              {entry.context[0]}
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="p-8 text-center rounded-xl bg-[#060e24] border border-dashed border-navy-800 text-slate-400 text-xs">
                      No sample entries pre-loaded in this view. Dataset contains {selectedDataset.entry_count} test cases in database.
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[400px] rounded-2xl bg-[#0a1535] border border-dashed border-[#172d62] flex items-center justify-center p-8 text-slate-400 text-xs">
              Select a dataset on the left to inspect its test cases and schemas.
            </div>
          )}
        </div>
      </div>

      {/* New Dataset Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-md rounded-2xl bg-[#0a1535] border border-[#1b3674] p-6 space-y-4 shadow-glow">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-blue-400" />
              <span>Create Evaluation Dataset</span>
            </h3>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Dataset Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Legal Contract Q&A Triad"
                className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Version</label>
                <input
                  type="text"
                  value={newVersion}
                  onChange={(e) => setNewVersion(e.target.value)}
                  placeholder="1.0.0"
                  className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Tags</label>
                <input
                  type="text"
                  value={newTags}
                  onChange={(e) => setNewTags(e.target.value)}
                  placeholder="rag, contract, safety"
                  className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
              <textarea
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                rows={2}
                placeholder="Target evaluation criteria and application scope..."
                className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#172d62]">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateDataset}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white shadow-glow transition-all"
              >
                Create Dataset
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Synthetic Data Generation Modal */}
      {showSyntheticModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl bg-[#0a1535] border border-[#1b3674] p-6 space-y-4 shadow-glow">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>Synthetic Ground Truth Generator</span>
            </h3>
            <p className="text-xs text-slate-400">
              EvalForge leverages LLMs to generate high-diversity, adversarial, or domain-targeted
              evaluation test cases with verified ground truth facts.
            </p>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Domain Description</label>
              <textarea
                value={domainDescription}
                onChange={(e) => setDomainDescription(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 rounded-xl bg-[#060e24] border border-[#1a346f] text-xs text-white focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Number of Samples to Generate ({sampleCount})
              </label>
              <input
                type="range"
                min="1"
                max="25"
                value={sampleCount}
                onChange={(e) => setSampleCount(parseInt(e.target.value))}
                className="w-full h-1.5 bg-navy-950 rounded-lg appearance-none cursor-pointer accent-cyan-400"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#172d62]">
              <button
                onClick={() => setShowSyntheticModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerateSynthetic}
                disabled={generating}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-glow transition-all"
              >
                {generating ? 'Generating Samples...' : 'Run Generator'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
