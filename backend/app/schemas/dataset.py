from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class BBoxAnnotation(BaseModel):
    id: Optional[str] = None
    class_id: int
    class_name: str
    confidence: float = 1.0
    # [x1, y1, x2, y2]
    box: List[float]

class DatasetItem(BaseModel):
    id: str
    stage: str  # "collected", "pending_review", "approved", "rejected", "validation"
    image_url: str
    image_path: str
    timestamp: str
    source: str
    model_version: str
    detections: List[BBoxAnnotation] = Field(default_factory=list)
    empty_rate: float = 0.0
    tags: List[str] = Field(default_factory=list)

class ReviewAction(BaseModel):
    action: str = Field(..., description="'approve', 'reject', 'update_labels'")
    annotations: Optional[List[BBoxAnnotation]] = None

class TrainingRequest(BaseModel):
    epochs: int = 50
    batch_size: int = 16
    imgsz: int = 640
    lr0: float = 0.01
    base_model_version: Optional[str] = "production"
    name: Optional[str] = None

class TrainingStatus(BaseModel):
    status: str  # "idle", "training", "evaluating", "completed", "failed"
    progress_percent: float = 0.0
    current_epoch: int = 0
    total_epochs: int = 0
    message: str = ""
    candidate_version: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
