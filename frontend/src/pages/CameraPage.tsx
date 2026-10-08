import React, { useState, useEffect } from 'react';
import { 
  Camera, 
  Sliders, 
  Crop, 
  Check, 
  WifiOff,
  VideoOff,
  Trash2,
  Plus,
  Tv,
  Layers,
  Sparkles
} from 'lucide-react';
import { TelemetryMessage } from '../types';
import { VideoPlayer } from '../components/VideoPlayer';
import { api } from '../services/api';

interface CameraPageProps {
  telemetry: TelemetryMessage | null;
}

export interface CameraSlot {
  id: string;
  label: string;
  streamUrl: string;
  status: 'connected' | 'connecting' | 'disconnected' | 'no_signal';
  fps?: number;
  resolution?: { width: number; height: number };
}

/** Panel de Sin Señal cuando hay un slot sin video */
const NoSignalPanel: React.FC<{ label?: string; subtitle?: string }> = ({ 
  label = 'Sin Señal', 
  subtitle = 'No hay señal de video disponible' 
}) => (
  <div className="flex flex-col items-center justify-center h-full min-h-[240px] rounded-2xl border border-slate-800 bg-slate-950/80 text-center p-6 gap-3 shadow-inner">
    <div className="w-14 h-14 rounded-full bg-slate-900 border border-slate-700/80 flex items-center justify-center shadow-lg">
      <VideoOff size={24} className="text-slate-500" />
    </div>
    <div>
      <p className="text-sm font-bold text-slate-300">{label}</p>
      <p className="text-xs text-slate-500 mt-1">{subtitle}</p>
    </div>
    <span className="flex items-center gap-1.5 text-[11px] text-slate-500 font-mono bg-slate-900 px-3 py-1 rounded-full border border-slate-800">
      <WifiOff size={12} className="text-amber-500" />
      Sin Señal / No Video
    </span>
  </div>
);

/** Panel cuando existen 0 cámaras disponibles */
const NoCamerasPanel: React.FC = () => (
  <div className="flex flex-col items-center justify-center min-h-[320px] rounded-2xl border border-slate-700/60 bg-slate-900/60 text-center p-8 gap-4 shadow-xl">
    <div className="w-16 h-16 rounded-full bg-slate-800/90 border border-slate-700 flex items-center justify-center shadow-lg">
      <Camera size={30} className="text-slate-400" />
    </div>
    <div>
      <h3 className="text-base font-extrabold text-slate-200">Sin cámaras disponibles</h3>
      <p className="text-xs text-slate-400 mt-2 max-w-md mx-auto leading-relaxed">
        No se han detectado cámaras activas en el sistema. Conecta una cámara web USB, configura un stream RTSP o activa el simulador para iniciar el monitoreo visual.
      </p>
    </div>
    <span className="px-3.5 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-300 font-mono flex items-center gap-2 shadow-sm">
      <VideoOff size={14} className="text-rose-400" />
      No Video / Sin cámaras
    </span>
  </div>
);

