from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class DetectionItem(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    box: List[float] = Field(description="[x1, y1, x2, y2] coords")

class TimingMetrics(BaseModel):
    preprocess_ms: float = 0.0
    inference_ms: float = 0.0
    postprocess_ms: float = 0.0
    total_ms: float = 0.0

class DetectionResult(BaseModel):
    detections: List[DetectionItem] = Field(default_factory=list)
    timings: TimingMetrics = Field(default_factory=TimingMetrics)
    model_version: str = "unknown"
    frame_width: int = 0
    frame_height: int = 0
