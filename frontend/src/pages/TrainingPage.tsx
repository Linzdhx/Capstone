import React, { useState, useEffect } from 'react';
import { 
  Cpu, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Database, 
  TrendingUp, 
  Award, 
  Sliders 
} from 'lucide-react';
import { TrainingStatus } from '../types';
import { api } from '../services/api';

export const TrainingPage: React.FC = () => {
  const [status, setStatus] = useState<TrainingStatus | null>(null);
  const [approvedCount, setApprovedCount] = useState<number>(0);
  const [epochs, setEpochs] = useState<number>(50);
  const [batchSize, setBatchSize] = useState<number>(16);
  const [imgsz, setImgsz] = useState<number>(640);
  const [lr0, setLr0] = useState<number>(0.01);
  const [isStarting, setIsStarting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadStatus = async () => {
    try {
      const [st, stats] = await Promise.all([
        api.getTrainingStatus(),
        api.getDatasetStats(),
      ]);
      setStatus(st);
      setApprovedCount(stats.approved || 0);
    } catch (e) {
      console.error('Error cargando estado de entrenamiento:', e);
    }
  };

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleStartTraining = async () => {
    try {
      setIsStarting(true);
      setErrorMsg(null);
      await api.startTraining(epochs, batchSize, imgsz, lr0);
      loadStatus();
    } catch (err: any) {
      setErrorMsg(err.message || 'Error al iniciar entrenamiento');
    } finally {
      setIsStarting(false);
    }
  };

  const isTrainingActive = status?.status === 'training' || status?.status === 'preparing' || status?.status === 'evaluating';

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Reentrenamiento Desacoplado & Fine-Tuning</h2>
          <p className="text-xs text-slate-400 mt-1">
            Worker asíncrono en segundo plano: El entrenamiento nunca bloquea la inferencia de la cámara ni la interfaz
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">
            Muestras Aprobadas: <strong className="text-emerald-400">{approvedCount}</strong> (mínimo 5)
          </span>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-rose-950/80 text-rose-300 border border-rose-800 rounded-xl text-xs flex items-center gap-2">
          <AlertCircle size={16} className="text-rose-400" />
          {errorMsg}
        </div>
      )}

      {/* Tarjeta de Estado del Worker en Vivo */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Cpu size={18} className="text-purple-400" />
            <h3 className="font-semibold text-sm text-slate-100">Estado del Training Worker</h3>
          </div>
          <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded-full uppercase border ${
            isTrainingActive
              ? 'bg-purple-500/20 text-purple-300 border-purple-500/40 animate-pulse'
              : status?.status === 'completed'
              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
              : status?.status === 'failed'
              ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
              : 'bg-slate-800 text-slate-400 border-slate-700'
          }`}>
            {status?.status || 'IDLE'}
          </span>
        </div>

        {/* Barra de Progreso */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs font-mono">
            <span className="text-slate-300">{status?.message || 'Worker en espera.'}</span>
            <span className="text-purple-400 font-bold">{Math.round(status?.progress_percent || 0)}%</span>
          </div>
          <div className="w-full bg-slate-950 rounded-full h-2.5 overflow-hidden border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-purple-600 to-indigo-500 transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, status?.progress_percent || 0))}%` }}
            />
          </div>
        </div>

        {/* Métricas del Candidato si se completó */}
        {status?.status === 'completed' && status.metrics && (
          <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-800/40 space-y-2">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold">
              <Award size={16} />
              <span>Candidato Generado y Evaluado: {status.candidate_version}</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono pt-2">
              <div>
                <span className="text-slate-400 block text-[11px]">mAP50</span>
                <span className="text-emerald-300 font-bold text-base">{status.metrics.mAP50 || 0}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">mAP50-95</span>
                <span className="text-slate-200 font-bold text-base">{status.metrics.mAP50_95 || 0}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Precision</span>
                <span className="text-slate-200 font-bold text-base">{status.metrics.precision || 0}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Recall</span>
                <span className="text-slate-200 font-bold text-base">{status.metrics.recall || 0}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Configuración de Hiperparámetros y Disparo de Entrenamiento */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
          <Sliders size={18} className="text-blue-400" />
          <h3 className="font-semibold text-sm text-slate-100">Hiperparámetros de Fine-Tuning</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          <div>
            <label className="text-slate-400 block mb-1">Épocas de Entrenamiento (epochs):</label>
            <input
              type="number"
              min="1"
              max="300"
              value={epochs}
              onChange={(e) => setEpochs(parseInt(e.target.value) || 10)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 font-mono"
            />
          </div>

          <div>
            <label className="text-slate-400 block mb-1">Batch Size:</label>
            <input
              type="number"
              min="1"
              max="64"
              value={batchSize}
              onChange={(e) => setBatchSize(parseInt(e.target.value) || 8)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 font-mono"
            />
          </div>

          <div>
            <label className="text-slate-400 block mb-1">Image Size (imgsz):</label>
            <input
              type="number"
              min="320"
              max="1280"
              step="32"
              value={imgsz}
              onChange={(e) => setImgsz(parseInt(e.target.value) || 640)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 font-mono"
            />
          </div>

          <div>
            <label className="text-slate-400 block mb-1">Learning Rate Inicial (lr0):</label>
            <input
              type="number"
              min="0.0001"
              max="0.1"
              step="0.001"
              value={lr0}
              onChange={(e) => setLr0(parseFloat(e.target.value) || 0.01)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 font-mono"
            />
          </div>
        </div>

        <div className="pt-2">
          <button
            onClick={handleStartTraining}
            disabled={isTrainingActive || isStarting}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-purple-600/30 transition-all disabled:opacity-50"
          >
            <Play size={16} />
            {isTrainingActive ? 'Entrenamiento en Curso...' : 'Iniciar Fine-Tuning en Segundo Plano'}
          </button>
        </div>
      </div>
    </div>
  );
};