export const CameraPage: React.FC<CameraPageProps> = ({ telemetry }) => {
  const [sourceType, setSourceType] = useState<string>('webcam');
  const [webcamIndex, setWebcamIndex] = useState<number>(0);
  const [rtspUrl, setRtspUrl] = useState<string>('');
  const [confidence, setConfidence] = useState<number>(0.25);
  const [iou, setIou] = useState<number>(0.45);
  const [roi, setRoi] = useState<number[] | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // Lista de cámaras
  const [cameras, setCameras] = useState<CameraSlot[]>([
    {
      id: 'main',
      label: 'Cámara Principal (Live Stream)',
      streamUrl: '/api/camera/stream',
      status: 'connected'
    }
  ]);

  // Modo de visualización: 'auto' sigue el estado del hardware, o presets '0', '1', '2', '3', '4'
  const [viewPreset, setViewPreset] = useState<'auto' | '0' | '1' | '2' | '3' | '4'>('auto');

  // Modal para agregar cámara
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [newCamLabel, setNewCamLabel] = useState<string>('');
  const [newCamUrl, setNewCamUrl] = useState<string>('');

  useEffect(() => {
    api.getRoi().then((res) => {
      if (res.roi) setRoi(res.roi);
    });
    if (telemetry?.model) {
      setConfidence(telemetry.model.confidence_threshold);
      setIou(telemetry.model.iou_threshold);
    }
  }, []);

  // Sincronizar estado de la cámara principal con la telemetría del backend
  useEffect(() => {
    if (telemetry?.camera) {
      const isConnected = telemetry.camera.status === 'CONNECTED';
      const isConnecting = telemetry.camera.status === 'CONNECTING';
      const status: CameraSlot['status'] = isConnected ? 'connected' : isConnecting ? 'connecting' : 'disconnected';

      setCameras(prev => {
        const main = prev.find(c => c.id === 'main');
        if (main) {
          return prev.map(c => c.id === 'main' ? {
            ...c,
            status,
            label: `Cámara Principal (${telemetry.camera.source || sourceType})`,
            fps: telemetry.camera.fps,
            resolution: telemetry.camera.resolution
          } : c);
        }
        return [
          {
            id: 'main',
            label: `Cámara Principal (${telemetry.camera.source || sourceType})`,
            streamUrl: '/api/camera/stream',
            status,
            fps: telemetry.camera.fps,
            resolution: telemetry.camera.resolution
          },
          ...prev
        ];
      });
    }
  }, [telemetry?.camera?.status, telemetry?.camera?.fps, telemetry?.camera?.source]);

  const handleApplySource = async () => {
    try {
      await api.setCameraSource(sourceType, webcamIndex, rtspUrl);
      const label = sourceType === 'rtsp' 
        ? `Cámara IP (${rtspUrl || 'RTSP'})` 
        : sourceType === 'synthetic' 
          ? 'Simulador Sintético de Góndola' 
          : `Webcam USB #${webcamIndex}`;
      setCameras(prev => prev.map(c => c.id === 'main' ? { ...c, label, status: 'connecting' } : c));
      setStatusMsg('Fuente de cámara actualizada correctamente');
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e: any) {
      setStatusMsg('Error al actualizar fuente de cámara');
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
      setStatusMsg(newRoi ? 'Zona de Interés (ROI) aplicada' : 'ROI restablecido');
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e: any) {
      setStatusMsg('Error al configurar ROI');
      setTimeout(() => setStatusMsg(null), 3000);
    }
  };

  const handleAddCamera = () => {
    if (!newCamLabel.trim()) return;
    const newId = `cam-${Date.now()}`;
    setCameras(prev => [
      ...prev,
      {
        id: newId,
        label: newCamLabel.trim(),
        streamUrl: newCamUrl.trim() || '/api/camera/stream',
        status: 'connected'
      }
    ]);
    setNewCamLabel('');
    setNewCamUrl('');
    setShowAddModal(false);
    setViewPreset('auto');
    setStatusMsg(`Cámara "${newCamLabel}" agregada correctamente`);
    setTimeout(() => setStatusMsg(null), 3000);
  };

  const handleRemoveCamera = (id: string) => {
    setCameras(prev => prev.filter(c => c.id !== id));
  };

  // Calcular las cámaras que deben mostrarse según el preset o el estado automático
  const getRenderedCameras = (): CameraSlot[] => {
    if (viewPreset === '0') return [];
    if (viewPreset === '1') {
      const first = cameras[0] || {
        id: 'main',
        label: 'Cámara Principal',
        streamUrl: '/api/camera/stream',
        status: 'connected'
      };
      return [{ ...first, status: 'connected' }];
    }
    if (viewPreset === '2') {
      return [
        cameras[0] || { id: 'main', label: 'Cámara 1 (Góndola A)', streamUrl: '/api/camera/stream', status: 'connected' },
        cameras[1] || { id: 'cam-2', label: 'Cámara 2 (Góndola B)', streamUrl: '/api/camera/stream', status: 'connected' },
      ];
    }
    if (viewPreset === '3') {
      return [
        cameras[0] || { id: 'main', label: 'Cámara 1 (Góndola A)', streamUrl: '/api/camera/stream', status: 'connected' },
        cameras[1] || { id: 'cam-2', label: 'Cámara 2 (Góndola B)', streamUrl: '/api/camera/stream', status: 'connected' },
        cameras[2] || { id: 'cam-3', label: 'Cámara 3 (Pasillo Central)', streamUrl: '/api/camera/stream', status: 'connected' },
      ];
    }
    if (viewPreset === '4') {
      return [
        cameras[0] || { id: 'main', label: 'Cámara 1 (Góndola A)', streamUrl: '/api/camera/stream', status: 'connected' },
        cameras[1] || { id: 'cam-2', label: 'Cámara 2 (Góndola B)', streamUrl: '/api/camera/stream', status: 'connected' },
        cameras[2] || { id: 'cam-3', label: 'Cámara 3 (Pasillo Central)', streamUrl: '/api/camera/stream', status: 'connected' },
        cameras[3] || { id: 'cam-4', label: 'Cámara 4 (Cabecera Sur)', streamUrl: '/api/camera/stream', status: 'connected' },
      ];
    }

    // Modo automático: mostrar todas las cámaras configuradas para evitar que desaparezcan al pausar
    return cameras;
  };

  const activeCameras = getRenderedCameras();
  const cameraCount = activeCameras.length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            Visor de Detección &amp; Configuración de Cámaras
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800">
              Grid Adaptativo
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Distribución responsive automática según cantidad de fuentes activas con soporte multi-cámara
          </p>
        </div>
        {statusMsg && (
          <div className="flex items-center gap-2 bg-blue-950/80 text-blue-300 border border-blue-800/60 px-3.5 py-1.5 rounded-lg text-xs font-medium animate-fadeIn">
            <Check size={14} className="text-blue-400" />
            {statusMsg}
          </div>
        )}
      </div>

      {/* Barra de control de layout y selector de pruebas */}
      <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-wrap items-center justify-between gap-3 shadow-md">
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400 font-semibold flex items-center gap-1.5">
            <Tv size={14} className="text-cyan-400" />
            Layout de Cámaras:
          </span>
          <div className="inline-flex rounded-lg bg-slate-950 p-1 border border-slate-800 gap-1 text-[11px]">
            <button
              onClick={() => setViewPreset('auto')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${viewPreset === 'auto' ? 'bg-cyan-600 text-white font-bold shadow' : 'text-slate-400 hover:text-slate-200'}`}
              title="Modo automático según cámaras detectadas"
            >
              Auto ({cameras.filter(c => c.status === 'connected').length} Activa{cameras.filter(c => c.status === 'connected').length === 1 ? '' : 's'})
            </button>
            <button
              onClick={() => setViewPreset('0')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${viewPreset === '0' ? 'bg-cyan-600 text-white font-bold shadow' : 'text-slate-400 hover:text-slate-200'}`}
              title="Probar 0 cámaras (Sin cámaras / No Video)"
            >
              0 Cámaras
            </button>
            <button
              onClick={() => setViewPreset('1')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${viewPreset === '1' ? 'bg-cyan-600 text-white font-bold shadow' : 'text-slate-400 hover:text-slate-200'}`}
              title="Probar 1 cámara (2 paneles: Cámara + Sin Señal)"
            >
              1 Cámara (2 Paneles)
            </button>
            <button
              onClick={() => setViewPreset('2')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${viewPreset === '2' ? 'bg-cyan-600 text-white font-bold shadow' : 'text-slate-400 hover:text-slate-200'}`}
              title="Probar 2 cámaras activas"
            >
              2 Cámaras
            </button>
            <button
              onClick={() => setViewPreset('3')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${viewPreset === '3' ? 'bg-cyan-600 text-white font-bold shadow' : 'text-slate-400 hover:text-slate-200'}`}
              title="Probar 3 cámaras (Grid responsive)"
            >
              3 Cámaras
            </button>
            <button
              onClick={() => setViewPreset('4')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${viewPreset === '4' ? 'bg-cyan-600 text-white font-bold shadow' : 'text-slate-400 hover:text-slate-200'}`}
              title="Probar 4 cámaras (Grid 2x2)"
            >
              4 Cámaras
            </button>
          </div>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 text-xs font-semibold transition-all"
        >
          <Plus size={13} />
          Agregar Cámara
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Columna Izquierda: Grid de Cámaras */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400 pb-1">
            <span className="flex items-center gap-2 font-medium">
              <Camera size={14} className="text-cyan-400" />
              <span>
                {cameraCount === 0 
                  ? '0 cámaras detectadas — Modo "No Video"' 
                  : cameraCount === 1 
                    ? '1 cámara activa — Layout obligatorio de 2 paneles (Cámara + Sin Señal)' 
                    : `${cameraCount} cámaras activas — Grid Adaptativo`}
              </span>
            </span>
            <span className="font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              Formato: {cameraCount === 0 ? 'Sin video' : cameraCount === 1 ? '1×2 Paneles' : cameraCount === 2 ? '1×2 Paneles' : cameraCount === 3 ? '1×3 Responsive' : '2×2 Grid'}
            </span>
          </div>

          {/* CASO 0 CÁMARAS: Mostrar "Sin cámaras" / "No Video" */}
          {cameraCount === 0 && <NoCamerasPanel />}

          {/* CASO 1 CÁMARA: Mostrar 2 paneles (Panel 1: Cámara, Panel 2: "Sin Señal") */}
          {cameraCount === 1 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="relative rounded-2xl overflow-hidden border border-slate-700/80 bg-slate-950 shadow-xl">
                <VideoPlayer
                  cameraStatus={telemetry?.camera.status || 'CONNECTED'}
                  fps={telemetry?.camera.fps || 30}
                  resolution={telemetry?.camera.resolution || { width: 1280, height: 720 }}
                  source={activeCameras[0]?.streamUrl || '/api/camera/stream'}
                />
                <div className="absolute top-2.5 left-2.5 z-20 flex items-center gap-1.5 bg-black/70 backdrop-blur-sm rounded-lg px-2.5 py-1 text-xs text-emerald-300 font-mono border border-emerald-500/30">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  {activeCameras[0]?.label || 'Cámara Principal'}
                </div>
              </div>

              {/* Segundo panel obligatorio: Sin Señal */}
              <NoSignalPanel label="Panel 2 — Sin Señal" subtitle="Cámara secundaria no configurada" />
            </div>
          )}

          {/* CASO 2 CÁMARAS: Mostrar ambas cámaras */}
          {cameraCount === 2 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {activeCameras.map((cam, idx) => (
                <div key={cam.id} className="relative rounded-2xl overflow-hidden border border-slate-700/80 bg-slate-950 shadow-xl">
                  {idx === 0 ? (
                    <VideoPlayer
                      cameraStatus={telemetry?.camera.status || 'CONNECTED'}
                      fps={telemetry?.camera.fps || 30}
                      resolution={telemetry?.camera.resolution || { width: 1280, height: 720 }}
                      source={cam.streamUrl}
                    />
                  ) : (
                    <div className="relative aspect-video flex flex-col items-center justify-center bg-slate-950 p-4">
                      <VideoPlayer
                        cameraStatus="CONNECTED"
                        fps={25}
                        resolution={{ width: 1280, height: 720 }}
                        source={cam.streamUrl}
                      />
                    </div>
                  )}
                  <div className="absolute top-2.5 left-2.5 z-20 flex items-center gap-1.5 bg-black/70 backdrop-blur-sm rounded-lg px-2.5 py-1 text-xs text-slate-200 font-mono border border-slate-700/50">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    {cam.label}
                  </div>
                  {cam.id !== 'main' && (
                    <button
                      onClick={() => handleRemoveCamera(cam.id)}
                      className="absolute top-2.5 right-2.5 z-20 p-1.5 rounded-lg bg-rose-950/80 text-rose-300 hover:bg-rose-800 border border-rose-700/60 transition-colors"
                      title="Eliminar cámara"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* CASO 3+ CÁMARAS: Grid responsive automático */}
          {cameraCount >= 3 && (
            <div className={`grid grid-cols-1 sm:grid-cols-2 ${cameraCount === 3 ? 'xl:grid-cols-3' : 'xl:grid-cols-2'} gap-4`}>
              {activeCameras.map((cam, idx) => (
                <div key={cam.id} className="relative rounded-2xl overflow-hidden border border-slate-700/80 bg-slate-950 shadow-xl">
                  <div className="aspect-video relative">
                    <VideoPlayer
                      cameraStatus={idx === 0 ? (telemetry?.camera.status || 'CONNECTED') : 'CONNECTED'}
                      fps={idx === 0 ? (telemetry?.camera.fps || 30) : 25}
                      resolution={idx === 0 ? (telemetry?.camera.resolution || { width: 1280, height: 720 }) : { width: 1280, height: 720 }}
                      source={cam.streamUrl}
                    />
                  </div>
                  <div className="absolute top-2.5 left-2.5 z-20 flex items-center gap-1.5 bg-black/70 backdrop-blur-sm rounded-lg px-2 py-0.5 text-[11px] text-slate-200 font-mono border border-slate-700/50">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    {cam.label}
                  </div>
                  {cam.id !== 'main' && (
                    <button
                      onClick={() => handleRemoveCamera(cam.id)}
                      className="absolute top-2.5 right-2.5 z-20 p-1.5 rounded-lg bg-rose-950/80 text-rose-300 hover:bg-rose-800 border border-rose-700/60 transition-colors"
                      title="Eliminar cámara"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Leyenda de Clases */}
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-wrap items-center justify-between text-xs gap-3">
            <div className="flex items-center gap-4">
              <span className="text-slate-400 font-medium">Leyenda YOLOv8:</span>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-emerald-500 shadow-sm" />
                <span className="text-slate-200">Product (Producto presente)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-rose-500 shadow-sm" />
                <span className="text-slate-200">Missing (Espacio vacío / Faltante)</span>
              </div>
            </div>
            {roi && (
              <span className="text-amber-400 font-mono font-medium bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800/40">
                ROI Activo [{roi.join(', ')}]
              </span>
            )}
          </div>
        </div>

        {/* Columna Derecha: Configuración */}
        <div className="space-y-4">
          {/* Fuente de Video */}
          <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
              <Camera size={16} className="text-blue-400" />
              <h3 className="font-semibold text-xs text-slate-100 uppercase tracking-wide">Fuente de Video Principal</h3>
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
                  <option value="synthetic">Simulador Sintético de Góndola</option>
                </select>
              </div>

              {(sourceType === 'webcam' || sourceType === 'usb') ? (
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
                  <label className="text-xs text-slate-400 block mb-1">URL RTSP:</label>
                  <input 
                    type="text" 
                    placeholder="rtsp://user:pass@192.168.1.50:554/stream" 
                    value={rtspUrl} 
                    onChange={(e) => setRtspUrl(e.target.value)} 
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono" 
                  />
                </div>
              ) : (
                <p className="text-xs text-slate-400 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                  Modo simulador activo. Genera fotogramas de góndola con productos y faltantes aleatorios.
                </p>
              )}

              <button 
                onClick={handleApplySource} 
                className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-all shadow-md shadow-blue-600/20 active:scale-95"
              >
                Conectar Fuente
              </button>
            </div>
          </div>

          {/* Umbrales YOLOv8 */}
          <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
              <Sliders size={16} className="text-indigo-400" />
              <h3 className="font-semibold text-xs text-slate-100 uppercase tracking-wide">Umbrales YOLOv8</h3>
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
                className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition-all border border-slate-700 active:scale-95"
              >
                Aplicar Umbrales en Caliente
              </button>
            </div>
          </div>

          {/* Región de Interés (ROI) */}
          <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
              <Crop size={16} className="text-amber-400" />
              <h3 className="font-semibold text-xs text-slate-100 uppercase tracking-wide">Zona de Interés (ROI)</h3>
            </div>
            <p className="text-xs text-slate-400">
              Aísla la estantería del entorno para evitar falsos positivos de clientes o pasillos.
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button 
                onClick={() => handleSetRoi([0.1, 0.2, 0.9, 0.85])} 
                className="p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-amber-500/50 text-slate-300 transition-all text-center"
              >
                Estante Central
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

      {/* Modal Agregar Cámara */}
      {showAddModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
          onClick={() => setShowAddModal(false)}
        >
          <div 
            className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="font-bold text-base text-white flex items-center gap-2">
                <Camera size={18} className="text-cyan-400" />
                Agregar Nueva Cámara
              </h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Nombre / Identificador:</label>
                <input
                  type="text"
                  placeholder="ej. Cámara 2 (Pasillo B)"
                  value={newCamLabel}
                  onChange={(e) => setNewCamLabel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">URL de Stream o Endpoint (opcional):</label>
                <input
                  type="text"
                  placeholder="/api/camera/stream o rtsp://..."
                  value={newCamUrl}
                  onChange={(e) => setNewCamUrl(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono"
                />
                <p className="text-[11px] text-slate-500 mt-1">Por defecto utiliza el stream en vivo activo del sistema.</p>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700"
              >
                Cancelar
              </button>
              <button
                onClick={handleAddCamera}
                disabled={!newCamLabel.trim()}
                className="px-4 py-2 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-500 disabled:opacity-50"
              >
                Agregar al Grid
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
