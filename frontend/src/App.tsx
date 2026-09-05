import React, { useEffect, useState } from 'react';
import { ActiveTab, Dataset, Experiment, MetricInfo, SystemHealth } from './types';
import { METRICS_CATALOG, MOCK_DATASETS, MOCK_EXPERIMENTS } from './data/mockData';
import { api } from './services/api';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { OverviewView } from './views/OverviewView';
import { PlaygroundView } from './views/PlaygroundView';
import { DatasetsView } from './views/DatasetsView';
import { ExperimentsView } from './views/ExperimentsView';
import { ComparisonView } from './views/ComparisonView';
import { CatalogView } from './views/CatalogView';
import { ReportsView } from './views/ReportsView';
import { SettingsView } from './views/SettingsView';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [health, setHealth] = useState<SystemHealth>({
    status: 'healthy',
    service: 'EvalForge',
    version: '0.1.0',
    environment: 'development',
    is_mock: false,
  });

  const [metrics, setMetrics] = useState<MetricInfo[]>(METRICS_CATALOG);
  const [datasets, setDatasets] = useState<Dataset[]>(MOCK_DATASETS);
  const [experiments, setExperiments] = useState<Experiment[]>(MOCK_EXPERIMENTS);

  const [reportExpId, setReportExpId] = useState<string | undefined>(undefined);
  const [compareExpIds, setCompareExpIds] = useState<string[]>([]);

  // Initial load
  useEffect(() => {
    refreshHealth();
    loadAllData();
  }, []);

  const refreshHealth = async () => {
    const h = await api.checkHealth();
    setHealth(h);
  };

  const loadAllData = async () => {
    try {
      const [m, d, e] = await Promise.all([
        api.getMetrics(),
        api.getDatasets(),
        api.getExperiments(),
      ]);
      setMetrics(m);
      setDatasets(d);
      setExperiments(e);
    } catch (err) {
      console.error('Error fetching application state:', err);
    }
  };

  const handleTestMetricInPlayground = (_metricName: string) => {
    setActiveTab('playground');
  };

  const handleViewReport = (expId: string) => {
    setReportExpId(expId);
    setActiveTab('reports');
  };

  const handleCompare = (expIds: string[]) => {
    setCompareExpIds(expIds);
    setActiveTab('compare');
  };

  return (
    <div className="flex h-screen w-screen bg-[#060d1f] text-slate-100 overflow-hidden font-sans">
      {/* Dark Blue Sidebar */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} health={health} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-mesh-dark">
        {/* Sticky Header */}
        <Header
          activeTab={activeTab}
          health={health}
          onRefreshHealth={refreshHealth}
          onOpenSettings={() => setActiveTab('settings')}
          onLaunchPlayground={() => setActiveTab('playground')}
        />

        {/* Dynamic View Container */}
        <main className="flex-1 overflow-y-auto">
          {activeTab === 'overview' && (
            <OverviewView
              onNavigate={setActiveTab}
              experiments={experiments}
              metrics={metrics}
            />
          )}

          {activeTab === 'playground' && (
            <PlaygroundView metricsCatalog={metrics} />
          )}

          {activeTab === 'datasets' && (
            <DatasetsView datasets={datasets} onRefresh={loadAllData} />
          )}

          {activeTab === 'experiments' && (
            <ExperimentsView
              experiments={experiments}
              datasets={datasets}
              metricsCatalog={metrics}
              onRefresh={loadAllData}
              onViewReport={handleViewReport}
              onCompare={handleCompare}
            />
          )}

          {activeTab === 'compare' && (
            <ComparisonView
              experiments={experiments}
              selectedExpIds={compareExpIds}
              onSelectExps={setCompareExpIds}
            />
          )}

          {activeTab === 'catalog' && (
            <CatalogView
              metrics={metrics}
              onTestMetricInPlayground={handleTestMetricInPlayground}
            />
          )}

          {activeTab === 'reports' && (
            <ReportsView
              experiments={experiments}
              selectedExpId={reportExpId}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsView health={health} onRefreshHealth={refreshHealth} />
          )}
        </main>
      </div>
    </div>
  );
};
