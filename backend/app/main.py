import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.logging import logger
from backend.app.core.config import BASE_DIR, settings
from backend.app.services.camera_service import camera_service
from backend.app.services.detection_service import detection_service
from backend.app.api.camera import router as camera_router
from backend.app.api.inventory import router as inventory_router
from backend.app.api.alerts import router as alerts_router
from backend.app.api.models import router as models_router
from backend.app.api.dataset import router as dataset_router
from backend.app.api.training import router as training_router
from backend.app.api.system import router as system_router
from backend.app.api.ws import router as ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Iniciar servicios de cámara y detección
    logger.info("Iniciando aplicación CVW Inventory Monitor...")
    camera_service.start()
    detection_service.start()
    yield
    # Shutdown: Detener servicios de forma limpia
    logger.info("Deteniendo servicios...")
    detection_service.stop()
    camera_service.stop()

app = FastAPI(
    title="CVW Inventory Monitor API",
    description="Sistema profesional de monitoreo de inventario con YOLOv8, Active Learning y Hot-Swap",
    version="1.0.0",
    lifespan=lifespan
)

# CORS para React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar Routers
app.include_router(camera_router)
app.include_router(inventory_router)
app.include_router(alerts_router)
app.include_router(models_router)
app.include_router(dataset_router)
app.include_router(training_router)
app.include_router(system_router)
app.include_router(ws_router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "camera_status": camera_service.status,
        "active_model": detection_service.model_mgr.active_version
    }

# Montar frontend estático si existe la build
frontend_dist = BASE_DIR / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

