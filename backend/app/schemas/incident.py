"""Schemas Pydantic para el sistema de gestión de incidencias y ubicaciones."""
from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# --- Enumeraciones ---

SeverityLevel = Literal["LOW", "MODERATE", "CRITICAL"]
IncidentStatus = Literal["ACTIVE", "RESOLVED"]
AlertChannel = Literal["webhook", "push", "email"]
AlertSendStatus = Literal["pending", "sent", "failed"]


# --- Location ---

class Location(BaseModel):
    """Representa una ubicación física permanente (pasillo/góndola)."""
    id: str                          # location_id permanente, ej: "GND-001"
    name: str                        # nombre base, ej: "GND-001"
    display_order: int               # orden visual, puede cambiar
    display_name: str                # nombre visible, ej: "Pasillo 1"
    is_active: bool = True
    created_at: str
    updated_at: str


class LocationCreate(BaseModel):
    id: str
    name: Optional[str] = None
    display_order: Optional[int] = None


class LocationUpdate(BaseModel):
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


# --- Severity ---

class SeverityInfo(BaseModel):
    severity: SeverityLevel
    status: str          # "Urgente" / "Atención Rápida" / "Prevención"
    action: str          # "Reposición total" / "Reposición moderada" / "Reposición preventiva"
    message: str         # mensaje descriptivo dinámico


# --- Stock Metrics ---

class StockMetrics(BaseModel):
    expected_count: int = 0          # espacios totales detectados
    missing_count: int = 0           # espacios vacíos (class_id=0, "missing")
    remaining_count: int = 0         # productos presentes
    missing_percentage: float = 0.0  # 0.0 - 100.0
    remaining_percentage: float = 0.0


# --- Incident ---

class Incident(BaseModel):
    """Incidencia de faltante detectada por YOLOv8."""
    id: str
    location_id: str
    image_path: Optional[str] = None
    image_url: Optional[str] = None

    # Métricas de stock al momento de creación
    missing_count: int = 0
    expected_count: int = 0
    remaining_count: int = 0
    missing_percentage: float = 0.0
    remaining_percentage: float = 0.0

    # Severidad calculada por backend
    severity: SeverityLevel = "LOW"
    status: IncidentStatus = "ACTIVE"

    # Confianza máxima de las detecciones missing
    confidence: float = 0.0

    created_at: str
    resolved_at: Optional[str] = None

    # Alerta enviada asociada
    alert_sent: bool = False
    alert_sent_at: Optional[str] = None
    alert_channel: Optional[str] = None


class IncidentSummary(BaseModel):
    """Versión resumida para listados."""
    id: str
    location_id: str
    display_name: str           # nombre visual del pasillo en el momento histórico
    missing_percentage: float
    missing_count: int
    expected_count: int
    remaining_count: int
    severity: SeverityLevel
    status: IncidentStatus
    created_at: str
    resolved_at: Optional[str] = None
    image_url: Optional[str] = None
    alert_sent: bool = False


# --- Aisle (pasillo en el dashboard) ---

class AisleStatus(BaseModel):
    """Estado actual de un pasillo para el Dashboard."""
    location_id: str
    display_order: int
    display_name: str         # Título Principal: "Alerta 1", "Alerta 2", ...
    aisle_name: Optional[str] = None  # Sub-etiqueta (Ubicación): "Pasillo 1", "Pasillo 2", ...
    filename: Optional[str] = None
    image_url: Optional[str] = None

    # Métricas actuales (de la imagen analizada)
    stock: StockMetrics

    # Severidad calculada
    severity_info: SeverityInfo

    # Estado de stock clasificado explícitamente
    # "SIN_STOCK"      -> 0 detecciones, góndola completamente vacía
    # "FALTA_PRODUCTO" -> hay missing > 0
    # "STOCK_CORRECTO" -> solo products, sin missing
    stock_status: str = "FALTA_PRODUCTO"

    # Información de depuración obligatoria de la evaluación de góndola
    debug_info: Optional[dict] = None

    # Incidencia activa
    active_incident_id: Optional[str] = None
    has_active_incident: bool = True
    last_detected_at: Optional[str] = None
    alert_sent: bool = False


# --- Analytics & Chart Schemas ---

class StockChartCategory(BaseModel):
    key: str                    # "urgent", "quick_attention", "emptying"
    name: str                   # "Urgente", "Atención Rápida", "Góndola Vaciándose"
    label: str                  # "🔴 Urgente (0% - 10% Stock)", etc.
    range_label: str            # "0% - 10% Stock"
    count: int = 0
    color: str                  # Código de color hex
    percentage: float = 0.0     # % de alertas en esta categoría


class StockAnalyticsSummary(BaseModel):
    total_active_alerts: int = 0
    average_depletion_pct: float = 0.0   # Porcentaje global de desabastecimiento promedio
    urgent_count: int = 0                # 0% - 10% Stock
    quick_attention_count: int = 0       # 10% - 15% Stock
    emptying_count: int = 0              # 15% - 20% Stock (o >15% con faltantes)
    categories: List[StockChartCategory] = Field(default_factory=list)


# --- Dashboard Summary ---

class DashboardSummary(BaseModel):
    is_active: bool = False     # False si no hay imágenes con fallas
    message: Optional[str] = None
    total_aisles: int = 0
    aisles_critical: int = 0
    aisles_moderate: int = 0
    aisles_low: int = 0
    aisles_ok: int = 0          # sin detecciones missing
    total_missing: int = 0
    total_spaces: int = 0
    overall_missing_pct: float = 0.0
    active_incidents: int = 0
    aisles: List[AisleStatus] = Field(default_factory=list)
    analytics: Optional[StockAnalyticsSummary] = None


# --- Image Upload & Analysis ---

class ImageAnalysisDetail(BaseModel):
    filename: str
    saved_to_historica: bool
    missing_count: int = 0
    product_count: int = 0
    expected_count: int = 0
    missing_percentage: float = 0.0
    severity: Optional[str] = None
    message: str


class UploadAnalysisResponse(BaseModel):
    total_analyzed: int
    faults_detected: int
    discarded_clean: int
    results: List[ImageAnalysisDetail] = Field(default_factory=list)
    dashboard_active: bool


# --- Alert Send (replenishment alert) ---

class ReplenishmentAlertRequest(BaseModel):
    channel: AlertChannel = "webhook"


class ReplenishmentAlertRecord(BaseModel):
    id: str
    incident_id: str
    channel: AlertChannel
    payload: dict
    status: AlertSendStatus
    sent_at: Optional[str] = None
    error_message: Optional[str] = None

