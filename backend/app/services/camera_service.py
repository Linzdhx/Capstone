import time
import threading
import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any

from backend.app.core.logging import logger
from backend.app.core.config import settings

class CameraService:
    """Servicio de captura de cámara multi-fuente con hilo dedicado y reconexión automática."""

    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

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

camera_service = CameraService()
