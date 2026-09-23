import React, { useState, useEffect } from 'react';
import { 
  Database, 
  Check, 
  X, 
  RefreshCw, 
  Camera, 
  Tag, 
  Eye, 
  Layers, 
  AlertCircle 
} from 'lucide-react';
import { DatasetItem, BBoxAnnotation } from '../types';
import { api } from '../services/api';

export const DatasetReviewPage: React.FC = () => {
  const [stage, setStage] = useState<string>('pending_review');
  const [samples, setSamples] = useState<DatasetItem[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [selectedSample, setSelectedSample] = useState<DatasetItem | null>(null);
  const [editedAnnotations, setEditedAnnotations] = useState<BBoxAnnotation[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, samplesData] = await Promise.all([
        api.getDatasetStats(),
        api.listDatasetSamples(stage),
      ]);
      setStats(statsData);
      setSamples(samplesData);
      if (samplesData.length > 0 && !selectedSample) {
        selectSample(samplesData[0]);
      } else if (samplesData.length === 0) {
        setSelectedSample(null);
      }
    } catch (e) {
      console.error('Error cargando muestras de dataset:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [stage]);

  const selectSample = (sample: DatasetItem) => {
    setSelectedSample(sample);
    setEditedAnnotations(JSON.parse(JSON.stringify(sample.detections || [])));
  };

  const handleToggleClass = (index: number) => {
    const updated = [...editedAnnotations];
    const currentCls = updated[index].class_name.toLowerCase();
    if (currentCls === 'product') {
      updated[index].class_name = 'missing';
      updated[index].class_id = 0;
    } else {
      updated[index].class_name = 'product';
      updated[index].class_id = 1;
    }
    setEditedAnnotations(updated);
  };

  const handleApprove = async () => {
    if (!selectedSample) return;
    try {
      await api.reviewSample(stage, selectedSample.id, 'approve', editedAnnotations);
      setActionMsg('Muestra aprobada y exportada para entrenamiento YOLO');
      setTimeout(() => setActionMsg(null), 3000);
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleReject = async () => {
    if (!selectedSample) return;
    try {
      await api.reviewSample(stage, selectedSample.id, 'reject');
      setActionMsg('Muestra descartada');
      setTimeout(() => setActionMsg(null), 3000);
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleManualCapture = async () => {
    try {
      await api.captureSample();
      setActionMsg('Nueva muestra capturada en Revisión');
      setTimeout(() => setActionMsg(null), 3000);
      setStage('pending_review');
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  const stagesList = [
    { key: 'pending_review', label: 'Pendientes de Revisión' },
    { key: 'approved', label: 'Aprobadas (Train Ready)' },
    { key: 'collected', label: 'Auto-Recolectadas' },
    { key: 'rejected', label: 'Rechazadas' },
    { key: 'validation', label: 'Validación' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Active Learning & Revisión Humana (HITL)</h2>
          <p className="text-xs text-slate-400 mt-1">
            Garantía de calidad: Las predicciones del modelo se verifican y corrigen manualmente antes de incorporarse al entrenamiento
          </p>
        </div>

        <div className="flex items-center gap-2">
          {actionMsg && (
            <span className="text-xs text-emerald-400 font-medium bg-emerald-950 px-3 py-1.5 rounded-lg border border-emerald-800">
              {actionMsg}
            </span>
          )}
          <button
            onClick={handleManualCapture}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-blue-600/20 transition-all"
          >
            <Camera size={14} />
            Capturar Frame Actual
          </button>
        </div>
      </div>

      {/* Selector de Etapas del Pipeline */}
      <div className="flex overflow-x-auto gap-2 p-1.5 bg-slate-900/60 rounded-xl border border-slate-800">
        {stagesList.map((st) => {
          const count = stats[st.key] || 0;
          const isActive = stage === st.key;
          return (
            <button
              key={st.key}
              onClick={() => setStage(st.key)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                isActive
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <span>{st.label}</span>
              <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-mono ${
                isActive ? 'bg-white/20 text-white' : 'bg-slate-800 text-slate-300'
              }`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Grid: Lista de Muestras + Editor de Anotaciones */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Galería de Muestras */}
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Muestras ({samples.length})</span>
            <button onClick={loadData} className="hover:text-slate-200 flex items-center gap-1">
              <RefreshCw size={12} /> Refrescar
            </button>
          </div>

          {samples.length === 0 ? (
            <div className="p-8 text-center rounded-2xl border border-slate-800 bg-slate-900/40 text-slate-500 text-xs">
              No hay imágenes en la etapa "{stage}".
            </div>
          ) : (
            <div className="space-y-2 max-h-[70vh] overflow-y-auto pr-1">
              {samples.map((s) => {
                const isSel = selectedSample?.id === s.id;
                return (
                  <div
                    key={s.id}
                    onClick={() => selectSample(s)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center gap-3 ${
                      isSel
                        ? 'bg-blue-600/10 border-blue-500/50 shadow-md shadow-blue-500/10'
                        : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <img
                      src={s.image_url}
                      alt={s.id}
                      className="w-16 h-12 object-cover rounded-lg bg-slate-950 border border-slate-800 flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-slate-200 truncate">{s.id}</span>
                        <span className="text-[10px] text-slate-500">{s.timestamp.split(' ')[1]}</span>
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400">
                        <span>{s.detections?.length || 0} etiquetas</span>
                        <span>•</span>
                        <span className="text-rose-400">{(s.empty_rate * 100).toFixed(0)}% vacíos</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Panel de Inspección y Corrección */}
        <div className="lg:col-span-2 space-y-4">
          {selectedSample ? (
            <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div>
                  <h3 className="font-semibold text-sm text-slate-100">
                    Muestra {selectedSample.id}
                  </h3>
                  <p className="text-xs text-slate-400">{selectedSample.timestamp} • Modelo: {selectedSample.model_version}</p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleReject}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-950 text-rose-300 border border-rose-800/60 hover:bg-rose-900 transition-all"
                  >
                    <X size={14} />
                    Descartar
                  </button>
                  <button
                    onClick={handleApprove}
                    className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/30 transition-all"
                  >
                    <Check size={14} />
                    Aprobar para Entrenamiento
                  </button>
                </div>
              </div>

              {/* Imagen con Anotaciones */}
              <div className="relative aspect-video w-full rounded-xl overflow-hidden bg-black flex items-center justify-center border border-slate-800">
                <img
                  src={selectedSample.image_url}
                  alt={selectedSample.id}
                  className="w-full h-full object-contain"
                />
              </div>

              {/* Lista de Etiquetas Editables */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">
                    Detecciones / Etiquetas ({editedAnnotations.length})
                  </span>
                  <span className="text-slate-500 text-[11px]">
                    Clic en la clase para alternar entre `product` y `missing`
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                  {editedAnnotations.map((ann, idx) => {
                    const isProduct = ann.class_name.toLowerCase() === 'product';
                    return (
                      <div
                        key={idx}
                        className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-slate-500 font-mono">#{idx + 1}</span>
                          <button
                            onClick={() => handleToggleClass(idx)}
                            className={`px-2 py-0.5 rounded font-mono font-bold text-[11px] transition-all ${
                              isProduct
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-500/30'
                                : 'bg-rose-500/20 text-rose-400 border border-rose-500/40 hover:bg-rose-500/30'
                            }`}
                          >
                            {ann.class_name.toUpperCase()} (Clic p/ cambiar)
                          </button>
                        </div>
                        <span className="text-[11px] text-slate-400 font-mono">
                          {Math.round(ann.confidence * 100)}% conf
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center rounded-2xl border border-slate-800 bg-slate-900/40 text-slate-500 text-xs">
              Seleccione una muestra para inspeccionar y corregir anotaciones.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
