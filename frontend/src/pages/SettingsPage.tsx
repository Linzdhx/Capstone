import React from 'react';
import { Settings, ShieldCheck, Terminal, HardDrive, Info } from 'lucide-react';
import { TelemetryMessage } from '../types';

interface SettingsPageProps {
  telemetry: TelemetryMessage | null;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ telemetry }) => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100">Configuración del Sistema & Entorno</h2>
        <p className="text-xs text-slate-400 mt-1">
          Parámetros globales desacoplados de `.env` y `configs/app_config.yaml`
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Rutas y Archivos del Proyecto */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
            <HardDrive size={16} className="text-blue-400" />
            <h3 className="font-semibold text-xs text-slate-100">Rutas de Modelos & Datos</h3>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">Modelo Producción:</span>
              <span className="text-slate-200">models/production/best.pt</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">Modelos Candidatos:</span>
              <span className="text-slate-200">models/candidates/</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">Modelos Archivados:</span>
              <span className="text-slate-200">models/archive/</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400">Dataset Active Learning:</span>
              <span className="text-slate-200">data/ (collected, pending, approved)</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-slate-400">Registro de Alertas:</span>
              <span className="text-slate-200">alerts/logs/alerts.jsonl</span>
            </div>
          </div>
        </div>

        {/* Seguridad & RTSP */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
            <ShieldCheck size={16} className="text-emerald-400" />
            <h3 className="font-semibold text-xs text-slate-100">Seguridad & Aislamiento de Credenciales</h3>
          </div>

          <div className="space-y-3 text-xs text-slate-300">
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <h4 className="font-semibold text-slate-200 mb-1">Cámaras IP / RTSP:</h4>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Las credenciales de acceso a cámaras IP se mantienen estrictamente en el backend dentro de <code className="text-blue-400">.env</code>.
                Nunca se serializan en respuestas de API hacia el cliente.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <h4 className="font-semibold text-slate-200 mb-1">Desacoplamiento de Inferencia:</h4>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                El reentrenamiento y evaluación corren en hilos/procesos independientes para asegurar cero interrupciones de FPS en el visor.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Info de Hardware */}
      {telemetry?.system && (
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
            <Terminal size={16} className="text-purple-400" />
            <h3 className="font-semibold text-xs text-slate-100">Entorno de Ejecución</h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-500 block text-[10px]">DISPOSITIVO GPU</span>
              <span className="text-slate-200 font-bold">{telemetry.system.gpu.name}</span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-500 block text-[10px]">ACELERACIÓN CUDA</span>
              <span className="text-emerald-400 font-bold">
                {telemetry.system.gpu.available ? 'HABILITADA (PyTorch)' : 'DESHABILITADA'}
              </span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-500 block text-[10px]">CPU CORES / MEMORIA</span>
              <span className="text-slate-200 font-bold">
                {telemetry.system.cpu.cores} núcleos / {telemetry.system.ram.total_gb} GB RAM
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
