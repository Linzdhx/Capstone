import React, { useState } from 'react';
import {
  MapPin,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Bell,
  Package,
  PackageX,
  TrendingDown,
  Clock,
  CheckSquare,
  Image as ImageIcon,
  Maximize2,
  X,
  FileCheck,
  ShieldOff,
} from 'lucide-react';
import { AisleStatus, SeverityLevel } from '../types';
import { SeverityBadge } from './SeverityBadge';
import { api } from '../services/api';

interface AisleCardProps {
  aisle: AisleStatus;
  onAlertSent?: (identifier: string) => void;
  onResolved?: (filename: string) => void;
}

type AlertButtonState = 'idle' | 'sending' | 'sent' | 'error';

const SEVERITY_CARD_BORDER: Record<SeverityLevel, string> = {
  CRITICAL: 'border-red-500/50 shadow-red-500/10',
  MODERATE: 'border-amber-500/50 shadow-amber-500/10',
  LOW: 'border-emerald-500/40 shadow-emerald-500/10',
};

const SEVERITY_HEADER_BG: Record<SeverityLevel, string> = {
  CRITICAL: 'bg-gradient-to-r from-red-950/60 to-red-900/30',
  MODERATE: 'bg-gradient-to-r from-amber-950/60 to-amber-900/30',
  LOW: 'bg-gradient-to-r from-emerald-950/60 to-emerald-900/30',
};

const SEVERITY_PROGRESS_COLOR: Record<SeverityLevel, string> = {
  CRITICAL: 'bg-red-500',
  MODERATE: 'bg-amber-500',
  LOW: 'bg-emerald-500',
};

/** Badge visual del estado de stock clasificado */
const StockStatusBadge: React.FC<{ stockStatus: AisleStatus['stock_status'] }> = ({ stockStatus }) => {
  if (stockStatus === 'SIN_STOCK') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-900/60 text-red-300 border border-red-500/50">
        <ShieldOff size={10} />
        Sin Stock
      </span>
    );
  }
  if (stockStatus === 'FALTA_PRODUCTO') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-orange-900/60 text-orange-300 border border-orange-500/50">
        <PackageX size={10} />
        Falta Producto
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-900/60 text-emerald-300 border border-emerald-500/50">
      <Package size={10} />
      Stock Correcto
    </span>
  );
};

