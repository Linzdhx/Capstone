from typing import List, Optional, Tuple
from backend.app.schemas.detection import DetectionItem
from backend.app.schemas.inventory import InventoryMetrics

class InventoryService:
    """Servicio puro y aislado para cálculo de métricas de ocupación, vacíos y filtrado ROI."""

    def __init__(self, roi: Optional[List[float]] = None):
        # ROI normalizado [x1, y1, x2, y2] con valores entre 0.0 y 1.0
        self.roi = self._sanitize_roi(roi)

    def set_roi(self, roi: Optional[List[float]]) -> None:
        self.roi = self._sanitize_roi(roi)

    def _sanitize_roi(self, roi: Optional[List[float]]) -> Optional[List[float]]:
        if not roi or len(roi) != 4:
            return None
        x1, y1, x2, y2 = roi
        x1 = max(0.0, min(1.0, float(x1)))
        y1 = max(0.0, min(1.0, float(y1)))
        x2 = max(0.0, min(1.0, float(x2)))
        y2 = max(0.0, min(1.0, float(y2)))
        if x2 <= x1 or y2 <= y1:
            return None
        return [x1, y1, x2, y2]

    def filter_by_roi(
        self,
        detections: List[DetectionItem],
        frame_width: int,
        frame_height: int
    ) -> List[DetectionItem]:
        """Filtra detecciones cuyo centro geométrico cae dentro del ROI especificado."""
        if not self.roi or frame_width <= 0 or frame_height <= 0:
            return detections

        rx1 = self.roi[0] * frame_width
        ry1 = self.roi[1] * frame_height
        rx2 = self.roi[2] * frame_width
        ry2 = self.roi[3] * frame_height

        filtered: List[DetectionItem] = []
        for det in detections:
            x1, y1, x2, y2 = det.box
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0

            if rx1 <= cx <= rx2 and ry1 <= cy <= ry2:
                filtered.append(det)

        return filtered

    def calculate_metrics(
        self,
        detections: List[DetectionItem],
        frame_width: int = 0,
        frame_height: int = 0
    ) -> InventoryMetrics:
        """Calcula conteos y porcentajes de ocupación / vacío con protección de división por cero."""
        roi_applied = False
        target_dets = detections

        if self.roi and frame_width > 0 and frame_height > 0:
            target_dets = self.filter_by_roi(detections, frame_width, frame_height)
            roi_applied = True

        products = sum(1 for d in target_dets if d.class_name.lower() == "product")
        missing = sum(1 for d in target_dets if d.class_name.lower() == "missing")
        total_spaces = products + missing

        if total_spaces == 0:
            return InventoryMetrics(
                products=0,
                missing=0,
                total_spaces=0,
                occupancy_rate=0.0,
                empty_rate=0.0,
                roi_applied=roi_applied
            )

        empty_rate = round(missing / total_spaces, 4)
        occupancy_rate = round(products / total_spaces, 4)

        return InventoryMetrics(
            products=products,
            missing=missing,
            total_spaces=total_spaces,
            occupancy_rate=occupancy_rate,
            empty_rate=empty_rate,
            roi_applied=roi_applied
        )

inventory_service = InventoryService()
