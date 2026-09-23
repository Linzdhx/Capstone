import os
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# Localizar la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_PATH = BASE_DIR / "configs" / "app_config.yaml"

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

class CameraConfig(BaseModel):
    source_type: str = "webcam"  # webcam, usb, rtsp, synthetic
    webcam_index: int = 0
    rtsp_url: str = ""
    target_fps: int = 30
    reconnect_delay_seconds: float = 3.0
    width: int = 1280
    height: int = 720

class ModelConfig(BaseModel):
    production_path: str = "models/production/best.pt"
    candidates_dir: str = "models/candidates"
    archive_dir: str = "models/archive"
    default_confidence: float = 0.25
    default_iou: float = 0.45
    device: str = "auto"

class InventoryConfig(BaseModel):
    # [x1, y1, x2, y2] coordenadas relativas normalizadas 0.0 - 1.0
    roi: Optional[List[float]] = None

class AlertsConfig(BaseModel):
    empty_threshold: float = 0.80
    consecutive_seconds: float = 3.0
    cooldown_seconds: float = 30.0
    images_dir: str = "alerts/images"
    logs_file: str = "alerts/logs/alerts.jsonl"
    webhook_url: str = ""

class ActiveLearningConfig(BaseModel):
    auto_collect: bool = True
    low_confidence_threshold: float = 0.40
    high_missing_threshold: float = 0.70
    min_seconds_between_captures: float = 5.0
    collected_dir: str = "data/collected"
    pending_dir: str = "data/pending_review"
    approved_dir: str = "data/approved"
    validation_dir: str = "data/validation"

class TrainingConfig(BaseModel):
    epochs: int = 50
    batch_size: int = 16
    imgsz: int = 640
    lr0: float = 0.01
    patience: int = 15
    min_approved_samples: int = 5
    eval_pass_map50: float = 0.80

class AppSettings(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    camera: CameraConfig = Field(default_factory=CameraConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    inventory: InventoryConfig = Field(default_factory=InventoryConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    active_learning: ActiveLearningConfig = Field(default_factory=ActiveLearningConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)

def load_settings() -> AppSettings:
    """Carga configuración combinando defaults, app_config.yaml y variables de entorno."""
    data: Dict[str, Any] = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    data = loaded
        except Exception as e:
            print(f"Error cargando {CONFIG_PATH}: {e}")

    settings = AppSettings(**data)
    
    # Sobrescribir con variables de entorno si existen
    if "CAMERA_SOURCE_TYPE" in os.environ:
        settings.camera.source_type = os.environ["CAMERA_SOURCE_TYPE"]
    if "CAMERA_WEBCAM_INDEX" in os.environ:
        try:
            settings.camera.webcam_index = int(os.environ["CAMERA_WEBCAM_INDEX"])
        except ValueError:
            pass
    if "CAMERA_RTSP_URL" in os.environ:
        settings.camera.rtsp_url = os.environ["CAMERA_RTSP_URL"]
    if "ALERT_EMPTY_THRESHOLD" in os.environ:
        try:
            settings.alerts.empty_threshold = float(os.environ["ALERT_EMPTY_THRESHOLD"])
        except ValueError:
            pass
    if "ALERT_CONSECUTIVE_SECONDS" in os.environ:
        try:
            settings.alerts.consecutive_seconds = float(os.environ["ALERT_CONSECUTIVE_SECONDS"])
        except ValueError:
            pass
    if "ALERT_COOLDOWN_SECONDS" in os.environ:
        try:
            settings.alerts.cooldown_seconds = float(os.environ["ALERT_COOLDOWN_SECONDS"])
        except ValueError:
            pass
            
    return settings

settings = load_settings()
