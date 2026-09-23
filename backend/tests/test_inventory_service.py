import pytest
from backend.app.services.inventory_service import InventoryService
from backend.app.schemas.detection import DetectionItem

def test_inventory_zero_detections():
    """Verifica que con 0 detecciones no haya división por cero."""
    service = InventoryService()
    metrics = service.calculate_metrics([], frame_width=1280, frame_height=720)
    assert metrics.products == 0
    assert metrics.missing == 0
    assert metrics.total_spaces == 0
    assert metrics.occupancy_rate == 0.0
    assert metrics.empty_rate == 0.0

def test_inventory_mixed_detections():
    """Verifica el cálculo de occupancy_rate y empty_rate."""
    service = InventoryService()
    dets = [
        DetectionItem(class_id=1, class_name="product", confidence=0.9, box=[10, 10, 50, 50]),
        DetectionItem(class_id=1, class_name="product", confidence=0.85, box=[60, 10, 100, 50]),
        DetectionItem(class_id=1, class_name="product", confidence=0.92, box=[110, 10, 150, 50]),
        DetectionItem(class_id=0, class_name="missing", confidence=0.88, box=[160, 10, 200, 50]),
    ]
    metrics = service.calculate_metrics(dets, frame_width=1280, frame_height=720)
    assert metrics.products == 3
    assert metrics.missing == 1
    assert metrics.total_spaces == 4
    assert metrics.occupancy_rate == 0.75
    assert metrics.empty_rate == 0.25

def test_inventory_80_percent_empty():
    """Verifica cuando la tasa de faltantes es exactamente u 80% o superior."""
    service = InventoryService()
    dets = [
        DetectionItem(class_id=0, class_name="missing", confidence=0.9, box=[10, 10, 50, 50]),
        DetectionItem(class_id=0, class_name="missing", confidence=0.9, box=[60, 10, 100, 50]),
        DetectionItem(class_id=0, class_name="missing", confidence=0.9, box=[110, 10, 150, 50]),
        DetectionItem(class_id=0, class_name="missing", confidence=0.9, box=[160, 10, 200, 50]),
        DetectionItem(class_id=1, class_name="product", confidence=0.9, box=[210, 10, 250, 50]),
    ]
    metrics = service.calculate_metrics(dets, frame_width=1280, frame_height=720)
    assert metrics.products == 1
    assert metrics.missing == 4
    assert metrics.total_spaces == 5
    assert metrics.empty_rate == 0.80
    assert metrics.occupancy_rate == 0.20

def test_inventory_roi_filtering():
    """Verifica que el filtrado por ROI excluya elementos fuera del rectángulo."""
    service = InventoryService(roi=[0.0, 0.0, 0.5, 0.5])  # Cuadrante superior izquierdo
    dets = [
        # Centro en (50, 50) -> Dentro de 0..640 x 0..360
        DetectionItem(class_id=1, class_name="product", confidence=0.9, box=[0, 0, 100, 100]),
        # Centro en (900, 500) -> Fuera
        DetectionItem(class_id=0, class_name="missing", confidence=0.9, box=[850, 450, 950, 550]),
    ]
    metrics = service.calculate_metrics(dets, frame_width=1280, frame_height=720)
    assert metrics.roi_applied is True
    assert metrics.products == 1
    assert metrics.missing == 0
    assert metrics.total_spaces == 1
