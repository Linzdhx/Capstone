from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.app.services.alert_service import alert_service
from backend.app.services.detection_service import detection_service
from backend.app.schemas.alert import AlertStatus, AlertEvent

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

class AlertConfigUpdate(BaseModel):
    empty_threshold: Optional[float] = None
    consecutive_seconds: Optional[float] = None
    cooldown_seconds: Optional[float] = None

@router.get("/status", response_model=AlertStatus)
def get_alert_status():
    _, metrics, _ = detection_service.get_latest_result()
    return alert_service.get_status(metrics.empty_rate)

@router.get("/history", response_model=List[AlertEvent])
def get_alert_history(limit: int = 50):
    return alert_service.get_history(limit=limit)

@router.get("/snapshots/{filename}")
def get_alert_snapshot(filename: str):
    file_path = alert_service.images_dir / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Snapshot no encontrado")
    return FileResponse(file_path, media_type="image/jpeg")

@router.post("/config")
def update_alert_config(cfg: AlertConfigUpdate):
    alert_service.update_config(
        empty_threshold=cfg.empty_threshold,
        consecutive_seconds=cfg.consecutive_seconds,
        cooldown_seconds=cfg.cooldown_seconds
    )
    return {
        "message": "Configuración de alertas actualizada",
        "empty_threshold": alert_service.empty_threshold,
        "consecutive_seconds": alert_service.consecutive_seconds,
        "cooldown_seconds": alert_service.cooldown_seconds
    }
