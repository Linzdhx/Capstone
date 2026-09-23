from fastapi import APIRouter, HTTPException
from backend.app.services.training_worker import training_worker
from backend.app.schemas.dataset import TrainingRequest, TrainingStatus

router = APIRouter(prefix="/api/training", tags=["Training"])

@router.get("/status", response_model=TrainingStatus)
def get_training_status():
    return training_worker.get_status()

@router.post("/start")
def start_training(req: TrainingRequest):
    ok = training_worker.start_training(req)
    if not ok:
        status = training_worker.get_status()
        raise HTTPException(
            status_code=400,
            detail=status.error or status.message or "No se pudo iniciar el entrenamiento"
        )
    return {
        "message": "Entrenamiento iniciado en segundo plano",
        "status": training_worker.get_status()
    }
