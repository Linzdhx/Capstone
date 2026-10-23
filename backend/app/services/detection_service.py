import time
import threading
from typing import Optional, Dict, Any, Tuple
import cv2
import numpy as np

from backend.app.core.logging import logger
from backend.app.services.camera_service import camera_manager
from backend.app.ml.model_manager import ModelManager
from backend.app.services.inventory_service import inventory_service, InventoryService
from backend.app.services.alert_service import alert_service, AlertService
from backend.app.schemas.detection import DetectionResult, DetectionItem
from backend.app.schemas.inventory import InventoryMetrics
# Import lazy para evitar importación circular; se resuelve al primer uso
_incident_service = None

def _get_incident_service():
    global _incident_service
    if _incident_service is None:
        from backend.app.services.incident_service import incident_service as _svc
        _incident_service = _svc
    return _incident_service

class DetectionService:
    """Orquestador de inferencia continua, dibujo de bounding boxes y puente entre cámara, inventario y alertas."""

    def __init__(
        self,
        camera_mgr=None,
        model_mgr: Optional[ModelManager] = None,
        inv_service: Optional[InventoryService] = None,
        alt_service: Optional[AlertService] = None
    ):
        self.camera_mgr = camera_mgr or camera_manager
        self.model_mgr = model_mgr or ModelManager()
        self.inventory = inv_service or inventory_service
        self.alerts = alt_service or alert_service

        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._latest_detections: Dict[str, DetectionResult] = {}
        self._latest_metrics: Dict[str, InventoryMetrics] = {}
        self._latest_annotated_frame: Dict[str, Optional[np.ndarray]] = {}
        self._fps: Dict[str, float] = {}
        self._fps_counter: Dict[str, int] = {}
        self._fps_timer: Dict[str, float] = {}

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
            for cam in self.camera_mgr.get_all().values():
                if not cam.is_running:
                    cam.start()
            self._thread = threading.Thread(target=self._detection_loop, daemon=True)
            self._thread.start()
            logger.info("DetectionService iniciado (Modo Multi-Cámara).")

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("DetectionService detenido.")

    def get_latest_result(self, cam_id: str = "main") -> Tuple[DetectionResult, InventoryMetrics, float]:
        with self._lock:
            return (
                self._latest_detections.get(cam_id, DetectionResult()),
                self._latest_metrics.get(cam_id, InventoryMetrics()),
                self._fps.get(cam_id, 0.0)
            )

    def get_latest_annotated_jpeg(self, cam_id: str = "main") -> Optional[bytes]:
        with self._lock:
            frame = self._latest_annotated_frame.get(cam_id)
            if frame is None:
                cam = self.camera_mgr.get_camera(cam_id)
                if cam:
                    raw = cam.get_latest_frame()
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
        metrics: InventoryMetrics,
        fps: float
    ) -> np.ndarray:
        annotated = frame.copy()
        h, w = annotated.shape[:2]

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

        target_dets = detection_result.detections
        if self.inventory.roi:
            target_dets = self.inventory.filter_by_roi(target_dets, w, h)

        for det in target_dets:
            x1, y1, x2, y2 = [int(v) for v in det.box]
            cls_name = det.class_name.lower()
            color = self.colors.get(cls_name, (200, 200, 200))

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

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

        cv2.rectangle(annotated, (0, 0), (w, 42), (20, 24, 30), -1)
        cv2.line(annotated, (0, 42), (w, 42), (50, 60, 75), 1)

        hud_text = (
            f"MODEL: {detection_result.model_version} | "
            f"FPS: {round(fps, 1)} | "
            f"PROD: {metrics.products} | "
            f"MISSING: {metrics.missing} | "
            f"EMPTY: {round(metrics.empty_rate * 100, 1)}% | "
            f"LATENCY: {round(detection_result.timings.total_ms, 1)}ms"
        )
        
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
        while self._running:
            cameras_to_process = list(self.camera_mgr.get_all().items())
            if not cameras_to_process:
                time.sleep(0.05)
                continue
                
            for cam_id, cam in cameras_to_process:
                if not self._running: break
                frame = cam.get_latest_frame()
                if frame is None:
                    continue

                h, w = frame.shape[:2]

                try:
                    det_result = self.model_mgr.predict(frame)
                    metrics = self.inventory.calculate_metrics(det_result.detections, w, h)
                    
                    if cam_id == "main":
                        self.alerts.evaluate(metrics, frame, len(det_result.detections))
                        try:
                            _get_incident_service().process_frame(
                                detections=det_result.detections,
                                frame=frame,
                                location_id="GND-001"
                            )
                        except Exception as inc_err:
                            logger.debug(f"IncidentService: {inc_err}")

                    if cam_id not in self._fps_timer:
                        self._fps_timer[cam_id] = time.time()
                        self._fps_counter[cam_id] = 0
                        self._fps[cam_id] = 0.0

                    self._fps_counter[cam_id] += 1
                    now = time.time()
                    dt = now - self._fps_timer[cam_id]
                    if dt >= 1.0:
                        self._fps[cam_id] = self._fps_counter[cam_id] / dt
                        self._fps_counter[cam_id] = 0
                        self._fps_timer[cam_id] = now
                    
                    fps_val = self._fps[cam_id]
                    annotated = self._draw_annotations(frame, det_result, metrics, fps_val)

                    with self._lock:
                        self._latest_detections[cam_id] = det_result
                        self._latest_metrics[cam_id] = metrics
                        self._latest_annotated_frame[cam_id] = annotated

                except Exception as e:
                    logger.error(f"Error en bucle de detección ({cam_id}): {e}")
                    time.sleep(0.01)

            time.sleep(0.005)

detection_service = DetectionService()
