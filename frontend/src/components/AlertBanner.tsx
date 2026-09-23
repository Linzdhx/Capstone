import React from 'react';
import { AlertTriangle, Clock, ShieldAlert } from 'lucide-react';
import { AlertTelemetry } from '../types';

interface AlertBannerProps {
  alert: AlertTelemetry;
  onViewAlerts?: () => void;
}

export const AlertBanner: React.FC<AlertBannerProps> = ({ alert, onViewAlerts }) => {
  if (!alert.is_active && alert.cooldown_remaining_seconds === 0) {
    return null;
  }

  const isCritical = alert.is_active;

  return (
    <div
      className={`mb-6 p-4 rounded-xl border backdrop-blur-md transition-all animate-in fade-in duration-300 ${
        isCritical
          ? 'bg-rose-950/40 border-rose-600/50 shadow-lg shadow-rose-950/30'
          : 'bg-amber-950/30 border-amber-600/40'
      }`}
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className={`p-2.5 rounded-xl ${
              isCritical
                ? 'bg-rose-600 text-white animate-bounce'
                : 'bg-amber-600 text-white'
            }`}
          >
            {isCritical ? <ShieldAlert size={22} /> : <AlertTriangle size={22} />}
          </div>
          <div>
            <h4 className="font-bold text-sm text-slate-100 flex items-center gap-2">
              {isCritical ? '¡ALERTA CRÍTICA DE DESABASTECIMIENTO!' : 'CONDICIÓN EN COOLDOWN'}
              <span className="text-xs px-2 py-0.5 rounded font-mono font-bold bg-white/10">
                {(alert.empty_rate * 100).toFixed(1)}% Vacíos
              </span>
            </h4>
            <p className="text-xs text-slate-300 mt-0.5">
              {isCritical
                ? `La proporción de espacios vacíos supera el umbral configurado (${(alert.threshold * 100).toFixed(0)}%) por más de 3 segundos consecutivos.`
                : `Alerta disparada previamente. Cooldown de seguridad activo (${alert.cooldown_remaining_seconds}s restantes).`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center">
          {alert.cooldown_remaining_seconds > 0 && (
            <div className="flex items-center gap-1.5 text-xs font-mono text-amber-400 bg-amber-950/60 px-2.5 py-1.5 rounded-lg border border-amber-800/50">
              <Clock size={13} />
              <span>Cooldown: {alert.cooldown_remaining_seconds}s</span>
            </div>
          )}
          {onViewAlerts && (
            <button
              onClick={onViewAlerts}
              className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-lg shadow-md transition-all"
            >
              Ver Registro
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
