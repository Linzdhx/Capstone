import React, { useState } from 'react';
import {
  LayoutDashboard,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Image as ImageIcon,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Bell,
  X,
} from 'lucide-react';
import { IncidentSummary, SeverityLevel } from '../types';
import { SeverityBadge } from './SeverityBadge';

interface IncidentHistoryProps {
  incidents: IncidentSummary[];
  isLoading: boolean;
  onRefresh: () => void;
  onResolve?: (incidentId: string) => void;
}

const STATUS_CONFIG = {
  ACTIVE: {
    label: 'Activa',
    icon: AlertCircle,
    color: 'text-rose-400',
    bg: 'bg-rose-900/20 border-rose-500/30',
  },
  RESOLVED: {
    label: 'Resuelta',
    icon: CheckCircle,
    color: 'text-emerald-400',
    bg: 'bg-emerald-900/20 border-emerald-500/30',
  },
} as const;

const SEVERITY_TEXT: Record<SeverityLevel, string> = {
  CRITICAL: 'text-red-400',
  MODERATE: 'text-amber-400',
  LOW: 'text-emerald-400',
};

interface SnapshotModalProps {
  imageUrl: string;
  incidentId: string;
  onClose: () => void;
}

const SnapshotModal: React.FC<SnapshotModalProps> = ({ imageUrl, incidentId, onClose }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
    <div className="relative max-w-3xl w-full bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl">
      <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950/60">
        <div>
          <h4 className="font-bold text-sm text-slate-100">Imagen de Incidencia</h4>
          <p className="text-xs text-slate-400 font-mono">{incidentId}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <X size={16} />
        </button>
      </div>
      <div className="p-4 bg-black flex items-center justify-center max-h-[70vh] overflow-hidden">
        <img
          src={imageUrl}
          alt="Incident snapshot"
          className="max-h-[65vh] object-contain rounded-lg"
        />
      </div>
    </div>
  </div>
);

export const IncidentHistory: React.FC<IncidentHistoryProps> = ({
  incidents,
  isLoading,
  onRefresh,
}) => {
  const [selectedImage, setSelectedImage] = useState<{ url: string; id: string } | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const toggleExpand = (id: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 bg-slate-950/40">
        <div className="flex items-center gap-2">
          <LayoutDashboard size={16} className="text-indigo-400" />
          <h3 className="font-bold text-sm text-slate-100">Histórico de Incidencias</h3>
          <span className="ml-1 text-[10px] font-mono bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full border border-slate-700">
            {incidents.length}
          </span>
        </div>
        <button
          id="btn-refresh-incidents"
          onClick={onRefresh}
          disabled={isLoading}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-800 border border-transparent hover:border-slate-700"
        >
          <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
          Actualizar
        </button>
      </div>

      {/* Tabla */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12 text-slate-500 text-xs">
          <RefreshCw size={16} className="animate-spin mr-2" />
          Cargando historial...
        </div>
      ) : incidents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-slate-500">
          <CheckCircle size={32} className="mb-3 opacity-30" />
          <p className="text-sm font-medium">Sin incidencias registradas</p>
          <p className="text-xs mt-1 text-slate-600">Las incidencias aparecerán cuando se detecten faltantes.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4 font-semibold">ID</th>
                <th className="py-3 px-4 font-semibold">Pasillo</th>
                <th className="py-3 px-4 font-semibold">Fecha</th>
                <th className="py-3 px-4 font-semibold">% Faltante</th>
                <th className="py-3 px-4 font-semibold">Faltantes</th>
                <th className="py-3 px-4 font-semibold">Severidad</th>
                <th className="py-3 px-4 font-semibold">Estado</th>
                <th className="py-3 px-4 font-semibold">Alerta</th>
                <th className="py-3 px-4 font-semibold">Imagen</th>
                <th className="py-3 px-4 font-semibold"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {incidents.map((inc) => {
                const statusCfg = STATUS_CONFIG[inc.status];
                const StatusIcon = statusCfg.icon;
                const isExpanded = expandedRows.has(inc.id);

                return (
                  <React.Fragment key={inc.id}>
                    <tr
                      className="hover:bg-slate-800/30 transition-colors cursor-pointer"
                      onClick={() => toggleExpand(inc.id)}
                    >
                      <td className="py-3 px-4 font-mono text-slate-500 text-[10px]">{inc.id}</td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-200">{inc.display_name}</div>
                        <div className="text-[10px] font-mono text-slate-600">{inc.location_id}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                        {new Date(inc.created_at).toLocaleString('es-CL', {
                          day: '2-digit', month: '2-digit', year: 'numeric',
                          hour: '2-digit', minute: '2-digit'
                        })}
                      </td>
                      <td className={`py-3 px-4 font-bold font-mono ${SEVERITY_TEXT[inc.severity]}`}>
                        {inc.missing_percentage.toFixed(1)}%
                      </td>
                      <td className="py-3 px-4 text-slate-300 font-mono">
                        {inc.missing_count}
                        <span className="text-slate-600">/{inc.expected_count}</span>
                      </td>
                      <td className="py-3 px-4">
                        <SeverityBadge severity={inc.severity} />
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-medium ${statusCfg.bg} ${statusCfg.color}`}>
                          <StatusIcon size={10} />
                          {statusCfg.label}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {inc.alert_sent ? (
                          <span className="inline-flex items-center gap-1 text-emerald-400 text-[10px]">
                            <Bell size={10} /> Enviada
                          </span>
                        ) : (
                          <span className="text-slate-600 text-[10px]">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {inc.image_url ? (
                          <button
                            id={`img-btn-${inc.id}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedImage({ url: inc.image_url!, id: inc.id });
                            }}
                            className="flex items-center gap-1 text-blue-400 hover:text-blue-300 underline transition-colors"
                          >
                            <ImageIcon size={12} /> Ver
                          </button>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </td>
                    </tr>

                    {/* Fila expandida con detalle */}
                    {isExpanded && (
                      <tr className="bg-slate-950/50">
                        <td colSpan={10} className="px-6 py-4">
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                            <div>
                              <span className="text-slate-500 block">Espacios totales</span>
                              <span className="font-mono text-slate-200 font-bold">{inc.expected_count}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 block">Faltantes</span>
                              <span className="font-mono text-rose-400 font-bold">{inc.missing_count}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 block">Restantes</span>
                              <span className="font-mono text-emerald-400 font-bold">{inc.remaining_count}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 block">% Restante</span>
                              <span className="font-mono text-slate-200 font-bold">
                                {(100 - inc.missing_percentage).toFixed(1)}%
                              </span>
                            </div>
                            {inc.resolved_at && (
                              <div className="col-span-2">
                                <span className="text-slate-500 block">Resuelta el</span>
                                <span className="font-mono text-emerald-400">
                                  {new Date(inc.resolved_at).toLocaleString('es-CL')}
                                </span>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal de imagen */}
      {selectedImage && (
        <SnapshotModal
          imageUrl={selectedImage.url}
          incidentId={selectedImage.id}
          onClose={() => setSelectedImage(null)}
        />
      )}
    </div>
  );
};
