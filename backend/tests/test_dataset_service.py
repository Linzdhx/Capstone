import numpy as np
import pytest
from backend.app.services.dataset_service import DatasetService
from backend.app.schemas.detection import DetectionResult, DetectionItem

def test_dataset_capture_and_transition(tmp_path):
    """Verifica el ciclo de vida de una muestra: capture -> pending_review -> approve."""
    service = DatasetService()
    # Usar directorios temporales
    service.collected_dir = tmp_path / "collected"
    service.pending_dir = tmp_path / "pending_review"
    service.approved_dir = tmp_path / "approved"
    service.rejected_dir = tmp_path / "rejected"
    for d in [service.collected_dir, service.pending_dir, service.approved_dir, service.rejected_dir]:
        d.mkdir(parents=True, exist_ok=True)

    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    det_result = DetectionResult(
        detections=[
            DetectionItem(class_id=1, class_name="product", confidence=0.88, box=[50, 50, 150, 150])
        ],
        model_version="v001"
    )

    # Captura en pending_review
    sample = service.capture_sample(dummy_frame, det_result, empty_rate=0.0, stage="pending_review")
    assert sample.stage == "pending_review"
    
    # Listar en pending_review
    pending_items = service.list_samples("pending_review")
    assert any(i.id == sample.id for i in pending_items)

    # Transición a approved
    ok = service.transition_sample(sample.id, from_stage="pending_review", to_stage="approved")
    assert ok is True

    # Verificar que esté en approved
    approved_items = service.list_samples("approved")
    assert any(i.id == sample.id for i in approved_items)

    # Verificar que se haya generado el archivo .txt de etiqueta YOLO
    txt_files = list(service.approved_dir.glob("*.txt"))
    assert len(txt_files) > 0
    with open(txt_files[0], "r") as f:
        content = f.read()
        assert content.startswith("1 ")  # class_id 1
