import React, { useState, useEffect } from 'react';
import { 
  Camera, 
  Sliders, 
  Crop, 
  Settings2, 
  RefreshCw, 
  Check, 
  AlertCircle 
} from 'lucide-react';
import { TelemetryMessage } from '../types';
import { VideoPlayer } from '../components/VideoPlayer';
import { api } from '../services/api';

interface CameraPageProps {
  telemetry: TelemetryMessage | null;
}

export const CameraPage: React.FC<CameraPageProps> = ({ telemetry }) => {
  const [sourceType, setSourceType] = useState<string>('webcam');
  const [webcamIndex, setWebcamIndex] = useState<number>(0);
  const [rtspUrl, setRtspUrl] = useState<string>('');
  const [confidence, setConfidence] = useState<number>(0.25);
  const [iou, setIou] = useState<number>(0.45);
  const [roi, setRoi] = useState<number[] | null>(null);
  const [customRoi, setCustomRoi] = useState({ x1: 0.1, y1: 0.2, x2: 0.9, y2: 0.8 });
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    // Cargar ROI y umbrales iniciales
    api.getRoi().then((res) => {
      if (res.roi) {
        setRoi(res.roi);
        setCustomRoi({ x1: res.roi[0], y1: res.roi[1], x2: res.roi[2], y2: res.roi[3] });
      }
    });
    if (telemetry?.model) {
      setConfidence(telemetry.model.confidence_threshold);
      setIou(telemetry.model.iou_threshold);
    }
  }, []);

  const handleApplySource = async () => {
    try {
      await api.setCameraSource(sourceType, webcamIndex, rtspUrl);
      setStatusMsg('Fuente de cámara actualizada correctamente');
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e: any) {
      setStatusMsg('Error al actualizar fuente');
      setTimeout(() => setStatusMsg(null), 3000);
    }
  };

  const handleApplyThresholds = async () => {
    try {
      await api.updateThresholds(confidence, iou);
      setStatusMsg('Umbrales de detección actualizados');
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e: any) {
      setStatusMsg('Error al actualizar umbrales');
      setTimeout(() => setStatusMsg(null), 3000);
    }
  };

  const handleSetRoi = async (newRoi: number[] | null) => {
    try {
      await api.setRoi(newRoi);
      setRoi(newRoi);
      setStatusMsg(newRoi ? 'Región de Interés (ROI) aplicada' : 'ROI restablecido a vista completa');
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e: any) {
      setStatusMsg('Error al configurar ROI');
      setTimeout(() => setStatusMsg(null), 3000);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Visor de Detección & Configuración de Cámara</h2>
          <p className="text-xs text-slate-400 mt-1">
            Transmisión de baja latencia con bounding boxes YOLOv8, umbrales y filtrado por zona (ROI)
          </p>
        </div>

        {statusMsg && (
          <div className="flex items-center gap-2 bg-blue-950/80 text-blue-300 border border-blue-800/60 px-3.5 py-1.5 rounded-lg text-xs font-medium">
            <Check size={14} className="text-blue-400" />
            {statusMsg}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Stream Principal */}
        <div className="lg:col-span-2 space-y-4">
          <VideoPlayer
            cameraStatus={telemetry?.camera.status || 'CONNECTING'}
            fps={telemetry?.camera.fps || 0}
            resolution={telemetry?.camera.resolution || { width: 1280, height: 720 }}
            source={telemetry?.camera.source || sourceType}
          />

          {/* Información de Etiquetas */}
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-center justify-between text-xs">
            <div className="flex items-center gap-4">
              <span className="text-slate-400 font-medium">Leyenda de Clases:</span>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-emerald-500" />
                <span className="text-slate-200">Product (Producto presente)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-rose-500" />
                <span className="text-slate-200">Missing (Espacio vacío / Gancho libre)</span>
              </div>
            </div>
            {roi && (
              <span className="text-amber-400 font-mono font-medium">ROI Activo [{roi.join(', ')}]</span>
            )}
          </div>
        </div>

        {/* Panel de Controles: Fuente, Umbrales y ROI */}
        <div className="space-y-4">
          {/* 1. Selector de Fuente */}
          <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
              <Camera size={16} className="text-blue-400" />
              <h3 className="font-semibold text-xs text-slate-100">Fuente de Video</h3>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Tipo de Cámara:</label>
                <select
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value="webcam">Webcam Integrada / USB (Índice)</option>
                  <option value="usb">Cámara USB Externa</option>
                  <option value="rtsp">Cámara IP (RTSP Segura)</option>
                  <option value="synthetic">Simulador Sintético de Estantería</option>
                </select>
              </div>

              {sourceType === 'webcam' || sourceType === 'usb' ? (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Índice del Dispositivo:</label>
                  <input
                    type="number"
                    min="0"
                    max="10"
                    value={webcamIndex}
                    onChange={(e) => setWebcamIndex(parseInt(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                  />
                </div>
              ) : sourceType === 'rtsp' ? (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">URL de Stream RTSP (backend-only):</label>
                  <input
                    type="text"
                    placeholder="rtsp://user:pass@192.168.1.50:554/stream"
                    value={rtspUrl}
                    onChange={(e) => setRtspUrl(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Las credenciales no se transfieren al navegador.</p>
                </div>
              ) : (
                <p className="text-xs text-slate-400 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                  Modo simulador activo. Genera fotogramas de góndola con productos y faltantes aleatorios para pruebas continuas sin cámara física.
                </p>
              )}

              <button
                onClick={handleApplySource}
                className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-all shadow-md shadow-blue-600/20"
              >
                Conectar Fuente
              </button>
            </div>
          </div>

          {/* 2. Umbrales de Detección */}
          <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
              <Sliders size={16} className="text-indigo-400" />
              <h3 className="font-semibold text-xs text-slate-100">Umbrales YOLOv8</h3>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-slate-400">Confidence Threshold:</span>
                  <span className="font-mono text-blue-400 font-bold">{confidence}</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.95"
                  step="0.05"
                  value={confidence}
                  onChange={(e) => setConfidence(parseFloat(e.target.value))}
                  className="w-full accent-blue-500 bg-slate-800 rounded-lg h-1.5 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-slate-400">IoU (NMS) Threshold:</span>
                  <span className="font-mono text-indigo-400 font-bold">{iou}</span>
                </div>
                <input
                  type="range"
                  min="0.10"
                  max="0.90"
                  step="0.05"
                  value={iou}
                  onChange={(e) => setIou(parseFloat(e.target.value))}
                  className="w-full accent-indigo-500 bg-slate-800 rounded-lg h-1.5 cursor-pointer"
                />
              </div>

              <button
                onClick={handleApplyThresholds}
                className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition-all border border-slate-700"
              >
                Aplicar Umbrales en Caliente
              </button>
            </div>
          </div>

          {/* 3. Región de Interés (ROI) */}
          <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
              <Crop size={16} className="text-amber-400" />
              <h3 className="font-semibold text-xs text-slate-100">Zona de Interés (ROI)</h3>
            </div>

            <p className="text-xs text-slate-400">
              Aísla la estantería del entorno para evitar falsos positivos de clientes o pasillos.
            </p>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                onClick={() => handleSetRoi([0.1, 0.2, 0.9, 0.85])}
                className="p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-amber-500/50 text-slate-300 transition-all text-center"
              >
                Estante Central (90%)
              </button>
              <button
                onClick={() => handleSetRoi([0.05, 0.1, 0.95, 0.5])}
                className="p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-amber-500/50 text-slate-300 transition-all text-center"
              >
                Nivel Superior
              </button>
            </div>

            <button
              onClick={() => handleSetRoi(null)}
              className="w-full py-2 bg-slate-950 hover:bg-slate-800 text-rose-400 rounded-lg text-xs font-semibold transition-all border border-slate-800"
            >
              Restablecer / Desactivar ROI
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
