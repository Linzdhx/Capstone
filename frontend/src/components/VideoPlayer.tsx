import React, { useState } from 'react';
import { 
  Play, 
  Pause, 
  Camera, 
  Maximize2, 
  Sliders, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle 
} from 'lucide-react';
import { api } from '../services/api';

interface VideoPlayerProps {
  cameraStatus: string;
  fps: number;
  resolution: { width: number; height: number };
  source: string;
  onSnapshotCaptured?: () => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  cameraStatus,
  fps,
  resolution,
  source,
  onSnapshotCaptured,
}) => {
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [isCapturing, setIsCapturing] = useState<boolean>(false);
  const [captureMsg, setCaptureMsg] = useState<string | null>(null);

  const togglePlayback = async () => {
    try {
      const nextAction = isPlaying ? 'stop' : 'start';
      await api.controlCamera(nextAction);
      setIsPlaying(!isPlaying);
    } catch (e) {
      console.error('Error toggling camera:', e);
    }
  };

  const handleManualCapture = async () => {
    try {
      setIsCapturing(true);
      const res = await api.captureSample();
      setCaptureMsg('¡Muestra guardada en Revisión!');
      if (onSnapshotCaptured) onSnapshotCaptured();
      setTimeout(() => setCaptureMsg(null), 3000);
    } catch (err: any) {
      setCaptureMsg('Error al capturar');
      setTimeout(() => setCaptureMsg(null), 3000);
    } finally {
      setIsCapturing(false);
    }
  };

  return (
    <div className="relative rounded-2xl overflow-hidden border border-slate-800 bg-[#06090e] shadow-2xl">
      {/* Top Overlay Banner */}
      <div className="absolute top-0 inset-x-0 z-10 flex items-center justify-between p-3 bg-gradient-to-b from-black/80 via-black/40 to-transparent">
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 relative">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                cameraStatus === 'CONNECTED' ? 'bg-emerald-400' : 'bg-rose-400'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                cameraStatus === 'CONNECTED' ? 'bg-emerald-500' : 'bg-rose-500'
              }`}
            />
          </span>
          <span className="text-xs font-mono font-medium text-slate-200">
            {cameraStatus} ({source})
          </span>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono text-slate-300 bg-black/60 px-2.5 py-1 rounded-md border border-white/10 backdrop-blur-sm">
          <span>{fps} FPS</span>
          <span className="text-slate-500">|</span>
          <span>{resolution.width}x{resolution.height}</span>
        </div>
      </div>

      {/* Video Content */}
      <div className="relative aspect-video w-full flex items-center justify-center bg-slate-950">
        {isPlaying ? (
          <img
            src="/api/camera/stream"
            alt="YOLOv8 Inventory Live Feed"
            className="w-full h-full object-contain"
            onError={() => {
              // Si falla el stream, puede estar reconectando
            }}
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-slate-500 p-8">
            <Pause size={48} className="mb-2 text-slate-600" />
            <p className="text-sm font-medium">Transmisión de video pausada</p>
            <p className="text-xs text-slate-600 mt-1">Presione reanudar para reactivar el stream</p>
          </div>
        )}

        {/* Capture Notification Toast */}
        {captureMsg && (
          <div className="absolute top-14 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 bg-emerald-950/90 text-emerald-200 border border-emerald-700/60 px-4 py-2 rounded-lg text-xs font-medium backdrop-blur-md shadow-lg">
            <CheckCircle2 size={16} className="text-emerald-400" />
            {captureMsg}
          </div>
        )}
      </div>

      {/* Bottom Controls Bar */}
      <div className="flex items-center justify-between p-3 bg-slate-900/90 border-t border-slate-800">
        <div className="flex items-center gap-2">
          <button
            onClick={togglePlayback}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              isPlaying
                ? 'bg-slate-800 hover:bg-slate-700 text-slate-200'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/30'
            }`}
          >
            {isPlaying ? <Pause size={14} /> : <Play size={14} />}
            {isPlaying ? 'Pausar' : 'Reanudar'}
          </button>

          <button
            onClick={handleManualCapture}
            disabled={isCapturing || !isPlaying}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600/20 text-blue-400 border border-blue-500/30 hover:bg-blue-600/30 transition-all disabled:opacity-50"
            title="Guardar fotograma actual para Active Learning"
          >
            <Camera size={14} />
            {isCapturing ? 'Guardando...' : 'Capturar Muestra'}
          </button>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="hidden sm:inline">Bounding boxes YOLOv8 renderizados en backend</span>
        </div>
      </div>
    </div>
  );
};
