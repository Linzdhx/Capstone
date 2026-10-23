import React, { useState, useEffect } from 'react';
import { 
  Camera, 
  Sliders, 
  Crop, 
  Check, 
  AlertCircle,
  Wifi,
  WifiOff,
  VideoOff,
  Trash2,
  Plus,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Cpu,
  Layers,
  Sparkles
} from 'lucide-react';
import { TelemetryMessage, CameraDeviceItem } from '../types';
import { VideoPlayer } from '../components/VideoPlayer';
import { api } from '../services/api';

interface CameraPageProps {
  telemetry: TelemetryMessage | null;
}

export const CameraPage: React.FC<CameraPageProps> = ({ telemetry }) => {
  const [cameras, setCameras] = useState<CameraDeviceItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<{ text: string; isError?: boolean } | null>(null);

  // Modal para agregar cámara IP / RTSP / avanzada
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [newCamName, setNewCamName] = useState<string>('');
  const [newCamSourceType, setNewCamSourceType] = useState<string>('rtsp');
  const [newCamRtspUrl, setNewCamRtspUrl] = useState<string>('');
  const [isSubmittingAdd, setIsSubmittingAdd] = useState<boolean>(false);

  // Panel colapsable de ajustes de inferencia YOLOv8 y ROI
  const [showInferenceSettings, setShowInferenceSettings] = useState<boolean>(false);
  const [confidence, setConfidence] = useState<number>(0.25);
  const [iou, setIou] = useState<number>(0.45);
  const [roi, setRoi] = useState<number[] | null>(null);

  const showNotification = (text: string, isError = false) => {
    setStatusMsg({ text, isError });
    setTimeout(() => setStatusMsg(null), 3500);
  };

  // ─── 1. Carga inicial de cámaras detectadas vía REST ───────────────────────────
  useEffect(() => {
    let isMounted = true;
    api.listCameras()
      .then((data: CameraDeviceItem[]) => {
        if (!isMounted) return;
        if (Array.isArray(data) && data.length > 0) {
          setCameras(data);
        } else {
          // Fallback seguro a main
          setCameras([{
            id: 'main',
            name: 'Cámara Principal',
            stream_url: '/api/camera/stream/main',
            status: 'CONNECTING',
            source_type: 'webcam',
            source_display: 'webcam (index: 0)',
            fps: 0,
            resolution: { width: 1280, height: 720 },
            is_main: true
          }]);
        }
      })
      .catch((err) => {
        console.error('Error cargando lista de cámaras:', err);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    // Cargar ROI e umbrales iniciales
    api.getRoi().then(res => { if (res.roi) setRoi(res.roi); }).catch(() => {});
    if (telemetry?.model) {
      setConfidence(telemetry.model.confidence_threshold);
      setIou(telemetry.model.iou_threshold);
    }

    return () => { isMounted = false; };
  }, []);

  // ─── 2. Sincronización en tiempo real vía WebSocket (Hotplug & Telemetría) ───
  useEffect(() => {
    if (!telemetry?.cameras || !Array.isArray(telemetry.cameras)) return;

    const serverCams: CameraDeviceItem[] = telemetry.cameras;
    setCameras((prev) => {
      const prevMap = new Map(prev.map(c => [c.id, c]));
      const serverIds = new Set(serverCams.map(c => c.id));

      // Actualizar o añadir cámaras provenientes del backend
      const merged: CameraDeviceItem[] = serverCams.map((serverCam) => {
        const existing = prevMap.get(serverCam.id);
        return {
          ...existing,
          ...serverCam,
          name: serverCam.name || existing?.name || (serverCam.id === 'main' ? 'Cámara Principal' : `Cámara ${serverCam.id}`),
          stream_url: serverCam.stream_url || `/api/camera/stream/${serverCam.id}`,
          is_main: serverCam.id === 'main',
        };
      });

      // Si una cámara local ya no está en la telemetría, conservarla como DISCONNECTED
      for (const [id, slot] of prevMap) {
        if (!serverIds.has(id)) {
          merged.push({
            ...slot,
            status: 'DISCONNECTED',
            fps: 0,
            error: 'Dispositivo no detectado o desconectado'
          });
        }
      }

      // Evitar re-renders si la estructura y estados no cambiaron
      if (
        merged.length === prev.length &&
        merged.every((m, i) => 
          prev[i] &&
          prev[i].id === m.id &&
          prev[i].status === m.status &&
          Math.abs((prev[i].fps || 0) - (m.fps || 0)) < 0.5
        )
      ) {
        return prev;
      }

      return merged;
    });
  }, [telemetry?.cameras]);

  // ─── 3. Forzar re-escaneo automático de hardware ──────────────────────────────
  const handleScanCameras = async () => {
    setIsScanning(true);
    try {
      const updatedList = await api.scanCameras();
      if (Array.isArray(updatedList) && updatedList.length > 0) {
        setCameras(updatedList);
        showNotification(`Detección completada: ${updatedList.length} cámara(s) detectadas`);
      } else {
        showNotification('Escaneo finalizado sin nuevas cámaras detectadas', false);
      }
    } catch (e: any) {
      showNotification('Error al escanear cámaras físicas', true);
    } finally {
      setIsScanning(false);
    }
  };

  // ─── 4. Añadir cámara manual (RTSP / Avanzado) ─────────────────────────────────
  const handleAddManualCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newCamSourceType === 'rtsp' && !newCamRtspUrl.trim()) {
      showNotification('Debes ingresar una URL RTSP válida', true);
      return;
    }

    setIsSubmittingAdd(true);
    try {
      const res = await api.addCamera({
        name: newCamName.trim() || undefined,
        source_type: newCamSourceType,
        rtsp_url: newCamRtspUrl.trim() || undefined,
      });

      if (res.camera) {
        setCameras(prev => [...prev.filter(c => c.id !== res.camera.id), res.camera]);
        showNotification(`Cámara "${res.camera.name || res.camera.id}" agregada exitosamente`);
        setShowAddModal(false);
        setNewCamName('');
        setNewCamRtspUrl('');
      } else {
        showNotification(res.message || 'Cámara agregada', false);
      }
    } catch (err: any) {
      showNotification('No se pudo añadir la cámara', true);
    } finally {
      setIsSubmittingAdd(false);
    }
  };

  // ─── 5. Eliminar cámara secundaria ───────────────────────────────────────────
  const handleRemoveCamera = async (camId: string, camName?: string) => {
    if (camId === 'main') {
      showNotification('La cámara principal no puede ser eliminada', true);
      return;
    }

    try {
      await api.removeCamera(camId);
      setCameras(prev => prev.filter(c => c.id !== camId));
      showNotification(`Cámara "${camName || camId}" desconectada y removida`);
    } catch (e) {
      showNotification('Error al eliminar la cámara', true);
    }
  };

  // ─── 6. Guardar umbrales YOLOv8 y ROI ─────────────────────────────────────────
  const handleApplyThresholds = async () => {
    try {
      await api.updateThresholds(confidence, iou);
      showNotification('Umbrales de detección actualizados correctamente');
    } catch {
      showNotification('Error al aplicar umbrales', true);
    }
  };

  const handleSetRoi = async (newRoi: number[] | null) => {
    try {
      await api.setRoi(newRoi);
      setRoi(newRoi);
      showNotification(newRoi ? 'Zona de Interés (ROI) aplicada' : 'ROI restablecido a vista completa');
    } catch {
      showNotification('Error al configurar ROI', true);
    }
  };

  // Renderizador de Badge de Estado
  const renderStatusBadge = (status: string) => {
    const s = (status || '').toUpperCase();
    if (s === 'CONNECTED') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-500/30">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          En vivo
        </span>
      );
    }
    if (s === 'CONNECTING') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-950/80 text-amber-300 border border-amber-500/30">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
          Conectando cámara…
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-rose-950/80 text-rose-300 border border-rose-500/30">
        <span className="w-2 h-2 rounded-full bg-rose-500" />
        Cámara desconectada
      </span>
    );
  };

  const activeConnectedCount = cameras.filter(c => c.status?.toUpperCase() === 'CONNECTED').length;

  return (
    <div className="space-y-6">
      {/* ─── Encabezado Principal ─────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-slate-900/90 via-slate-900/70 to-slate-950 border border-slate-800 shadow-xl backdrop-blur-md">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-100 tracking-tight">
              Cámaras en Vivo
            </h1>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-cyan-950 text-cyan-400 border border-cyan-800">
              <Camera size={13} />
              {cameras.length} {cameras.length === 1 ? 'dispositivo' : 'dispositivos'}
            </span>
            {activeConnectedCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/90 text-emerald-400 border border-emerald-800">
                <Wifi size={12} />
                {activeConnectedCount} en transmisión
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            Detección automática multi-fuente. Cada recuadro visualiza su transmisión y flujo de inferencia YOLOv8 de forma independiente.
          </p>
        </div>

        {/* Acciones Rápidas */}
        <div className="flex items-center gap-2 self-stretch sm:self-auto">
          <button
            onClick={handleScanCameras}
            disabled={isScanning}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all shadow-sm active:scale-95 disabled:opacity-50"
            title="Escanear y auto-detectar cámaras conectadas al sistema"
          >
            <RefreshCw size={14} className={isScanning ? 'animate-spin text-cyan-400' : 'text-slate-400'} />
            <span>{isScanning ? 'Buscando cámaras…' : 'Buscar Cámaras'}</span>
          </button>

          <button
            onClick={() => setShowAddModal(true)}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-all shadow-lg shadow-blue-600/25 active:scale-95"
            title="Añadir cámara IP o RTSP de forma manual"
          >
            <Plus size={15} />
            <span>Añadir Cámara IP</span>
          </button>
        </div>
      </div>

      {/* ─── Mensaje de Notificación Flotante ─────────────────────────────── */}
      {statusMsg && (
        <div className={`flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-xs font-medium border shadow-lg animate-fadeIn ${
          statusMsg.isError 
            ? 'bg-rose-950/90 text-rose-200 border-rose-800' 
            : 'bg-emerald-950/90 text-emerald-200 border-emerald-800'
        }`}>
          {statusMsg.isError ? <AlertCircle size={16} className="text-rose-400 shrink-0" /> : <Check size={16} className="text-emerald-400 shrink-0" />}
          <span>{statusMsg.text}</span>
        </div>
      )}

      {/* ─── Estado de Carga / Sin Cámaras ───────────────────────────────── */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[360px] rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center space-y-3">
          <RefreshCw size={32} className="animate-spin text-cyan-400" />
          <h3 className="text-base font-bold text-slate-200">Buscando cámaras disponibles…</h3>
          <p className="text-xs text-slate-500 max-w-sm">
            Inicializando servicios de captura de video y enumerando hardware de cámara compatible.
          </p>
        </div>
      ) : cameras.length === 0 ? (
        <div className="flex flex-col items-center justify-center min-h-[380px] rounded-2xl border border-dashed border-slate-700 bg-slate-950/60 p-8 text-center space-y-4 shadow-inner">
          <div className="w-16 h-16 rounded-2xl bg-slate-900 border border-slate-700 flex items-center justify-center shadow-lg text-slate-400">
            <VideoOff size={32} />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-100">No se encontraron cámaras disponibles</h3>
            <p className="text-xs text-slate-400 mt-1.5 max-w-md mx-auto leading-relaxed">
              No hay dispositivos de video USB ni transmisiones RTSP conectadas activamente al sistema. Conecta una cámara web USB o añade una transmisión IP.
            </p>
          </div>
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleScanCameras}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white shadow-md transition-all active:scale-95"
            >
              <RefreshCw size={14} />
              Re-escanear cámaras
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all active:scale-95"
            >
              <Plus size={14} />
              Configurar cámara IP
            </button>
          </div>
        </div>
      ) : (
        /* ─── Grid de Cámaras Adaptativo y Dinámico ──────────────────────── */
        <div className={`grid gap-6 ${
          cameras.length === 1 
            ? 'grid-cols-1 max-w-4xl mx-auto' 
            : cameras.length === 2 
              ? 'grid-cols-1 lg:grid-cols-2' 
              : 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3'
        }`}>
          {cameras.map((cam) => {
            const isMain = cam.id === 'main';
            const isConnected = cam.status?.toUpperCase() === 'CONNECTED';
            const fpsVal = cam.fps !== undefined ? cam.fps : (isMain ? (telemetry?.camera.fps || 0) : 0);
            const resVal = cam.resolution || (isMain ? (telemetry?.camera.resolution || { width: 1280, height: 720 }) : { width: 1280, height: 720 });

            return (
              <div 
                key={cam.id} 
                className="flex flex-col rounded-2xl overflow-hidden border border-slate-800 bg-slate-900/70 shadow-2xl backdrop-blur-sm transition-all hover:border-slate-700/80"
              >
                {/* Cabecera de la Cámara */}
                <div className="flex items-center justify-between p-3.5 bg-slate-950/80 border-b border-slate-800/80 gap-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border ${
                      isMain 
                        ? 'bg-blue-950/80 text-blue-400 border-blue-800/60' 
                        : 'bg-slate-800 text-slate-300 border-slate-700'
                    }`}>
                      <Camera size={16} />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h2 className="text-xs sm:text-sm font-bold text-slate-100 truncate">
                          {cam.name || (isMain ? 'Cámara Principal' : `Cámara ${cam.id}`)}
                        </h2>
                        {isMain && (
                          <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-900/60 text-blue-300 border border-blue-700/40">
                            Principal
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400 font-mono truncate">
                        ID: {cam.id} • {cam.source_display || cam.source_type}
                      </p>
                    </div>
                  </div>

                  {/* Estado y Opciones */}
                  <div className="flex items-center gap-2 shrink-0">
                    {renderStatusBadge(cam.status)}

                    {!isMain && (
                      <button
                        onClick={() => handleRemoveCamera(cam.id, cam.name)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-300 hover:bg-rose-950/60 border border-transparent hover:border-rose-800/60 transition-all"
                        title="Eliminar cámara"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Reproductor de Video Independiente */}
                <div className="relative aspect-video w-full bg-black flex items-center justify-center overflow-hidden">
                  <VideoPlayer
                    cameraStatus={cam.status || 'CONNECTED'}
                    fps={Math.round(fpsVal)}
                    resolution={resVal}
                    source={cam.stream_url}
                    camId={cam.id}
                    camName={cam.name}
                  />

                  {/* Overlay en caso de desconexión total */}
                  {!isConnected && (
                    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-slate-950/90 backdrop-blur-xs p-6 text-center space-y-2">
                      <WifiOff size={28} className="text-rose-400 animate-pulse" />
                      <p className="text-xs sm:text-sm font-bold text-slate-200">
                        {cam.status?.toUpperCase() === 'CONNECTING' ? 'Conectando cámara…' : 'Cámara desconectada'}
                      </p>
                      <p className="text-[11px] text-slate-400 max-w-xs">
                        {cam.error || 'Verifica la conexión física del dispositivo o la red RTSP.'}
                      </p>
                    </div>
                  )}
                </div>

                {/* Pie de Recuadro: Métricas & Telemetría */}
                <div className="flex items-center justify-between px-3.5 py-2.5 bg-slate-950/60 border-t border-slate-800/60 text-xs text-slate-400">
                  <span className="font-mono text-[11px] flex items-center gap-1.5 text-slate-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    {fpsVal.toFixed(1)} FPS • {resVal.width}×{resVal.height}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    {isMain ? 'Flujo de Inferencia Activo' : 'Transmisión en Vivo'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ─── Leyenda y Ajustes de Inferencia (YOLOv8 & ROI) ───────────────── */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm overflow-hidden shadow-lg">
        <button
          onClick={() => setShowInferenceSettings(!showInferenceSettings)}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-800/40 transition-colors"
        >
          <div className="flex items-center gap-2.5">
            <Sliders size={16} className="text-indigo-400" />
            <h3 className="font-bold text-xs sm:text-sm text-slate-200 uppercase tracking-wider">
              Ajustes de Inferencia &amp; Zona de Interés (ROI)
            </h3>
            {roi && (
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-400 border border-amber-800">
                ROI Activo
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-slate-400 text-xs">
            <span>{showInferenceSettings ? 'Ocultar ajustes' : 'Configurar umbrales'}</span>
            {showInferenceSettings ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
        </button>

        {showInferenceSettings && (
          <div className="p-5 border-t border-slate-800/80 bg-slate-950/40 grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Umbrales */}
            <div className="space-y-4">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wide flex items-center gap-1.5">
                <Cpu size={14} className="text-cyan-400" />
                Parámetros de Detección YOLOv8
              </h4>

              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Confidence Threshold (Confianza mínima):</span>
                    <span className="font-mono text-cyan-400 font-bold">{confidence}</span>
                  </div>
                  <input 
                    type="range" 
                    min="0.05" 
                    max="0.95" 
                    step="0.05" 
                    value={confidence} 
                    onChange={(e) => setConfidence(parseFloat(e.target.value))} 
                    className="w-full accent-cyan-500 bg-slate-800 rounded-lg h-1.5 cursor-pointer" 
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">IoU Threshold (Supresión de no-máximos):</span>
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
                  className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold transition-all border border-slate-700 shadow-sm active:scale-95"
                >
                  Guardar Umbrales
                </button>
              </div>
            </div>

            {/* Zona de Interés (ROI) */}
            <div className="space-y-4">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wide flex items-center gap-1.5">
                <Crop size={14} className="text-amber-400" />
                Zona de Interés de la Góndola (ROI)
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Filtra las detecciones fuera del estante seleccionado para evitar falsos positivos por personas o tránsito en pasillos.
              </p>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <button 
                  onClick={() => handleSetRoi([0.1, 0.2, 0.9, 0.85])} 
                  className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-amber-500/50 text-slate-300 transition-all font-medium text-center hover:bg-slate-800"
                >
                  Estante Central
                </button>
                <button 
                  onClick={() => handleSetRoi([0.05, 0.1, 0.95, 0.5])} 
                  className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-amber-500/50 text-slate-300 transition-all font-medium text-center hover:bg-slate-800"
                >
                  Nivel Superior
                </button>
              </div>

              <button 
                onClick={() => handleSetRoi(null)} 
                className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-rose-400 hover:text-rose-300 rounded-xl text-xs font-semibold transition-all border border-slate-800"
              >
                Restablecer Vista Completa
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ─── Modal Añadir Cámara IP / RTSP / Simulador ──────────────────────── */}
      {showAddModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fadeIn"
          onClick={() => setShowAddModal(false)}
        >
          <div 
            className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Camera size={18} className="text-cyan-400" />
                <h3 className="font-bold text-base text-slate-100">
                  Añadir Cámara de Video
                </h3>
              </div>
              <button 
                onClick={() => setShowAddModal(false)} 
                className="text-slate-400 hover:text-slate-200 text-lg leading-none"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddManualCamera} className="space-y-4">
              <div>
                <label className="text-xs text-slate-300 font-semibold block mb-1">
                  Nombre descriptivo:
                </label>
                <input
                  type="text"
                  placeholder="ej. Cámara Pasillo Sur, Góndola Lácteos"
                  value={newCamName}
                  onChange={(e) => setNewCamName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 transition-colors"
                />
              </div>

              <div>
                <label className="text-xs text-slate-300 font-semibold block mb-1">
                  Tipo de Fuente:
                </label>
                <select
                  value={newCamSourceType}
                  onChange={(e) => setNewCamSourceType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 transition-colors"
                >
                  <option value="rtsp">Cámara IP de Red (Stream RTSP)</option>
                  <option value="synthetic">Simulador Sintético de Estantería</option>
                </select>
              </div>

              {newCamSourceType === 'rtsp' && (
                <div>
                  <label className="text-xs text-slate-300 font-semibold block mb-1">
                    URL RTSP del Stream:
                  </label>
                  <input
                    type="text"
                    placeholder="rtsp://usuario:clave@192.168.1.50:554/live"
                    value={newCamRtspUrl}
                    onChange={(e) => setNewCamRtspUrl(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500 transition-colors"
                    required
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    Las cámaras web USB se detectan automáticamente. Usa esta opción para cámaras IP de seguridad o vigilancia.
                  </p>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingAdd}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/20 transition-all active:scale-95 disabled:opacity-50"
                >
                  {isSubmittingAdd ? 'Conectando…' : 'Conectar e Inicializar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
