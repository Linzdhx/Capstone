from fastapi import APIRouter
from backend.app.services.inventory_service import inventory_service
from backend.app.services.detection_service import detection_service
from backend.app.schemas.inventory import InventoryMetrics, ROISetting

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])

@router.get("/metrics", response_model=InventoryMetrics)
def get_inventory_metrics():
    _, metrics, _ = detection_service.get_latest_result()
    return metrics

@router.get("/roi")
def get_roi():
    return {"roi": inventory_service.roi}

@router.post("/roi")
def set_roi(setting: ROISetting):
    inventory_service.set_roi(setting.roi)
    return {
        "message": "ROI actualizado exitosamente",
        "roi": inventory_service.roi
    }
