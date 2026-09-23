import React, { useState } from 'react';
import { Navbar, TabKey } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { CameraPage } from './pages/CameraPage';
import { AlertsPage } from './pages/AlertsPage';
import { DatasetReviewPage } from './pages/DatasetReviewPage';
import { TrainingPage } from './pages/TrainingPage';
import { ModelsPage } from './pages/ModelsPage';
import { SettingsPage } from './pages/SettingsPage';
import { useTelemetry } from './hooks/useTelemetry';
import { AppState } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('dashboard');
  const { data: telemetry, isConnected: wsConnected } = useTelemetry();

  // Calcular el estado global del sistema
  const computeSystemState = (): AppState => {
    if (!telemetry || !wsConnected) return 'DISCONNECTED';
    if (telemetry.alert.is_active) return 'ALERT';
    if (telemetry.camera.status === 'CONNECTED') return 'RUNNING';
    return 'CONNECTED';
  };

  const systemState = computeSystemState();
  const hasActiveAlert = Boolean(telemetry?.alert?.is_active);

  return (
    <div className="min-h-screen bg-[#070A0F] text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Barra de Navegación Principal */}
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        systemState={systemState}
        hasActiveAlert={hasActiveAlert}
        wsConnected={wsConnected}
      />

      {/* Contenido Principal de las Páginas */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' && (
          <DashboardPage telemetry={telemetry} onNavigate={setActiveTab} />
        )}
        {activeTab === 'camera' && (
          <CameraPage telemetry={telemetry} />
        )}
        {activeTab === 'alerts' && (
          <AlertsPage telemetry={telemetry} />
        )}
        {activeTab === 'dataset' && (
          <DatasetReviewPage />
        )}
        {activeTab === 'training' && (
          <TrainingPage />
        )}
        {activeTab === 'models' && (
          <ModelsPage />
        )}
        {activeTab === 'settings' && (
          <SettingsPage telemetry={telemetry} />
        )}
      </main>

      {/* Footer Estilizado */}
      <footer className="border-t border-slate-900 bg-[#06090e] py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>CVW Inventory Monitor v1.0.0 • YOLOv8 Empty Spaces Roboflow v3</span>
          <span className="font-mono text-[11px] text-slate-600">
            PyTorch • FastAPI • React + TypeScript • TailwindCSS
          </span>
        </div>
      </footer>
    </div>
  );
};

export default App;
