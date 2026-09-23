import time
import threading
from typing import Optional, Dict, Any, Tuple
import cv2
import numpy as np

from backend.app.core.logging import logger
from backend.app.services.camera_service import camera_service, CameraService
from backend.app.ml.model_manager import ModelManager
from backend.app.services.inventory_service import inventory_service, InventoryService
from backend.app.services.alert_service import alert_service, AlertService
from backend.app.schemas.detection import DetectionResult, DetectionItem
from backend.app.schemas.inventory import InventoryMetrics

class DetectionService:
    """Orquestador de inferencia continua, dibujo de bounding boxes y puente entre cámara, inventario y alertas."""

    def __init__(
        self,
        camera: Optional[CameraService] = None,
        model_mgr: Optional[ModelManager] = None,
        inv_service: Optional[InventoryService] = None,
        alt_service: Optional[AlertService] = None
    ):
        self.camera = camera or camera_service
        self.model_mgr = model_mgr or ModelManager()
        self.inventory = inv_service or inventory_service
        self.alerts = alt_service or alert_service

        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._latest_detections: DetectionResult = DetectionResult()
        self._latest_metrics: InventoryMetrics = InventoryMetrics()
        self._latest_annotated_frame: Optional[np.ndarray] = None
        self._fps: float = 0.0
        self._fps_counter: int = 0
        self._fps_timer: float = time.time()

        # Paleta de colores visualmente atractiva (BGR)
        # Missing: Coral / Rojo suave (0, 70, 240)
        # Product: Verde esmeralda fresco (60, 200, 70)
        # ROI: Azul eléctrico (255, 180, 20)
        self.colors = {
            "missing": (30, 40, 235),
            "product": (50, 200, 60),
            "roi": (240, 160, 20),
            "text": (255, 255, 255)
        }

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            if not self.camera.is_running:
                self.camera.start()
            self._thread = threading.Thread(target=self._detection_loop, daemon=True)
            self._thread.start()
            logger.info("DetectionService iniciado.")

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("DetectionService detenido.")

    def get_latest_result(self) -> Tuple[DetectionResult, InventoryMetrics, float]:
        with self._lock:
            return self._latest_detections, self._latest_metrics, self._fps

    def get_latest_annotated_jpeg(self) -> Optional[bytes]:
        with self._lock:
            frame = self._latest_annotated_frame
            if frame is None:
                # Si no hay frame procesado aún, intentar del camera service
                raw = self.camera.get_latest_frame()
                if raw is not None:
                    _, buf = cv2.imencode(".jpg", raw, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    return buf.tobytes()
                return None
            _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            return buf.tobytes()

    def _draw_annotations(
        self,
        frame: np.ndarray,
        detection_result: DetectionResult,
        metrics: InventoryMetrics
    ) -> np.ndarray:
        """Dibuja bounding boxes estilizados, etiquetas y HUD con métricas."""
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # 1. Dibujar ROI si está configurado
        if self.inventory.roi:
            rx1 = int(self.inventory.roi[0] * w)
            ry1 = int(self.inventory.roi[1] * h)
            rx2 = int(self.inventory.roi[2] * w)
            ry2 = int(self.inventory.roi[3] * h)
            cv2.rectangle(annotated, (rx1, ry1), (rx2, ry2), self.colors["roi"], 2)
            cv2.putText(
                annotated,
                "ZONA DE INTERES (ROI)",
                (rx1 + 8, max(25, ry1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                self.colors["roi"],
                2
            )

        # 2. Dibujar bounding boxes de detecciones
        target_dets = detection_result.detections
        if self.inventory.roi:
            target_dets = self.inventory.filter_by_roi(target_dets, w, h)

        for det in target_dets:
            x1, y1, x2, y2 = [int(v) for v in det.box]
            cls_name = det.class_name.lower()
            color = self.colors.get(cls_name, (200, 200, 200))

            # Rectángulo exterior
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Etiqueta con fondo semitransparente
            label = f"{det.class_name.upper()} {int(det.confidence * 100)}%"
            (lw, lh), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            y_label_top = max(0, y1 - lh - 8)
            cv2.rectangle(annotated, (x1, y_label_top), (x1 + lw + 8, y_label_top + lh + 6), color, -1)
            cv2.putText(
                annotated,
                label,
                (x1 + 4, y_label_top + lh + 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        # 3. HUD superior estilizado
        # Fondo oscuro sutil para el HUD
        cv2.rectangle(annotated, (0, 0), (w, 42), (20, 24, 30), -1)
        cv2.line(annotated, (0, 42), (w, 42), (50, 60, 75), 1)

        hud_text = (
            f"MODEL: {detection_result.model_version} | "
            f"FPS: {round(self._fps, 1)} | "
            f"PROD: {metrics.products} | "
            f"MISSING: {metrics.missing} | "
            f"EMPTY: {round(metrics.empty_rate * 100, 1)}% | "
            f"LATENCY: {round(detection_result.timings.total_ms, 1)}ms"
        )
        
        # Color del texto de estado en HUD si hay alerta
        status_color = (60, 60, 240) if metrics.empty_rate >= 0.80 and metrics.total_spaces > 0 else (220, 220, 220)
        cv2.putText(
            annotated,
            hud_text,
            (16, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            status_color,
            2,
            cv2.LINE_AA
        )

        return annotated

    def _detection_loop(self) -> None:
        """Bucle principal de inferencia periódica."""
        while self._running:
            frame = self.camera.get_latest_frame()
            if frame is None:
                time.sleep(0.03)
                continue

            h, w = frame.shape[:2]

            try:
                # 1. Inferencia con ModelManager
                det_result = self.model_mgr.predict(frame)

                # 2. Análisis de métricas con InventoryService
                metrics = self.inventory.calculate_metrics(det_result.detections, w, h)

                # 3. Evaluación de Alertas
                self.alerts.evaluate(metrics, frame, len(det_result.detections))

                # 4. Renderizado visual
                annotated = self._draw_annotations(frame, det_result, metrics)

                # 5. Cálculo de FPS de inferencia
                self._fps_counter += 1
                now = time.time()
                dt = now - self._fps_timer
                if dt >= 1.0:
                    self._fps = self._fps_counter / dt
                    self._fps_counter = 0
                    self._fps_timer = now

                with self._lock:
                    self._latest_detections = det_result
                    self._latest_metrics = metrics
                    self._latest_annotated_frame = annotated

            except Exception as e:
                logger.error(f"Error en bucle de detección: {e}")
                time.sleep(0.05)

            # Pequeña pausa para no saturar CPU cuando la cámara no entrega nuevo frame
            time.sleep(0.005)

detection_service = DetectionService()
