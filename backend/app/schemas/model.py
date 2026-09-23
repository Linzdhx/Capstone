from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ModelMetrics(BaseModel):
    mAP50: Optional[float] = None
    mAP50_95: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None

class ModelVersionInfo(BaseModel):
    version: str
    name: str
    status: str  # "production", "candidate", "archive"
    classes: Dict[str, str]
    task: str = "detect"
    base_model: Optional[str] = None
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    metrics: Optional[Dict[str, Any]] = None
    created_at: str
    parent_model: Optional[str] = None
    path: str

class ModelThresholdUpdate(BaseModel):
    confidence: Optional[float] = Field(None, ge=0.01, le=1.0)
    iou: Optional[float] = Field(None, ge=0.01, le=1.0)

class HotSwapRequest(BaseModel):
    version: str = Field(..., description="ID de versión del modelo candidato a activar (ej: v002)")

class RollbackRequest(BaseModel):
    version: str = Field(..., description="ID de versión anterior a restaurar (ej: v001)")
