from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.app.services.dataset_service import dataset_service
from backend.app.services.detection_service import detection_service
from backend.app.schemas.dataset import DatasetItem, ReviewAction

router = APIRouter(prefix="/api/dataset", tags=["Dataset"])

@router.get("/stats")
def get_dataset_stats():
    return dataset_service.get_stats()

@router.get("/samples", response_model=List[DatasetItem])
def list_samples(stage: str = "pending_review"):
    if stage not in ["collected", "pending_review", "approved", "rejected", "validation"]:
        raise HTTPException(status_code=400, detail="Stage inválido")
    return dataset_service.list_samples(stage=stage)

@router.get("/images/{stage}/{filename}")
def get_dataset_image(stage: str, filename: str):
    stage_dir = dataset_service._get_stage_dir(stage)
    file_path = stage_dir / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Imagen de dataset no encontrada")
    return FileResponse(file_path, media_type="image/jpeg")

@router.post("/capture")
@router.post("/capture/{cam_id}")
def manual_capture(cam_id: Optional[str] = None):
    target_id = cam_id or "main"
    cam = detection_service.camera_mgr.get_camera(target_id)
    if not cam:
        target_id = "main"
        cam = detection_service.camera_mgr.get_camera("main")

    frame = cam.get_latest_frame() if cam else None
    if frame is None:
        raise HTTPException(status_code=503, detail=f"No hay frames disponibles de la cámara '{target_id}'")

    det_result, metrics, _ = detection_service.get_latest_result(target_id)
    if not det_result.detections:
        try:
            h, w = frame.shape[:2]
            det_result = detection_service.model_mgr.predict(frame)
            metrics = detection_service.inventory.calculate_metrics(det_result.detections, w, h)
        except Exception:
            pass

    cam_name = cam.name if cam else target_id
    item = dataset_service.capture_sample(
        frame=frame,
        det_result=det_result,
        empty_rate=metrics.empty_rate,
        reason=f"manual_capture_{target_id}",
        source=f"{cam_name} ({target_id})",
        stage="pending_review"
    )
    return {"message": f"Muestra capturada para revisión desde {cam_name}", "sample": item}

@router.post("/review/{stage}/{sample_id}")
def review_sample(stage: str, sample_id: str, action: ReviewAction):
    sample = dataset_service.get_sample(stage, sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Muestra no encontrada")

    if action.action == "approve":
        if action.annotations is not None:
            dataset_service.update_annotations(stage, sample_id, action.annotations)
        ok = dataset_service.transition_sample(sample_id, from_stage=stage, to_stage="approved")
        return {"message": "Muestra aprobada para entrenamiento", "success": ok}

    elif action.action == "reject":
        ok = dataset_service.transition_sample(sample_id, from_stage=stage, to_stage="rejected")
        return {"message": "Muestra rechazada", "success": ok}

    elif action.action == "update_labels":
        if action.annotations is None:
            raise HTTPException(status_code=400, detail="Se requiere lista de anotaciones")
        updated = dataset_service.update_annotations(stage, sample_id, action.annotations)
        return {"message": "Anotaciones actualizadas", "sample": updated}

    raise HTTPException(status_code=400, detail="Acción de revisión desconocida")
