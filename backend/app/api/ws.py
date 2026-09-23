import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.core.logging import logger
from backend.app.services.detection_service import detection_service
from backend.app.services.alert_service import alert_service
from backend.app.api.system import get_system_metrics_dict

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """Canal WebSocket para telemetría en tiempo real a ~5-10Hz."""
    await websocket.accept()
    logger.info("Cliente WebSocket conectado a telemetría.")
    try:
        while True:
            det_result, metrics, inference_fps = detection_service.get_latest_result()
            cam_info = detection_service.camera.get_info()
            alert_st = alert_service.get_status(metrics.empty_rate)
            sys_metrics = get_system_metrics_dict()

            payload = {
                "timestamp": asyncio.get_event_loop().time(),
                "camera": {
                    "status": cam_info.get("status"),
                    "fps": cam_info.get("fps"),
                    "resolution": cam_info.get("resolution"),
                    "source": cam_info.get("source_display")
                },
                "model": {
                    "version": det_result.model_version,
                    "inference_fps": round(inference_fps, 1),
                    "confidence_threshold": detection_service.model_mgr.confidence_threshold,
                    "iou_threshold": detection_service.model_mgr.iou_threshold,
                    "timings": {
                        "preprocess_ms": det_result.timings.preprocess_ms,
                        "inference_ms": det_result.timings.inference_ms,
                        "postprocess_ms": det_result.timings.postprocess_ms,
                        "total_ms": det_result.timings.total_ms
                    }
                },
                "inventory": {
                    "products": metrics.products,
                    "missing": metrics.missing,
                    "total_spaces": metrics.total_spaces,
                    "occupancy_rate": metrics.occupancy_rate,
                    "empty_rate": metrics.empty_rate,
                    "roi_applied": metrics.roi_applied
                },
                "alert": {
                    "is_active": alert_st.is_active,
                    "consecutive_seconds_high": alert_st.consecutive_seconds_high,
                    "cooldown_remaining_seconds": alert_st.cooldown_remaining_seconds,
                    "empty_rate": alert_st.current_empty_rate,
                    "threshold": alert_st.threshold,
                    "last_alert": alert_st.last_alert.model_dump() if alert_st.last_alert else None
                },
                "system": sys_metrics
            }

            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.15)  # ~7 Hz

    except WebSocketDisconnect:
        logger.info("Cliente WebSocket desconectado.")
    except Exception as e:
        logger.warning(f"Error en WebSocket telemetría: {e}")
