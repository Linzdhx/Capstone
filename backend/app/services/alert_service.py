import os
import time
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
import cv2
import numpy as np

from backend.app.core.logging import logger
from backend.app.core.config import BASE_DIR, settings
from backend.app.schemas.alert import AlertEvent, AlertStatus
from backend.app.schemas.inventory import InventoryMetrics

class AlertService:
    """Sistema de alertas por desabastecimiento con ventana temporal, cooldown y registro persistente."""

    def __init__(
        self,
        empty_threshold: Optional[float] = None,
        consecutive_seconds: Optional[float] = None,
        cooldown_seconds: Optional[float] = None,
        images_dir: Optional[Path] = None,
        logs_file: Optional[Path] = None
    ):
        self.empty_threshold = empty_threshold if empty_threshold is not None else settings.alerts.empty_threshold
        self.consecutive_seconds = consecutive_seconds if consecutive_seconds is not None else settings.alerts.consecutive_seconds
        self.cooldown_seconds = cooldown_seconds if cooldown_seconds is not None else settings.alerts.cooldown_seconds
        
        self.images_dir = images_dir if images_dir is not None else BASE_DIR / "alerts" / "images"
        self.logs_file = logs_file if logs_file is not None else BASE_DIR / "alerts" / "logs" / "alerts.jsonl"
        
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.logs_file.parent.mkdir(parents=True, exist_ok=True)

        self._high_condition_start_time: Optional[float] = None
        self._last_alert_triggered_time: float = 0.0
        self._is_active: bool = False
        self._last_alert_event: Optional[AlertEvent] = None
        self._history: List[AlertEvent] = self._load_recent_history()

    def update_config(
        self,
        empty_threshold: Optional[float] = None,
        consecutive_seconds: Optional[float] = None,
        cooldown_seconds: Optional[float] = None
    ) -> None:
        if empty_threshold is not None:
            self.empty_threshold = float(empty_threshold)
        if consecutive_seconds is not None:
            self.consecutive_seconds = float(consecutive_seconds)
        if cooldown_seconds is not None:
            self.cooldown_seconds = float(cooldown_seconds)

    def _load_recent_history(self, limit: int = 50) -> List[AlertEvent]:
        history: List[AlertEvent] = []
        if self.logs_file.exists():
            try:
                with open(self.logs_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in reversed(lines[-limit:]):
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            history.append(AlertEvent(**data))
            except Exception as e:
                logger.warning(f"No se pudo cargar historial de alertas: {e}")
        return history

    def evaluate(
        self,
        metrics: InventoryMetrics,
        frame: Optional[np.ndarray] = None,
        detections_count: int = 0
    ) -> Optional[AlertEvent]:
        """Evalúa las métricas actuales del frame. Si la condición persiste más de consecutive_seconds y se superó el cooldown, dispara alerta."""
        now = time.time()
        cooldown_remaining = max(0.0, (self._last_alert_triggered_time + self.cooldown_seconds) - now)

        # Regla: Si no hay espacios detectados, no generar alerta ni división por cero
        if metrics.total_spaces == 0:
            self._high_condition_start_time = None
            self._is_active = False
            return None

        # Condición de desabastecimiento: empty_rate >= empty_threshold (80%)
        if metrics.empty_rate >= self.empty_threshold:
            if self._high_condition_start_time is None:
                self._high_condition_start_time = now

            duration = now - self._high_condition_start_time
            # Solo disparar si superó consecutive_seconds y el cooldown ya expiró
            if duration >= self.consecutive_seconds and cooldown_remaining == 0.0:
                event = self._trigger_alert(metrics, frame, detections_count, now)
                self._is_active = True
                return event
            elif duration >= self.consecutive_seconds:
                # Condición alta pero aún en cooldown
                self._is_active = True
                return None
        else:
            # Condición resuelta o volvió a niveles normales
            self._high_condition_start_time = None
            self._is_active = False

        return None

    def _trigger_alert(
        self,
        metrics: InventoryMetrics,
        frame: Optional[np.ndarray],
        detections_count: int,
        timestamp_float: float
    ) -> AlertEvent:
        event_id = str(uuid.uuid4())[:8]
        ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp_float))
        snapshot_filename = None
        snapshot_url = None

        if frame is not None:
            snapshot_filename = f"alert_{event_id}_{int(timestamp_float)}.jpg"
            save_path = self.images_dir / snapshot_filename
            try:
                cv2.imwrite(str(save_path), frame)
                snapshot_url = f"/api/alerts/snapshots/{snapshot_filename}"
            except Exception as e:
                logger.error(f"Error guardando snapshot de alerta: {e}")

        event = AlertEvent(
            id=event_id,
            timestamp=ts_str,
            empty_rate=metrics.empty_rate,
            occupancy_rate=metrics.occupancy_rate,
            products=metrics.products,
            missing=metrics.missing,
            snapshot_filename=snapshot_filename,
            snapshot_url=snapshot_url,
            detections_count=detections_count,
            message=f"Alerta de estantería vacía: {round(metrics.empty_rate * 100, 1)}% faltantes ({metrics.missing}/{metrics.total_spaces})"
        )

        self._last_alert_triggered_time = timestamp_float
        self._last_alert_event = event
        self._history.insert(0, event)

        # Registro persistente en JSONL
        try:
            with open(self.logs_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.model_dump()) + "\n")
        except Exception as e:
            logger.error(f"Error escribiendo en {self.logs_file}: {e}")

        logger.warning(f"¡ALERTA DISPARADA! {event.message}")
        self._dispatch_webhook(event)
        return event

    def _dispatch_webhook(self, event: AlertEvent) -> None:
        """Preparado para notificaciones externas futuras (Slack, Discord, webhook interno)."""
        webhook_url = settings.alerts.webhook_url
        if not webhook_url:
            return
        try:
            import requests
            requests.post(webhook_url, json=event.model_dump(), timeout=2.0)
        except Exception as e:
            logger.warning(f"No se pudo despachar webhook de alerta: {e}")

    def get_status(self, current_empty_rate: float = 0.0) -> AlertStatus:
        now = time.time()
        cooldown_remaining = max(0.0, (self._last_alert_triggered_time + self.cooldown_seconds) - now)
        consecutive = 0.0
        if self._high_condition_start_time is not None:
            consecutive = round(now - self._high_condition_start_time, 2)

        return AlertStatus(
            is_active=self._is_active,
            consecutive_seconds_high=consecutive,
            cooldown_remaining_seconds=round(cooldown_remaining, 1),
            current_empty_rate=round(current_empty_rate, 4),
            threshold=self.empty_threshold,
            last_alert=self._last_alert_event
        )

    def get_history(self, limit: int = 50) -> List[AlertEvent]:
        return self._history[:limit]

alert_service = AlertService()
