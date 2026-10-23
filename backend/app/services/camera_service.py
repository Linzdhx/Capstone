import time
import threading
import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any

from backend.app.core.logging import logger
from backend.app.core.config import settings

class CameraService:
    """Servicio de captura de cámara multi-fuente con hilo dedicado y reconexión automática."""

    def __init__(self, name: str = "Cámara"):
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self.name: str = name
        self.source_type: str = settings.camera.source_type
        self.webcam_index: int = settings.camera.webcam_index
        self.rtsp_url: str = settings.camera.rtsp_url
        self.reconnect_delay: float = settings.camera.reconnect_delay_seconds

        self._latest_frame: Optional[np.ndarray] = None
        self._latest_frame_time: float = 0.0
        self._frame_count: int = 0
        self._fps: float = 0.0
        self._fps_timer: float = time.time()
        self._status: str = "DISCONNECTED"
        self._error_message: Optional[str] = None
        self._resolution: Tuple[int, int] = (0, 0)
        self._synthetic_counter: int = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def status(self) -> str:
        return self._status

    def get_info(self) -> Dict[str, Any]:
        with self._lock:
            # Para RTSP, enmascaramos credenciales para no exponer contraseñas
            safe_source = self.source_type
            if self.source_type == "webcam" or self.source_type == "usb":
                safe_source = f"{self.source_type} (index: {self.webcam_index})"
            elif self.source_type == "rtsp":
                safe_source = "rtsp://***:***" if self.rtsp_url else "rtsp (no configurado)"

            return {
                "name": self.name,
                "status": self._status,
                "source_type": self.source_type,
                "source_display": safe_source,
                "fps": round(self._fps, 1),
                "resolution": {
                    "width": self._resolution[0],
                    "height": self._resolution[1]
                },
                "error": self._error_message
            }

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._status = "CONNECTING"
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            logger.info("CameraService iniciado.")

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._status = "DISCONNECTED"
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("CameraService detenido.")

    def change_source(self, source_type: str, webcam_index: Optional[int] = None, rtsp_url: Optional[str] = None) -> None:
        was_running = self._running
        if was_running:
            self.stop()

        with self._lock:
            self.source_type = source_type
            if webcam_index is not None:
                self.webcam_index = webcam_index
            if rtsp_url is not None:
                self.rtsp_url = rtsp_url

        if was_running:
            self.start()

    def get_latest_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def _generate_synthetic_shelf_frame(self) -> np.ndarray:
        """Genera un fotograma sintético realista simulando un estante con ganchos, productos y faltantes."""
        self._synthetic_counter += 1
        width, height = 1280, 720
        frame = np.full((height, width, 3), (235, 235, 235), dtype=np.uint8)

        # Fondo con textura de góndola / estantería
        cv2.rectangle(frame, (80, 100), (1200, 620), (190, 195, 200), -1)
        cv2.rectangle(frame, (80, 100), (1200, 620), (130, 135, 140), 3)

        # Barras metálicas horizontales del estante
        for y_bar in [250, 450]:
            cv2.line(frame, (100, y_bar), (1180, y_bar), (100, 100, 105), 6)
            cv2.line(frame, (100, y_bar - 2), (1180, y_bar - 2), (160, 160, 165), 2)

        # Dibujar ganchos y productos / faltantes oscilantes
        cols = 6
        step_x = (1180 - 140) // cols
        
        # Simular variación periódica para ver cambios en vivo
        phase = (self._synthetic_counter // 60) % 4

        for row_idx, y_center in enumerate([250, 450]):
            for c in range(cols):
                cx = 160 + c * step_x
                # Gancho metálico
                cv2.circle(frame, (cx, y_center - 15), 6, (80, 80, 85), -1)
                cv2.line(frame, (cx, y_center - 15), (cx, y_center + 10), (80, 80, 85), 3)

                # Decidir si es producto o missing según posición y fase
                is_missing = ((c + row_idx + phase) % 3 == 0)
                
                if is_missing:
                    # Zona vacía (etiqueta de gancho sin producto)
                    cv2.rectangle(frame, (cx - 35, y_center + 15), (cx + 35, y_center + 85), (170, 175, 180), 2)
                    cv2.putText(frame, "EMPTY", (cx - 28, y_center + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 100, 100), 1)
                else:
                    # Paquete de producto en gancho (ej. bolsita de snacks o golosinas)
                    cv2.rectangle(frame, (cx - 40, y_center + 15), (cx + 40, y_center + 120), (50, 140, 220), -1)
                    cv2.rectangle(frame, (cx - 40, y_center + 15), (cx + 40, y_center + 120), (30, 90, 160), 2)
                    # Agujero de gancho en el producto
                    cv2.circle(frame, (cx, y_center + 25), 4, (240, 240, 240), -1)
                    # Detalle gráfico de marca
                    cv2.putText(frame, "ITEM", (cx - 22, y_center + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Marca de agua de origen sintético
        cv2.putText(frame, "CAM: SYNTHETIC SHELF SIMULATOR", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 2)
        return frame

    def _capture_loop(self) -> None:
        """Bucle continuo de adquisición de frames con tolerancia a fallos."""
        while self._running:
            cap = None
            try:
                if self.source_type == "synthetic":
                    with self._lock:
                        self._status = "CONNECTED"
                        self._resolution = (1280, 720)
                        self._error_message = None

                    while self._running and self.source_type == "synthetic":
                        frame = self._generate_synthetic_shelf_frame()
                        self._update_frame(frame)
                        time.sleep(1.0 / max(1, settings.camera.target_fps))
                    continue

                # Fuente real: Webcam / USB / RTSP
                source: Any = self.webcam_index if self.source_type in ["webcam", "usb"] else self.rtsp_url
                logger.info(f"Intentando abrir fuente de cámara '{self.source_type}': {source}")

                with self._lock:
                    self._status = "CONNECTING"

                # En Windows, usar cv2.CAP_DSHOW suele mejorar la apertura de webcams USB
                backend_flag = cv2.CAP_DSHOW if isinstance(source, int) else cv2.CAP_FFMPEG
                cap = cv2.VideoCapture(source, backend_flag)
                
                # Configurar resolución recomendada
                if isinstance(source, int):
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.camera.width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.camera.height)

                if not cap.isOpened():
                    raise ConnectionError(f"No se pudo abrir la cámara {source}")

                # Primer frame exitoso
                ret, frame = cap.read()
                if not ret or frame is None:
                    raise ConnectionError("No se pudieron leer frames de la fuente de video")

                with self._lock:
                    self._status = "CONNECTED"
                    self._error_message = None
                    h, w = frame.shape[:2]
                    self._resolution = (w, h)
                logger.info(f"Cámara conectada exitosamente. Resolución: {w}x{h}")

                # Bucle de lectura
                while self._running:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        logger.warning("Fallo en lectura de frame de cámara.")
                        break

                    self._update_frame(frame)
                    # Control de tasa de captura
                    time.sleep(0.001)

            except Exception as e:
                err = str(e)
                logger.warning(f"Error en CameraService ({self.source_type}): {err}. Fallback a modo sintético o reintento...")
                with self._lock:
                    self._status = "DISCONNECTED"
                    self._error_message = err

                # Si falló una webcam no conectada físicamente, cambiar temporalmente a synthetic para no detener la app
                if self.source_type in ["webcam", "usb"] and ("No se pudo abrir" in err or "leer frames" in err):
                    logger.info("Cámara física no encontrada. Activando simulador de estantería para desarrollo continuo.")
                    with self._lock:
                        self.source_type = "synthetic"
                    continue

                # Esperar delay antes de reintentar
                time.sleep(self.reconnect_delay)
            finally:
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass

    def _update_frame(self, frame: np.ndarray) -> None:
        with self._lock:
            self._latest_frame = frame
            self._latest_frame_time = time.time()
            self._frame_count += 1
            now = time.time()
            dt = now - self._fps_timer
            if dt >= 1.0:
                self._fps = self._frame_count / dt
                self._frame_count = 0
                self._fps_timer = now

def _detect_physical_cameras(max_index: int = 4) -> list:
    """
    Escanea los índices 0..max_index y devuelve la lista de índices que tienen
    una cámara física conectada. Usa CAP_DSHOW en Windows para evitar demoras.
    SOLO llamar al inicio, cuando ningún CameraService está activo aún.
    """
    found = []
    for idx in range(max_index):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                found.append(idx)
        cap.release()
        time.sleep(0.05)  # pequeña pausa entre pruebas
    return found


def _detect_new_camera_indices(skip_indices: set, max_index: int = 4) -> list:
    """
    Escanea SOLO los índices que NO están en skip_indices.
    Esto es crítico: no intentar abrir cámaras que ya están siendo
    usadas por un CameraService activo (causaría conflicto DSHOW en Windows).
    """
    found = []
    for idx in range(max_index):
        if idx in skip_indices:
            continue  # Ya está registrado y activo — nunca tocarlo
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                found.append(idx)
        cap.release()
        time.sleep(0.05)
    return found


def get_windows_camera_devices() -> list:
    """Obtiene la lista de nombres de cámaras físicas desde el registro de Windows."""
    names = []
    try:
        import winreg
        base = r'SYSTEM\CurrentControlSet\Control\DeviceClasses\{65e8773d-8f56-11d0-a3b9-00a0c9223196}'
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base)
        for i in range(winreg.QueryInfoKey(k)[0]):
            sub = winreg.EnumKey(k, i)
            if 'USB#VID' not in sub:
                continue
            try:
                sk = winreg.OpenKey(k, sub + r'\#GLOBAL\Device Parameters')
                fname, _ = winreg.QueryValueEx(sk, 'FriendlyName')
                if fname not in names and 'controller' not in fname.lower():
                    names.append(fname)
            except Exception:
                pass
    except Exception:
        pass
    return names


def _resolve_friendly_name(index: int, default_id: str) -> str:
    """Devuelve un nombre amigable e identificable para la cámara física."""
    devices = get_windows_camera_devices()
    if index == 0:
        integrated = [d for d in devices if any(k in d.lower() for k in ["truevision", "integrated", "builtin", "front", "internal"])]
        if integrated:
            return integrated[0]
        if devices:
            return devices[-1] if len(devices) > 1 else devices[0]
        return "Cámara Principal (Webcam)"
    elif index == 1:
        external = [d for d in devices if not any(k in d.lower() for k in ["truevision", "integrated", "builtin", "internal"])]
        if external:
            return external[0]
        if len(devices) > 1:
            return devices[0]
        return "Cámara Secundaria (USB)"
    else:
        return f"Cámara USB #{index}"


_CAM_ID_MAP = ["main", "cam-2", "cam-3", "cam-4"]


class CameraManager:
    def __init__(self):
        self.cameras: Dict[str, CameraService] = {}
        self._lock = threading.Lock()
        self._hotplug_thread: Optional[threading.Thread] = None
        self._hotplug_running = False
        # Mapa índice físico → cam_id para evitar duplicados
        self._index_to_id: Dict[int, str] = {}
        self._auto_detect_and_register()

    def _auto_detect_and_register(self):
        """Detecta cámaras físicas disponibles al arranque y las registra."""
        source_type = settings.camera.source_type

        if source_type == "synthetic":
            self.add_camera("main", "synthetic", name="Simulador Sintético", auto_start=False)
            logger.info("CameraManager: modo sintético registrado como 'main'.")
            return

        if source_type == "rtsp":
            self.add_camera("main", "rtsp", rtsp_url=settings.camera.rtsp_url, name="Cámara IP (RTSP)", auto_start=False)
            logger.info("CameraManager: cámara RTSP registrada como 'main'.")
            return

        # Modo webcam/usb: detectar todas las físicas disponibles
        logger.info("CameraManager: escaneando cámaras físicas disponibles...")
        found_indices = _detect_physical_cameras(max_index=4)

        if not found_indices:
            logger.warning("CameraManager: no se detectaron cámaras físicas. Activando modo sintético.")
            self.add_camera("main", "synthetic", name="Simulador Sintético", auto_start=False)
            return

        for i, cam_index in enumerate(found_indices):
            cam_id = _CAM_ID_MAP[i] if i < len(_CAM_ID_MAP) else f"cam-{i+1}"
            name = _resolve_friendly_name(cam_index, cam_id)
            self._index_to_id[cam_index] = cam_id
            self.add_camera(cam_id, source_type, webcam_index=cam_index, name=name, auto_start=False)
            logger.info(f"CameraManager: cámara física index={cam_index} ('{name}') registrada como '{cam_id}'.")

        # Arrancar el hotplug loop para detectar cámaras nuevas en caliente
        self._start_hotplug()

    def _start_hotplug(self):
        """Inicia el hilo de detección dinámica de nuevas cámaras."""
        if self._hotplug_running:
            return
        self._hotplug_running = True
        self._hotplug_thread = threading.Thread(
            target=self._hotplug_loop, daemon=True, name="camera-hotplug"
        )
        self._hotplug_thread.start()
        logger.info("CameraManager: hilo de hotplug iniciado.")

    def scan_and_update(self) -> list:
        """
        Fuerza un escaneo seguro de índices libres y auto-registra cámaras nuevas.
        Seguro en Windows DSHOW: nunca toca índices ya en uso.
        """
        source_type = settings.camera.source_type
        if source_type in ("webcam", "usb"):
            with self._lock:
                occupied_indices = set(self._index_to_id.keys())

            new_found = _detect_new_camera_indices(skip_indices=occupied_indices, max_index=4)
            if new_found:
                for cam_index in sorted(new_found):
                    with self._lock:
                        if cam_index in self._index_to_id:
                            continue
                        used_ids = set(self._index_to_id.values())
                        cam_id = next(
                            (c for c in _CAM_ID_MAP if c not in used_ids),
                            f"cam-{cam_index+1}"
                        )
                        name = _resolve_friendly_name(cam_index, cam_id)
                        self._index_to_id[cam_index] = cam_id

                    self.add_camera(cam_id, source_type, webcam_index=cam_index, name=name, auto_start=True)
                    logger.info(f"CameraManager [hotplug]: nueva cámara index={cam_index} ('{name}') -> '{cam_id}'.")

        return self.list_cameras_info()

    def _hotplug_loop(self):
        """Bucle en segundo plano para detección periódica de dispositivos."""
        SCAN_INTERVAL = 8.0
        while self._hotplug_running:
            time.sleep(SCAN_INTERVAL)
            try:
                self.scan_and_update()
            except Exception as e:
                logger.warning(f"CameraManager [hotplug] error: {e}")

    def stop_hotplug(self):
        self._hotplug_running = False

    def add_camera(
        self,
        cam_id: str,
        source_type: str,
        webcam_index: Optional[int] = None,
        rtsp_url: Optional[str] = None,
        name: Optional[str] = None,
        auto_start: bool = True
    ) -> CameraService:
        with self._lock:
            if cam_id in self.cameras:
                self.cameras[cam_id].stop()

            cam_name = name or (
                _resolve_friendly_name(webcam_index, cam_id)
                if webcam_index is not None
                else ("Cámara IP (RTSP)" if source_type == "rtsp" else "Simulador Sintético")
            )
            cam = CameraService(name=cam_name)
            cam.change_source(source_type, webcam_index, rtsp_url)
            self.cameras[cam_id] = cam
            if webcam_index is not None:
                self._index_to_id[webcam_index] = cam_id

        if auto_start:
            cam.start()

        return cam

    def get_camera(self, cam_id: str) -> Optional[CameraService]:
        return self.cameras.get(cam_id)

    def remove_camera(self, cam_id: str) -> bool:
        if cam_id == "main":
            return False  # No permitir eliminar cámara principal
        with self._lock:
            if cam_id in self.cameras:
                self.cameras[cam_id].stop()
                del self.cameras[cam_id]
                for idx, cid in list(self._index_to_id.items()):
                    if cid == cam_id:
                        del self._index_to_id[idx]
                return True
        return False

    def get_all(self) -> Dict[str, CameraService]:
        return self.cameras

    def list_cameras_info(self) -> list:
        return [
            {
                "id": cam_id,
                "stream_url": f"/api/camera/stream/{cam_id}",
                "is_main": cam_id == "main",
                **cam.get_info()
            }
            for cam_id, cam in self.cameras.items()
        ]


camera_manager = CameraManager()
camera_service = camera_manager.get_camera("main")

