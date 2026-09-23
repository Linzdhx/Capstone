from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class AlertEvent(BaseModel):
    id: str
    timestamp: str
    empty_rate: float
    occupancy_rate: float
    products: int
    missing: int
    snapshot_filename: Optional[str] = None
    snapshot_url: Optional[str] = None
    detections_count: int = 0
    message: str

class AlertStatus(BaseModel):
    is_active: bool = False
    consecutive_seconds_high: float = 0.0
    cooldown_remaining_seconds: float = 0.0
    current_empty_rate: float = 0.0
    threshold: float = 0.80
    last_alert: Optional[AlertEvent] = None
