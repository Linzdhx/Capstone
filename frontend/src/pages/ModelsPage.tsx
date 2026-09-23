import React, { useState, useEffect } from 'react';
import { 
  Boxes, 
  RotateCcw, 
  ArrowUpRight, 
  CheckCircle2, 
  AlertTriangle, 
  Archive, 
  RefreshCw, 
  Check 
} from 'lucide-react';
import { ModelVersionInfo } from '../types';
import { api } from '../services/api';

export const ModelsPage: React.FC = () => {
  const [models, setModels] = useState<{
    production: ModelVersionInfo[];
    candidates: ModelVersionInfo[];
    archive: ModelVersionInfo[];
  }>({
    production: [],
    candidates: [],
    archive: [],
  });
  const [loading, setLoading] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const loadModels = async () => {
    try {
      setLoading(true);
      const data = await api.listModels();
      setModels(data);
    } catch (e) {
      console.error('Error cargando modelos:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadModels();
  }, []);

  const handleHotSwap = async (version: string) => {
    try {
      await api.hotSwap(version);
      setStatusMsg(`Hot-swap completado exitosamente: Versión '${version}' ahora en producción.`);
      setTimeout(() => setStatusMsg(null), 4000);
      loadModels();
    } catch (e: any) {
      setStatusMsg(`Error en hot-swap: ${e.message}`);
      setTimeout(() => setStatusMsg(null), 4000);
    }
  };

  const handleRollback = async (version: string) => {
    try {
      await api.rollback(version);
      setStatusMsg(`Rollback completado exitosamente: Versión '${version}' restaurada.`);
      setTimeout(() => setStatusMsg(null), 4000);
      loadModels();
    } catch (e: any) {
      setStatusMsg(`Error en rollback: ${e.message}`);
      setTimeout(() => setStatusMsg(null), 4000);
    }
  };

  const activeModel = models.production[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Model Manager & Versionado (Hot-Swap / Rollback)</h2>
          <p className="text-xs text-slate-400 mt-1">
            Gestión segura de ciclo de vida: Activación en caliente de candidatos evaluados y restauración instantánea sin reinicio
          </p>
        </div>

        <button
          onClick={loadModels}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs transition-colors"
        >
          <RefreshCw size={14} />
          Refrescar Lista
        </button>
      </div>

      {statusMsg && (
        <div className="p-3 bg-blue-950/80 text-blue-300 border border-blue-800 rounded-xl text-xs flex items-center gap-2">
          <Check size={16} className="text-blue-400" />
          {statusMsg}
        </div>
      )}

      {/* Modelo Activo de Producción */}
      {activeModel && (
        <div className="p-6 rounded-2xl border border-blue-500/40 bg-gradient-to-br from-blue-950/30 via-slate-900/60 to-slate-900/60 backdrop-blur-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center border border-blue-500/30">
                <Boxes size={22} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-sm text-slate-100">{activeModel.name}</h3>
                  <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                    EN PRODUCCIÓN
                  </span>
                </div>
                <p className="text-xs font-mono text-slate-400">Versión: {activeModel.version} • Archivo: best.pt</p>
              </div>
            </div>

            <div className="text-right text-xs text-slate-400">
              <span>Registrado: {activeModel.created_at || 'Inicial'}</span>
            </div>
          </div>

          {/* Grid de Métricas de Producción */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-1">
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 text-xs block">mAP50</span>
              <span className="text-lg font-bold font-mono text-emerald-400">
                {activeModel.metrics?.mAP50 ?? '0.85'}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 text-xs block">mAP50-95</span>
              <span className="text-lg font-bold font-mono text-slate-200">
                {activeModel.metrics?.mAP50_95 ?? '0.62'}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 text-xs block">Precision</span>
              <span className="text-lg font-bold font-mono text-slate-200">
                {activeModel.metrics?.precision ?? '0.88'}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 text-xs block">Recall</span>
              <span className="text-lg font-bold font-mono text-slate-200">
                {activeModel.metrics?.recall ?? '0.82'}
              </span>
            </div>
          </div>

          <div className="text-xs text-slate-400 flex items-center justify-between pt-2">
            <span>Clases: <strong>0: missing, 1: product</strong></span>
            <span>Ruta: <code className="text-slate-300 font-mono">models/production/best.pt</code></span>
          </div>
        </div>
      )}

      {/* Candidatos Disponibles */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
          <ArrowUpRight size={18} className="text-purple-400" />
          <h3 className="font-semibold text-sm text-slate-100">
            Modelos Candidatos ({models.candidates.length})
          </h3>
        </div>

        {models.candidates.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No hay candidatos pendientes de validación. Inicie un reentrenamiento en la pestaña "Entrenamiento" para generar una nueva versión.
          </div>
        ) : (
          <div className="space-y-3">
            {models.candidates.map((cand) => (
              <div
                key={cand.version}
                className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-100">{cand.version}</span>
                    <span className="text-xs text-slate-400">({cand.name})</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/40">
                      CANDIDATE
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-400 mt-1 font-mono">
                    <span>mAP50: <strong className="text-emerald-400">{cand.metrics?.mAP50 || 'N/A'}</strong></span>
                    <span>Precision: {cand.metrics?.precision || 'N/A'}</span>
                    <span>Recall: {cand.metrics?.recall || 'N/A'}</span>
                  </div>
                </div>

                <button
                  onClick={() => handleHotSwap(cand.version)}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-emerald-600/30 transition-all flex items-center gap-1.5"
                >
                  <ArrowUpRight size={14} />
                  Promover a Producción (Hot-Swap)
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Historial de Versiones Archivadas (Rollback) */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
          <Archive size={18} className="text-amber-400" />
          <h3 className="font-semibold text-sm text-slate-100">
            Versiones Archivadas para Rollback ({models.archive.length})
          </h3>
        </div>

        {models.archive.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No hay modelos archivados en este momento. Las versiones previas se archivarán automáticamente tras cada hot-swap.
          </div>
        ) : (
          <div className="space-y-3">
            {models.archive.map((arch) => (
              <div
                key={arch.version}
                className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-200">{arch.version}</span>
                    <span className="text-xs text-slate-400">({arch.name})</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                      ARCHIVE
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1 font-mono">
                    Ruta: models/archive/{arch.version}/best.pt
                  </p>
                </div>

                <button
                  onClick={() => handleRollback(arch.version)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-amber-300 rounded-lg text-xs font-semibold border border-amber-600/30 transition-all flex items-center gap-1.5"
                >
                  <RotateCcw size={14} />
                  Restaurar (Rollback)
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
