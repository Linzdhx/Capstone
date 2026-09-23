from typing import Dict, List
from fastapi import APIRouter, HTTPException

from backend.app.services.detection_service import detection_service
from backend.app.schemas.model import (
    ModelVersionInfo,
    ModelThresholdUpdate,
    HotSwapRequest,
    RollbackRequest
)

router = APIRouter(prefix="/api/models", tags=["Models"])

@router.get("", response_model=Dict[str, List[ModelVersionInfo]])
def list_models():
    return detection_service.model_mgr.list_versions()

@router.get("/active", response_model=ModelVersionInfo)
def get_active_model():
    return detection_service.model_mgr.get_info()

@router.post("/thresholds")
def update_thresholds(req: ModelThresholdUpdate):
    updated = detection_service.model_mgr.update_thresholds(
        confidence=req.confidence,
        iou=req.iou
    )
    return {
        "message": "Umbrales actualizados exitosamente",
        "thresholds": updated
    }

@router.post("/hot-swap")
def hot_swap_model(req: HotSwapRequest):
    try:
        detection_service.model_mgr.hot_swap(req.version)
        return {
            "message": f"Hot-swap completado exitosamente a la versión '{req.version}'",
            "active_model": detection_service.model_mgr.get_info()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/rollback")
def rollback_model(req: RollbackRequest):
    try:
        detection_service.model_mgr.rollback(req.version)
        return {
            "message": f"Rollback completado exitosamente a la versión '{req.version}'",
            "active_model": detection_service.model_mgr.get_info()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
