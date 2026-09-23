from typing import Optional, List
from pydantic import BaseModel, Field

class InventoryMetrics(BaseModel):
    products: int = 0
    missing: int = 0
    total_spaces: int = 0
    occupancy_rate: float = 0.0
    empty_rate: float = 0.0
    roi_applied: bool = False

class ROISetting(BaseModel):
    # Coordenadas normalizadas [x1, y1, x2, y2] entre 0.0 y 1.0
    roi: Optional[List[float]] = Field(default=None, description="[x1, y1, x2, y2] normalizado o null")
