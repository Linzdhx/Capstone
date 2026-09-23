import React from 'react';
import { Cpu, HardDrive, Zap } from 'lucide-react';
import { SystemTelemetry } from '../types';

interface SystemMonitorProps {
  system: SystemTelemetry;
}

export const SystemMonitor: React.FC<SystemMonitorProps> = ({ system }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* CPU Card */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Cpu size={16} className="text-blue-400" />
            <span className="text-xs font-semibold text-slate-300">CPU Usage</span>
          </div>
          <span className="text-xs font-mono text-slate-400">{system.cpu.cores} Cores</span>
        </div>
        <div className="flex items-baseline justify-between mb-2">
          <span className="text-xl font-bold font-mono text-slate-100">{system.cpu.percent}%</span>
          <span className="text-xs text-slate-400">Procesador</span>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              system.cpu.percent > 85 ? 'bg-rose-500' : system.cpu.percent > 60 ? 'bg-amber-500' : 'bg-blue-500'
            }`}
            style={{ width: `${Math.min(100, system.cpu.percent)}%` }}
          />
        </div>
      </div>

      {/* RAM Card */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <HardDrive size={16} className="text-indigo-400" />
            <span className="text-xs font-semibold text-slate-300">RAM System</span>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {system.ram.used_gb} / {system.ram.total_gb} GB
          </span>
        </div>
        <div className="flex items-baseline justify-between mb-2">
          <span className="text-xl font-bold font-mono text-slate-100">{system.ram.percent}%</span>
          <span className="text-xs text-slate-400">Memoria física</span>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              system.ram.percent > 85 ? 'bg-rose-500' : 'bg-indigo-500'
            }`}
            style={{ width: `${Math.min(100, system.ram.percent)}%` }}
          />
        </div>
      </div>

      {/* GPU RTX 3060 Card */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Zap size={16} className="text-emerald-400" />
            <span className="text-xs font-semibold text-slate-300">GPU Acceleration</span>
          </div>
          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold ${
            system.gpu.available ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'
          }`}>
            {system.gpu.available ? 'CUDA ACTIVE' : 'CPU FALLBACK'}
          </span>
        </div>
        <div className="flex items-baseline justify-between mb-1">
          <span className="text-sm font-semibold text-slate-200 truncate max-w-[200px]" title={system.gpu.name}>
            {system.gpu.name}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-2">
          <span>VRAM: {system.gpu.vram_allocated_mb} MB</span>
          <span>Reservada: {system.gpu.vram_reserved_mb} MB</span>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className="h-full bg-emerald-500 transition-all duration-300"
            style={{
              width: `${system.gpu.vram_total_mb > 0 ? (system.gpu.vram_allocated_mb / system.gpu.vram_total_mb) * 100 : 15}%`
            }}
          />
        </div>
      </div>
    </div>
  );
};
