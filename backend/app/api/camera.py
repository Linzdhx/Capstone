import time
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from backend.app.services.camera_service import camera_service
from backend.app.services.detection_service import detection_service

router = APIRouter(prefix="/api/camera", tags=["Camera"])

class CameraControlRequest(BaseModel):
    action: str  # "start" or "stop"

class CameraSourceRequest(BaseModel):
    source_type: str  # "webcam", "usb", "rtsp", "synthetic"
    webcam_index: Optional[int] = 0
    rtsp_url: Optional[str] = None

@router.get("/status")
def get_camera_status():
    return camera_service.get_info()

@router.post("/control")
def control_camera(req: CameraControlRequest):
    if req.action == "start":
        camera_service.start()
        detection_service.start()
        return {"message": "Cámara iniciada", "status": camera_service.status}
    elif req.action == "stop":
        camera_service.stop()
        detection_service.stop()
        return {"message": "Cámara detenida", "status": camera_service.status}
    raise HTTPException(status_code=400, detail="Acción inválida. Usa 'start' o 'stop'.")

@router.post("/source")
def change_camera_source(req: CameraSourceRequest):
    if req.source_type not in ["webcam", "usb", "rtsp", "synthetic"]:
        raise HTTPException(status_code=400, detail="Tipo de fuente inválido.")
    
    camera_service.change_source(
        source_type=req.source_type,
        webcam_index=req.webcam_index,
        rtsp_url=req.rtsp_url
    )
    return {
        "message": f"Fuente de cámara cambiada a '{req.source_type}'",
        "info": camera_service.get_info()
    }

def _mjpeg_generator():
    """Generador MJPEG continuo para streaming HTTP de video."""
    while True:
        frame_bytes = detection_service.get_latest_annotated_jpeg()
        if frame_bytes is None:
            time.sleep(0.04)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )
        time.sleep(0.033)  # ~30 FPS

@router.get("/stream")
def video_feed():
    """Stream de video MJPEG con bounding boxes en tiempo real."""
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
