import React from 'react';
import { 
  LayoutDashboard, 
  Camera, 
  AlertTriangle, 
  Database, 
  Cpu, 
  Boxes, 
  Settings, 
  Radio
} from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { AppState } from '../types';

export type TabKey = 'dashboard' | 'camera' | 'alerts' | 'dataset' | 'training' | 'models' | 'settings';

interface NavbarProps {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
  systemState: AppState;
  hasActiveAlert: boolean;
  wsConnected: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  systemState,
  hasActiveAlert,
  wsConnected,
}) => {
  const tabs: { key: TabKey; label: string; icon: React.ReactNode; alertBadge?: boolean }[] = [
    { key: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
    { key: 'camera', label: 'Cámara en Vivo', icon: <Camera size={18} /> },
    { key: 'alerts', label: 'Alertas', icon: <AlertTriangle size={18} />, alertBadge: hasActiveAlert },
    { key: 'dataset', label: 'Active Learning', icon: <Database size={18} /> },
    { key: 'training', label: 'Entrenamiento', icon: <Cpu size={18} /> },
    { key: 'models', label: 'Modelos', icon: <Boxes size={18} /> },
    { key: 'settings', label: 'Configuración', icon: <Settings size={18} /> },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#0B0F17]/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Boxes className="text-white" size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-100 text-lg tracking-tight">CVW Inventory</span>
                <span className="text-[10px] font-mono font-semibold bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/20">YOLOv8</span>
              </div>
              <p className="text-[11px] text-slate-400">Monitoreo en Tiempo Real</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => onTabChange(tab.key)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm shadow-blue-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                  {tab.alertBadge && (
                    <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                  )}
                </button>
              );
            })}
          </nav>

          {/* Right Status */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs font-mono text-slate-400 bg-slate-900/60 px-2.5 py-1 rounded-md border border-slate-800">
              <Radio size={12} className={wsConnected ? 'text-emerald-400 animate-pulse' : 'text-slate-600'} />
              <span>{wsConnected ? 'LIVE' : 'RECONNECTING'}</span>
            </div>
            <StatusBadge state={systemState} size="sm" />
          </div>
        </div>
      </div>

      {/* Mobile nav */}
      <div className="md:hidden flex overflow-x-auto px-4 py-2 border-t border-slate-800/60 gap-1 bg-[#0e131d]">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => onTabChange(tab.key)}
            className={`flex items-center gap-1.5 whitespace-nowrap px-3 py-1.5 rounded-lg text-xs font-medium ${
              activeTab === tab.key
                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>
    </header>
  );
};