export const AisleCard: React.FC<AisleCardProps> = ({ aisle, onAlertSent, onResolved }) => {
  const [alertState, setAlertState] = useState<AlertButtonState>(aisle.alert_sent ? 'sent' : 'idle');
  const [alertError, setAlertError] = useState<string | null>(null);
  const [isResolving, setIsResolving] = useState(false);
  const [showImageModal, setShowImageModal] = useState(false);
  const [showDebug, setShowDebug] = useState(false);

  const { stock, severity_info: sev, filename, image_url } = aisle;
  const missingPct = Math.min(100, Math.max(0, stock.missing_percentage));
  const remainingPct = Math.min(100, Math.max(0, stock.remaining_percentage));
  const severity = sev.severity as SeverityLevel;

  const handleSendAlert = async () => {
    if (!filename || alertState === 'sending' || alertState === 'sent') return;
    setAlertState('sending');
    setAlertError(null);
    try {
      await api.sendHistoricaAlert(filename, 'webhook');
      setAlertState('sent');
      onAlertSent?.(filename);
    } catch (e: any) {
      setAlertState('error');
      setAlertError(e.message || 'Error al enviar');
      setTimeout(() => setAlertState('idle'), 4000);
    }
  };

  const handleResolve = async () => {
    if (!filename || isResolving) return;
    const confirm = window.confirm(`¿Confirmas que la falla del ${aisle.display_name} fue resuelta? Se eliminará la imagen de /historica y los pasillos siguientes se reordenarán automáticamente.`);
    if (!confirm) return;

    setIsResolving(true);
    try {
      await api.resolveHistoricaFile(filename);
      onResolved?.(filename);
    } catch (e: any) {
      alert(`Error al resolver: ${e.message}`);
    } finally {
      setIsResolving(false);
    }
  };

  return (
    <>
      <div
        className={`relative flex flex-col rounded-2xl border bg-slate-900/80 backdrop-blur-sm shadow-xl transition-all duration-300 hover:scale-[1.01] hover:shadow-2xl overflow-hidden ${SEVERITY_CARD_BORDER[severity]}`}
      >
        {/* Pulse animado para CRÍTICO */}
        {severity === 'CRITICAL' && (
          <div className="absolute inset-0 rounded-2xl ring-1 ring-red-500/30 animate-pulse pointer-events-none" />
        )}

        {/* Header de la tarjeta */}
        <div className={`px-5 py-3.5 ${SEVERITY_HEADER_BG[severity]} border-b border-white/5`}>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="p-2 rounded-lg bg-slate-800/80 text-cyan-400">
                <Bell size={16} className="shrink-0" />
              </div>
              <div className="min-w-0">
                {/* Título Principal: Alerta N */}
                <h3 className="font-extrabold text-base text-white tracking-tight flex items-center gap-2 truncate">
                  {aisle.display_name.startsWith('Alerta') ? aisle.display_name : `Alerta ${aisle.display_order}`}
                </h3>
                {/* Sub-etiqueta (Ubicación): Pasillo N */}
                <div className="flex items-center gap-1.5 text-xs font-semibold text-cyan-300">
                  <MapPin size={12} className="shrink-0 text-cyan-400" />
                  <span>{aisle.aisle_name || `Pasillo ${aisle.display_order}`}</span>
                  {filename && (
                    <span className="text-[10px] font-mono text-slate-400 font-normal truncate max-w-[140px]">
                      &bull; {filename}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex flex-col items-end gap-1.5 shrink-0">
              <SeverityBadge severity={severity} />
              <StockStatusBadge stockStatus={aisle.stock_status} />
            </div>
          </div>
        </div>

        {/* Banner de Sin Stock (alerta visual prominente cuando no hay detecciones) */}
        {aisle.stock_status === 'SIN_STOCK' && (
          <div className="mx-5 mt-4 flex items-center gap-3 px-4 py-3 bg-red-950/70 border border-red-500/60 rounded-xl">
            <ShieldOff size={20} className="text-red-400 shrink-0" />
            <div>
              <p className="text-xs font-extrabold text-red-300 uppercase tracking-wide">Sin Stock — Góndola Vacía</p>
              <p className="text-[11px] text-red-400/80 mt-0.5">
                El modelo no detectó productos ni espacios. La góndola está completamente vacía.
              </p>
            </div>
          </div>
        )}

        {/* Thumbnail de la imagen en /historica */}
        {image_url && (
          <div className="relative group mx-5 mt-4 rounded-xl overflow-hidden border border-slate-700/80 bg-slate-950 max-h-36">
            <img
              src={image_url}
              alt={`Falla ${aisle.display_name}`}
              className="w-full h-36 object-cover object-center group-hover:scale-105 transition-transform duration-300"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-between p-2.5">
              <span className="text-[10px] text-white font-medium flex items-center gap-1">
                <ImageIcon size={12} />
                Captura en /historica
              </span>
              <button
                onClick={() => setShowImageModal(true)}
                className="p-1.5 rounded-lg bg-slate-900/90 text-cyan-400 hover:text-white border border-slate-700 hover:border-cyan-500 transition-colors"
                title="Ampliar captura"
              >
                <Maximize2 size={13} />
              </button>
            </div>
          </div>
        )}

        {/* Cuerpo: Métricas */}
        <div className="px-5 py-4 flex-1 space-y-4">
          {/* Métricas numéricas */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-slate-800/60 p-3 border border-slate-700/50">
              <div className="flex items-center gap-1.5 mb-1">
                <PackageX size={13} className="text-rose-400" />
                <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wide">Faltantes</span>
              </div>
              <div className="text-xl font-extrabold text-rose-400 font-mono">
                {stock.missing_count}
                <span className="text-xs text-slate-500 ml-1 font-normal">/ {stock.expected_count}</span>
              </div>
              <div className="text-[11px] text-rose-300/80 font-bold mt-0.5">
                {missingPct.toFixed(1)}% faltante
              </div>
            </div>

            <div className="rounded-xl bg-slate-800/60 p-3 border border-slate-700/50">
              <div className="flex items-center gap-1.5 mb-1">
                <Package size={13} className="text-emerald-400" />
                <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wide">Restantes</span>
              </div>
              <div className="text-xl font-extrabold text-emerald-400 font-mono">
                {stock.remaining_count}
                <span className="text-xs text-slate-500 ml-1 font-normal">/ {stock.expected_count}</span>
              </div>
              <div className="text-[11px] text-emerald-300/80 font-bold mt-0.5">
                {remainingPct.toFixed(1)}% remanente
              </div>
            </div>
          </div>

          {/* Barra de stock faltante */}
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold flex items-center gap-1">
                <TrendingDown size={11} />
                Nivel de faltante
              </span>
              <span className="text-xs font-bold font-mono text-rose-400">{missingPct.toFixed(1)}%</span>
            </div>
            <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ${SEVERITY_PROGRESS_COLOR[severity]}`}
                style={{ width: `${missingPct}%` }}
              />
            </div>
          </div>

          {/* Barra de stock restante */}
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold flex items-center gap-1">
                <Package size={11} />
                Stock restante
              </span>
              <span className="text-xs font-bold font-mono text-emerald-400">{remainingPct.toFixed(1)}%</span>
            </div>
            <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-emerald-500 transition-all duration-700"
                style={{ width: `${remainingPct}%` }}
              />
            </div>
          </div>

          {/* Tiempo de detección */}
          {aisle.last_detected_at && (
            <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
              <Clock size={11} />
              <span>Registrado: {new Date(aisle.last_detected_at).toLocaleTimeString('es-CL')}</span>
            </div>
          )}
        </div>

        {/* Footer: Severidad + Acciones */}
        <div className="px-5 pb-5 space-y-3 border-t border-slate-800/80 pt-4">
          <div className="rounded-xl bg-slate-800/50 border border-slate-700/40 px-3.5 py-2.5 space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[10px] text-slate-500 uppercase font-semibold">Estado</span>
              <span className="font-bold text-slate-200">{sev.status}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-[10px] text-slate-500 uppercase font-semibold">Acción</span>
              <span className="font-bold text-slate-200">{sev.action}</span>
            </div>
          </div>

          <p className="text-[11px] text-slate-400 leading-relaxed italic">{sev.message}</p>

          {/* Información de depuración diagnóstica (Requisito 7) */}
          {aisle.debug_info && (
            <div className="pt-1">
              <button
                type="button"
                onClick={() => setShowDebug(!showDebug)}
                className="w-full flex items-center justify-between text-[11px] text-cyan-400 hover:text-cyan-300 font-mono py-1.5 px-2.5 rounded-lg bg-slate-950/80 border border-slate-800 hover:border-slate-700 transition-colors"
              >
                <span className="flex items-center gap-1.5 font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                  Diagnóstico IA (Debug)
                </span>
                <span>{showDebug ? '▲ Ocultar' : '▼ Ver'}</span>
              </button>
              {showDebug && (
                <div className="mt-2 p-3 rounded-xl bg-black/80 border border-slate-800 text-[10px] font-mono space-y-1.5 text-slate-300 shadow-inner">
                  <div className="flex justify-between border-b border-slate-800/80 pb-1">
                    <span className="text-slate-500">Camera / Shelf:</span>
                    <span className="text-cyan-300 font-bold">{aisle.debug_info.camera_id} • {aisle.debug_info.shelf_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Raw detections:</span>
                    <span className="text-slate-200 font-bold">{aisle.debug_info.detections_count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Valid detections:</span>
                    <span className="text-slate-200 font-bold">
                      {aisle.debug_info.valid_detections_count} (Prod: {aisle.debug_info.valid_products_count}, Miss: {aisle.debug_info.valid_missing_count})
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Average confidence:</span>
                    <span className="text-slate-200 font-bold">{aisle.debug_info.average_confidence}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Estimated occupancy:</span>
                    <span className="text-slate-200 font-bold">{aisle.debug_info.estimated_occupancy}</span>
                  </div>
                  <div className="flex justify-between pt-1 border-t border-slate-800/80">
                    <span className="text-slate-500 font-bold">Final status:</span>
                    <span className={`font-extrabold uppercase ${aisle.debug_info.final_stock_status === 'SIN_STOCK' ? 'text-red-400' : 'text-orange-400'}`}>
                      {aisle.debug_info.final_stock_status}
                    </span>
                  </div>
                  {aisle.debug_info.confidence_scores && aisle.debug_info.confidence_scores.length > 0 && (
                    <div className="pt-1 text-[9px] text-slate-500 truncate" title={aisle.debug_info.confidence_scores.join(', ')}>
                      Confidences: [{aisle.debug_info.confidence_scores.join(', ')}]
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Botones de acción: Alerta + Resolver */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
            {/* Botón Alerta */}
            <button
              id={`alert-btn-${aisle.location_id}`}
              onClick={handleSendAlert}
              disabled={alertState === 'sending' || alertState === 'sent'}
              className={`flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl text-xs font-bold transition-all duration-200 border
                ${alertState === 'sent'
                  ? 'bg-emerald-600/20 text-emerald-300 border-emerald-600/40 cursor-default'
                  : alertState === 'error'
                    ? 'bg-rose-600/20 text-rose-300 border-rose-600/40'
                    : alertState === 'sending'
                      ? 'bg-slate-700/60 text-slate-400 border-slate-600/40 cursor-wait'
                      : 'bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 border-blue-600/40 hover:border-blue-500/60 cursor-pointer active:scale-95'
                }`}
            >
              {alertState === 'idle' && <><Bell size={13} /> Alerta</>}
              {alertState === 'sending' && <><Loader2 size={13} className="animate-spin" /> Enviando...</>}
              {alertState === 'sent' && <><CheckCircle2 size={13} /> Alerta Enviada</>}
              {alertState === 'error' && <><AlertTriangle size={13} /> Error</>}
            </button>

            {/* Botón Resolver Falla (Elimina de /historica y reordena pasillos) */}
            <button
              onClick={handleResolve}
              disabled={isResolving}
              className="flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl text-xs font-bold bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 hover:border-emerald-400 transition-all duration-200 cursor-pointer active:scale-95 disabled:opacity-50"
              title="Resolver falla y eliminar de /historica (reordena los pasillos siguientes)"
            >
              {isResolving ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  <span>Reordenando...</span>
                </>
              ) : (
                <>
                  <CheckSquare size={13} />
                  <span>Resolver Falla</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Modal para ampliar imagen */}
      {showImageModal && image_url && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4"
          onClick={() => setShowImageModal(false)}
        >
          <div
            className="relative bg-slate-900 border border-slate-700 rounded-2xl max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950/60">
              <div className="flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-cyan-400" />
                <h4 className="font-bold text-white text-sm">
                  Captura {aisle.display_name} — {filename}
                </h4>
              </div>
              <button
                onClick={() => setShowImageModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X size={18} />
              </button>
            </div>
            <div className="p-4 flex items-center justify-center overflow-auto max-h-[75vh]">
              <img
                src={image_url}
                alt={aisle.display_name}
                className="max-w-full max-h-full object-contain rounded-lg border border-slate-800 shadow-md"
              />
            </div>
            <div className="p-3 bg-slate-950/80 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
              <span>Faltantes: <strong className="text-rose-400">{stock.missing_count}</strong> ({missingPct.toFixed(1)}%)</span>
              <span>Ubicación física: <code className="text-cyan-300 font-mono">/historica/{filename}</code></span>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
