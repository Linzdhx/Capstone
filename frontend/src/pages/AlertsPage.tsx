import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  Clock, 
  ShieldAlert, 
  Sliders, 
  ExternalLink, 
  X, 
  Check, 
  Image as ImageIcon 
} from 'lucide-react';
import { TelemetryMessage, AlertEvent } from '../types';
import { api } from '../services/api';

interface AlertsPageProps {
  telemetry: TelemetryMessage | null;
}

export const AlertsPage: React.FC<AlertsPageProps> = ({ telemetry }) => {
  const [history, setHistory] = useState<AlertEvent[]>([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState<AlertEvent | null>(null);
  const [threshold, setThreshold] = useState<number>(0.80);
  const [consecutive, setConsecutive] = useState<number>(3.0);
  const [cooldown, setCooldown] = useState<number>(30.0);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const loadHistory = async () => {
    try {
      const data = await api.getAlertHistory(50);
      setHistory(data);
    } catch (e) {
      console.error('Error cargando historial de alertas:', e);
    }
  };

  useEffect(() => {
    loadHistory();
    if (telemetry?.alert) {
      setThreshold(telemetry.alert.threshold);
    }
  }, []);

  const handleSaveConfig = async () => {
    try {
      await api.updateAlertConfig(threshold, consecutive, cooldown);
      setSaveMsg('Configuración de alertas actualizada');
      setTimeout(() => setSaveMsg(null), 3000);
    } catch (e) {
      setSaveMsg('Error al guardar configuración');
      setTimeout(() => setSaveMsg(null), 3000);
    }
  };

  const alertStatus = telemetry?.alert;

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Sistema de Alertas por Desabastecimiento</h2>
          <p className="text-xs text-slate-400 mt-1">
            Detección persistente de estantería vacía con ventana temporal, cooldown de seguridad y registro de snapshots
          </p>
        </div>
        {saveMsg && (
          <div className="flex items-center gap-2 bg-emerald-950 text-emerald-300 border border-emerald-800 px-3.5 py-1.5 rounded-lg text-xs font-medium">
            <Check size={14} className="text-emerald-400" />
            {saveMsg}
          </div>
        )}
      </div>

      {/* Tarjetas de Estado Actual */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className={`p-4 rounded-xl border ${
          alertStatus?.is_active
            ? 'bg-rose-950/30 border-rose-600/50 text-rose-200'
            : 'bg-slate-900/60 border-slate-800 text-slate-200'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400">Estado de Alerta</span>
            <ShieldAlert size={18} className={alertStatus?.is_active ? 'text-rose-400 animate-bounce' : 'text-slate-500'} />
          </div>
          <div className="text-xl font-bold font-mono">
            {alertStatus?.is_active ? '¡ALERTA ACTIVA!' : 'NORMAL'}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {alertStatus?.is_active
              ? 'Proporción de vacíos crítica sostenida.'
              : 'Niveles dentro de los parámetros aceptables.'}
          </p>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 text-slate-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400">Ventana Consecutiva</span>
            <Clock size={18} className="text-blue-400" />
          </div>
          <div className="text-xl font-bold font-mono text-blue-400">
            {alertStatus?.consecutive_seconds_high || 0}s / {consecutive}s
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Tiempo continuo por encima del umbral de faltantes.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 text-slate-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400">Cooldown Restante</span>
            <Clock size={18} className="text-amber-400" />
          </div>
          <div className="text-xl font-bold font-mono text-amber-400">
            {alertStatus?.cooldown_remaining_seconds || 0}s
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Tiempo de espera para prevenir spam de notificaciones.
          </p>
        </div>
      </div>

      {/* Configuración de Reglas de Alerta */}
      <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
          <Sliders size={16} className="text-blue-400" />
          <h3 className="font-semibold text-xs text-slate-100">Parámetros de Disparo de Alerta</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1">
              Umbral de Vacío (empty_threshold):
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="0.50"
                max="0.95"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-full accent-blue-500 bg-slate-800 rounded-lg h-1.5 cursor-pointer"
              />
              <span className="text-xs font-mono font-bold text-slate-200 min-w-[45px]">
                {(threshold * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1">
              Segundos Consecutivos (consecutive_seconds):
            </label>
            <input
              type="number"
              min="1"
              max="60"
              value={consecutive}
              onChange={(e) => setConsecutive(parseFloat(e.target.value) || 1)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200"
            />
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1">
              Cooldown entre Alertas (cooldown_seconds):
            </label>
            <input
              type="number"
              min="5"
              max="300"
              value={cooldown}
              onChange={(e) => setCooldown(parseFloat(e.target.value) || 5)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200"
            />
          </div>
        </div>

        <button
          onClick={handleSaveConfig}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-blue-600/20 transition-all"
        >
          Guardar Configuración
        </button>
      </div>

      {/* Historial de Alertas */}
      <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="text-rose-400" />
            <h3 className="font-semibold text-xs text-slate-100">Registro Histórico de Alertas</h3>
          </div>
          <button
            onClick={loadHistory}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            Actualizar Registro
          </button>
        </div>

        {history.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            No se han registrado eventos de alerta de desabastecimiento hasta el momento.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 text-slate-400 uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Fecha y Hora</th>
                  <th className="py-2.5 px-3">Faltantes %</th>
                  <th className="py-2.5 px-3">Productos</th>
                  <th className="py-2.5 px-3">Vacíos</th>
                  <th className="py-2.5 px-3">Total Espacios</th>
                  <th className="py-2.5 px-3">Snapshot</th>
                  <th className="py-2.5 px-3">Mensaje</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {history.map((ev) => (
                  <tr key={ev.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2.5 px-3 text-slate-300">{ev.timestamp}</td>
                    <td className="py-2.5 px-3 font-bold text-rose-400">
                      {(ev.empty_rate * 100).toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-3 text-emerald-400">{ev.products}</td>
                    <td className="py-2.5 px-3 text-rose-400">{ev.missing}</td>
                    <td className="py-2.5 px-3 text-slate-300">{ev.products + ev.missing}</td>
                    <td className="py-2.5 px-3">
                      {ev.snapshot_url ? (
                        <button
                          onClick={() => setSelectedSnapshot(ev)}
                          className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 underline font-sans"
                        >
                          <ImageIcon size={14} />
                          Ver
                        </button>
                      ) : (
                        <span className="text-slate-600 font-sans">N/A</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 font-sans text-slate-400 max-w-xs truncate">
                      {ev.message}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal de Snapshot */}
      {selectedSnapshot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative max-w-3xl w-full bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950/60">
              <div>
                <h4 className="font-bold text-sm text-slate-100">
                  Snapshot de Alerta ({selectedSnapshot.id})
                </h4>
                <p className="text-xs text-slate-400">{selectedSnapshot.timestamp}</p>
              </div>
              <button
                onClick={() => setSelectedSnapshot(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-4 bg-black flex items-center justify-center max-h-[70vh] overflow-hidden">
              <img
                src={selectedSnapshot.snapshot_url}
                alt="Alert Snapshot"
                className="max-h-[65vh] object-contain rounded-lg"
              />
            </div>

            <div className="p-4 bg-slate-950/60 flex items-center justify-between text-xs text-slate-300">
              <span>{selectedSnapshot.message}</span>
              <span className="font-mono text-rose-400 font-bold">
                Tasa Vacíos: {(selectedSnapshot.empty_rate * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
