import time
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from backend.app.services.camera_service import camera_service, camera_manager
from backend.app.services.detection_service import detection_service

router = APIRouter(prefix="/api/camera", tags=["Camera"])

@router.get("/list")
def list_cameras():
    """Devuelve todas las cámaras activas detectadas con sus URLs de stream y metadatos."""
    return camera_manager.list_cameras_info()

@router.post("/scan")
def scan_cameras():
    """Fuerza un re-escaneo de cámaras disponibles y devuelve la lista actualizada."""
    return camera_manager.scan_and_update()


class CameraControlRequest(BaseModel):
    action: str  # "start" or "stop"
    cam_id: Optional[str] = None

class CameraSourceRequest(BaseModel):
    source_type: str  # "webcam", "usb", "rtsp", "synthetic"
    webcam_index: Optional[int] = 0
    rtsp_url: Optional[str] = None
    name: Optional[str] = None

class CameraAddRequest(BaseModel):
    name: Optional[str] = None
    source_type: str = "rtsp"  # "rtsp", "webcam", "synthetic"
    webcam_index: Optional[int] = None
    rtsp_url: Optional[str] = None


@router.get("/status")
def get_camera_status():
    return camera_service.get_info() if camera_service else {}

@router.post("/control")
def control_camera(req: CameraControlRequest):
    target_id = req.cam_id or "main"
    cam = camera_manager.get_camera(target_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Cámara '{target_id}' no encontrada.")

    if req.action == "start":
        cam.start()
        if target_id == "main" and not detection_service._running:
            detection_service.start()
        return {"message": f"Cámara '{target_id}' iniciada", "status": cam.status}
    elif req.action == "stop":
        cam.stop()
        return {"message": f"Cámara '{target_id}' detenida", "status": cam.status}
    raise HTTPException(status_code=400, detail="Acción inválida. Usa 'start' o 'stop'.")

@router.post("/source")
def change_camera_source(req: CameraSourceRequest):
    if req.source_type not in ["webcam", "usb", "rtsp", "synthetic"]:
        raise HTTPException(status_code=400, detail="Tipo de fuente inválido.")
    
    if camera_service:
        camera_service.change_source(
            source_type=req.source_type,
            webcam_index=req.webcam_index,
            rtsp_url=req.rtsp_url
        )
        if req.name:
            camera_service.name = req.name
        return {
            "message": f"Fuente de cámara principal cambiada a '{req.source_type}'",
            "info": camera_service.get_info()
        }
    raise HTTPException(status_code=404, detail="Cámara principal no disponible.")

@router.post("/source/{cam_id}")
def change_camera_source_id(cam_id: str, req: CameraSourceRequest):
    if req.source_type not in ["webcam", "usb", "rtsp", "synthetic"]:
        raise HTTPException(status_code=400, detail="Tipo de fuente inválido.")
    
    camera_manager.add_camera(
        cam_id=cam_id,
        source_type=req.source_type,
        webcam_index=req.webcam_index,
        rtsp_url=req.rtsp_url,
        name=req.name,
        auto_start=True
    )
    cam = camera_manager.get_camera(cam_id)
    return {
        "message": f"Fuente de cámara '{cam_id}' configurada.",
        "info": cam.get_info() if cam else {}
    }

@router.post("/add")
def add_new_camera(req: CameraAddRequest):
    """Permite añadir cámaras de forma manual (ej. RTSP o Simulador) con ID único."""
    if req.source_type not in ["webcam", "usb", "rtsp", "synthetic"]:
        raise HTTPException(status_code=400, detail="Tipo de fuente inválido.")

    if req.source_type in ["webcam", "usb"] and req.webcam_index is not None:
        if req.webcam_index in camera_manager._index_to_id:
            existing_id = camera_manager._index_to_id[req.webcam_index]
            raise HTTPException(
                status_code=400,
                detail=f"El índice de cámara {req.webcam_index} ya está en uso por '{existing_id}'."
            )

    used_ids = set(camera_manager.get_all().keys())
    idx = len(used_ids) + 1
    cam_id = f"cam-{idx}"
    while cam_id in used_ids:
        idx += 1
        cam_id = f"cam-{idx}"

    name = req.name or (f"Cámara IP {idx}" if req.source_type == "rtsp" else f"Cámara {idx}")
    cam = camera_manager.add_camera(
        cam_id=cam_id,
        source_type=req.source_type,
        webcam_index=req.webcam_index,
        rtsp_url=req.rtsp_url,
        name=name,
        auto_start=True
    )
    return {
        "message": f"Cámara '{cam_id}' agregada correctamente.",
        "camera": {
            "id": cam_id,
            "stream_url": f"/api/camera/stream/{cam_id}",
            "is_main": False,
            **cam.get_info()
        }
    }

@router.delete("/{cam_id}")
def delete_camera(cam_id: str):
    """Elimina una cámara no principal y libera sus recursos."""
    if cam_id == "main":
        raise HTTPException(status_code=400, detail="No se puede eliminar la cámara principal 'main'.")
    success = camera_manager.remove_camera(cam_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Cámara '{cam_id}' no encontrada.")
    return {"message": f"Cámara '{cam_id}' eliminada exitosamente."}


_disconnected_frames = {}

def _get_placeholder_jpeg(cam_id: str, label: str) -> bytes:
    if cam_id not in _disconnected_frames:
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        img[:] = (18, 22, 30)
        cv2.rectangle(img, (40, 40), (1240, 680), (35, 42, 55), 2)
        cv2.putText(img, "CAMARA SIN SENAL O CONECTANDO...", (330, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 100, 220), 2)
        cv2.putText(img, label, (330, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (160, 170, 180), 1)
        _, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        _disconnected_frames[cam_id] = buf.tobytes()
    return _disconnected_frames[cam_id]


def _mjpeg_generator(cam_id: str):
    """Generador MJPEG continuo para streaming HTTP de video independiente por cámara."""
    while True:
        frame_bytes = detection_service.get_latest_annotated_jpeg(cam_id)
        if frame_bytes is None:
            cam = camera_manager.get_camera(cam_id)
            if cam:
                frame_bytes = _get_placeholder_jpeg(cam_id, cam.name)
            else:
                time.sleep(0.1)
                continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )
        time.sleep(0.033)  # ~30 FPS


@router.get("/stream")
def video_feed_default():
    """Stream MJPEG por defecto para compatibilidad histórica con 'main'."""
    return StreamingResponse(
        _mjpeg_generator("main"),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/stream/{cam_id}")
def video_feed(cam_id: str):
    """Stream de video MJPEG individual e independiente para la cámara solicitada."""
    return StreamingResponse(
        _mjpeg_generator(cam_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
