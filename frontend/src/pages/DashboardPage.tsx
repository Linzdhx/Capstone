import React from 'react';
import { 
  Package, 
  PackageX, 
  Layers, 
  Percent, 
  Activity, 
  Clock, 
  Zap, 
  Boxes 
} from 'lucide-react';
import { TelemetryMessage } from '../types';
import { MetricCard } from '../components/MetricCard';
import { VideoPlayer } from '../components/VideoPlayer';
import { SystemMonitor } from '../components/SystemMonitor';
import { AlertBanner } from '../components/AlertBanner';

interface DashboardPageProps {
  telemetry: TelemetryMessage | null;
  onNavigate: (tab: any) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ telemetry, onNavigate }) => {
  if (!telemetry) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-slate-400">
        <Activity className="animate-spin mb-3 text-blue-500" size={32} />
        <p className="text-sm font-medium">Conectando con el motor de telemetría e inferencia...</p>
      </div>
    );
  }

  const { inventory, model, camera, alert, system } = telemetry;
  const isHighEmpty = inventory.empty_rate >= 0.80 && inventory.total_spaces > 0;

  return (
    <div className="space-y-6">
      {/* Alerta Crítica Activa si existe */}
      <AlertBanner alert={alert} onViewAlerts={() => onNavigate('alerts')} />

      {/* Fila 1: KPIs Principales de Inventario */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Productos en Estante"
          value={inventory.products}
          subtitle="Detectados"
          icon={<Package size={18} />}
          variant="success"
        />
        <MetricCard
          title="Espacios Vacíos"
          value={inventory.missing}
          subtitle="Faltantes"
          icon={<PackageX size={18} />}
          variant={isHighEmpty ? 'danger' : 'warning'}
        />
        <MetricCard
          title="Espacios Totales"
          value={inventory.total_spaces}
          subtitle="Capacidad detectada"
          icon={<Layers size={18} />}
          variant="default"
        />
        <MetricCard
          title="Tasa de Ocupación"
          value={`${(inventory.occupancy_rate * 100).toFixed(1)}%`}
          subtitle="Stock presente"
          icon={<Percent size={18} />}
          variant="info"
          percentage={inventory.occupancy_rate * 100}
        />
        <MetricCard
          title="Tasa de Espacios Vacíos"
          value={`${(inventory.empty_rate * 100).toFixed(1)}%`}
          subtitle={inventory.roi_applied ? 'Con ROI activo' : 'Estante global'}
          icon={<PackageX size={18} />}
          variant={isHighEmpty ? 'danger' : 'default'}
          percentage={inventory.empty_rate * 100}
        />
      </div>

      {/* Fila 2: Video en Vivo + Panel de Rendimiento del Modelo */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <VideoPlayer
            cameraStatus={camera.status}
            fps={camera.fps}
            resolution={camera.resolution}
            source={camera.source}
          />
        </div>

        {/* Panel Lateral: Modelo e Inferencia */}
        <div className="space-y-4">
          <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
              <div className="flex items-center gap-2">
                <Boxes size={18} className="text-blue-400" />
                <h3 className="font-semibold text-sm text-slate-100">Modelo Activo</h3>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                {model.version}
              </span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Arquitectura:</span>
                <span className="font-mono text-slate-200">YOLOv8n (detect)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Clases del Modelo:</span>
                <span className="font-mono text-slate-200">0: missing | 1: product</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Confidence Threshold:</span>
                <span className="font-mono text-slate-200">{model.confidence_threshold}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">IoU Threshold:</span>
                <span className="font-mono text-slate-200">{model.iou_threshold}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">FPS de Inferencia:</span>
                <span className="font-mono font-bold text-emerald-400">{model.inference_fps} FPS</span>
              </div>
            </div>
          </div>

          {/* Desglose de Latencias */}
          <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
            <div className="flex items-center gap-2 mb-3">
              <Clock size={16} className="text-indigo-400" />
              <h3 className="font-semibold text-xs text-slate-200">Desglose de Latencia</h3>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-slate-400">Preprocess:</span>
                <span className="text-slate-200">{model.timings.preprocess_ms} ms</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Inferencia PyTorch:</span>
                <span className="text-emerald-400 font-bold">{model.timings.inference_ms} ms</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Postprocess / NMS:</span>
                <span className="text-slate-200">{model.timings.postprocess_ms} ms</span>
              </div>
              <div className="flex justify-between pt-2 border-t border-slate-800 font-bold">
                <span className="text-slate-300">Latencia Total:</span>
                <span className="text-blue-400">{model.timings.total_ms} ms</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Fila 3: Monitor de Sistema (CPU, RAM, GPU RTX 3060) */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
          Hardware & Telemetría del Sistema
        </h3>
        <SystemMonitor system={system} />
      </div>
    </div>
  );
};
