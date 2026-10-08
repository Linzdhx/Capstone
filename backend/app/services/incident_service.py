"""
IncidentService: gestiona ubicaciones, incidencias de faltantes, deduplicación temporal,
cálculo de métricas, severidad automática, y alertas de reposición.
"""
import json
import time
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import cv2
import numpy as np
import requests
import re

from backend.app.core.logging import logger
from backend.app.core.config import BASE_DIR, settings
from backend.app.schemas.detection import DetectionItem
from backend.app.schemas.incident import (
    Location, Incident, IncidentSummary, AisleStatus, StockMetrics,
    SeverityInfo, DashboardSummary, ReplenishmentAlertRecord,
    SeverityLevel, ImageAnalysisDetail, UploadAnalysisResponse,
    StockAnalyticsSummary, StockChartCategory
)


# ---------------------------------------------------------------------------
# Constantes de configuración (sobreescribibles desde .env o app_config.yaml)
# ---------------------------------------------------------------------------
MISSING_CLASS_ID = 0
MISSING_CLASS_NAME = "missing"
PRODUCT_CLASS_NAME = "product"

INCIDENT_CONFIDENCE_THRESHOLD: float = 0.5
DUPLICATE_WINDOW_SECONDS: float = 30.0  # agrupar detecciones consecutivas en <30s

_DATA_DIR = BASE_DIR / "data" / "incidents"
_LOCATIONS_FILE = _DATA_DIR / "locations.json"
_INCIDENTS_FILE = _DATA_DIR / "incidents.jsonl"
_ALERTS_FILE = _DATA_DIR / "alert_sends.jsonl"
_IMAGES_DIR = BASE_DIR / "alerts" / "images"
_HISTORICA_DIR = BASE_DIR / "historica"
_APPROVED_DIR = BASE_DIR / "data" / "approved"
_PENDING_DIR = BASE_DIR / "data" / "pending_review"



# ---------------------------------------------------------------------------
# Helper: calcular severidad a partir de missing_percentage
# ---------------------------------------------------------------------------
def compute_severity(missing_pct: float, display_name: str) -> SeverityInfo:
    pct = max(0.0, min(100.0, missing_pct))
    if pct > 20.0:
        return SeverityInfo(
            severity="CRITICAL",
            status="Urgente",
            action="Reposición total",
            message=f"Atención inmediata: El {display_name} requiere reposición total de mercancía."
        )
    elif pct > 10.0:
        return SeverityInfo(
            severity="MODERATE",
            status="Atención Rápida",
            action="Reposición moderada",
            message=(
                f"Aviso: El {display_name} requiere reposición parcial de stock. "
                f"Se estiman {round(pct, 1)}% de unidades faltantes."
            )
        )
    else:
        return SeverityInfo(
            severity="LOW",
            status="Prevención",
            action="Reposición preventiva",
            message=(
                f"Aviso preventivo: El {display_name} presenta un nivel bajo de faltantes. "
                "Se recomienda revisar y mantener el stock mínimo."
            )
        )


# ---------------------------------------------------------------------------
# Helper: calcular StockMetrics a partir de detecciones
# ---------------------------------------------------------------------------
def compute_stock_metrics(detections: List[DetectionItem], conf_threshold: float) -> StockMetrics:
    filtered = [d for d in detections]  # ya vienen filtradas por ROI si aplica
    missing_count = sum(
        1 for d in filtered
        if d.class_name.lower() == MISSING_CLASS_NAME and d.confidence >= conf_threshold
    )
    product_count = sum(
        1 for d in filtered
        if d.class_name.lower() == PRODUCT_CLASS_NAME and d.confidence >= conf_threshold
    )
    expected_count = missing_count + product_count
    remaining_count = product_count

    # Si expected_count == 0 (0 detecciones en estante vacío), la góndola está SIN STOCK (100% faltante)
    if expected_count == 0:
        missing_pct = 100.0
        remaining_pct = 0.0
    else:
        missing_pct = round((missing_count / expected_count) * 100, 2)
        remaining_pct = round((remaining_count / expected_count) * 100, 2)

    # Clamp
    missing_pct = max(0.0, min(100.0, missing_pct))
    remaining_pct = max(0.0, min(100.0, remaining_pct))
    return StockMetrics(
        expected_count=expected_count,
        missing_count=missing_count,
        remaining_count=remaining_count,
        missing_percentage=missing_pct,
        remaining_percentage=remaining_pct
    )


# ---------------------------------------------------------------------------
# IncidentService
# ---------------------------------------------------------------------------
class IncidentService:
    """
    Servicio central de gestión de incidencias de faltantes:
    - Persiste ubicaciones (Location) con identidad permanente (location_id).
    - Crea/actualiza incidencias evitando duplicados consecutivos (DUPLICATE_WINDOW_SECONDS).
    - Calcula severidad automáticamente en backend.
    - Mantiene estado actual por pasillo para el Dashboard.
    - Permite enviar alertas de reposición y registrar el envío.
    """

    def __init__(
        self,
        confidence_threshold: float = INCIDENT_CONFIDENCE_THRESHOLD,
        duplicate_window_seconds: float = DUPLICATE_WINDOW_SECONDS
    ):
        self.confidence_threshold = confidence_threshold
        self.duplicate_window_seconds = duplicate_window_seconds

        self._lock = threading.RLock()

        # Asegurar directorios
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        _HISTORICA_DIR.mkdir(parents=True, exist_ok=True)

        # Estado en memoria
        self._locations: Dict[str, Location] = {}       # location_id -> Location
        self._incidents: Dict[str, Incident] = {}        # incident_id -> Incident
        self._alert_records: List[ReplenishmentAlertRecord] = []

        # Para deduplicación: última detección por location_id
        self._last_detection_time: Dict[str, float] = {}  # loc_id -> timestamp
        self._active_incident_by_loc: Dict[str, str] = {}  # loc_id -> incident_id activo

        # Estado actual de telemetría por ubicación (se actualiza en tiempo real)
        self._current_detections: List[DetectionItem] = []
        self._current_frame: Optional[np.ndarray] = None

        self._load_state()
        self._ensure_default_location()

    # -------------------------------------------------------------------------
    # Persistencia
    # -------------------------------------------------------------------------

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _load_state(self) -> None:
        """Carga ubicaciones e incidencias desde disco."""
        # Locations
        if _LOCATIONS_FILE.exists():
            try:
                with open(_LOCATIONS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        loc = Location(**item)
                        self._locations[loc.id] = loc
            except Exception as e:
                logger.warning(f"No se pudo cargar locations.json: {e}")

        # Incidents (JSONL)
        if _INCIDENTS_FILE.exists():
            try:
                with open(_INCIDENTS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            inc = Incident(**json.loads(line))
                            self._incidents[inc.id] = inc
                            if inc.status == "ACTIVE":
                                self._active_incident_by_loc[inc.location_id] = inc.id
            except Exception as e:
                logger.warning(f"No se pudo cargar incidents.jsonl: {e}")

        # Alert records (JSONL)
        if _ALERTS_FILE.exists():
            try:
                with open(_ALERTS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            rec = ReplenishmentAlertRecord(**json.loads(line))
                            self._alert_records.append(rec)
            except Exception as e:
                logger.warning(f"No se pudo cargar alert_sends.jsonl: {e}")

        logger.info(
            f"IncidentService cargado: {len(self._locations)} ubicaciones, "
            f"{len(self._incidents)} incidencias, {len(self._alert_records)} registros de alerta."
        )

    def _save_locations(self) -> None:
        try:
            with open(_LOCATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump([loc.model_dump() for loc in self._locations.values()], f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando locations.json: {e}")

    def _append_incident(self, inc: Incident) -> None:
        """Persiste/actualiza incidencia en el archivo JSONL (reescribe todo para actualizaciones)."""
        try:
            with open(_INCIDENTS_FILE, "w", encoding="utf-8") as f:
                for i in self._incidents.values():
                    f.write(json.dumps(i.model_dump()) + "\n")
        except Exception as e:
            logger.error(f"Error guardando incidents.jsonl: {e}")

    def _append_alert_record(self, rec: ReplenishmentAlertRecord) -> None:
        try:
            with open(_ALERTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec.model_dump()) + "\n")
        except Exception as e:
            logger.error(f"Error guardando alert_sends.jsonl: {e}")

    # -------------------------------------------------------------------------
    # Gestión de Locations
    # -------------------------------------------------------------------------

    def _ensure_default_location(self) -> None:
        """Crea la ubicación por defecto si no existe ninguna."""
        if not self._locations:
            now = self._now_iso()
            loc = Location(
                id="GND-001",
                name="GND-001",
                display_order=1,
                display_name="Pasillo 1",
                is_active=True,
                created_at=now,
                updated_at=now
            )
            self._locations[loc.id] = loc
            self._save_locations()
            logger.info("Ubicación por defecto GND-001 creada.")

    def get_locations(self, active_only: bool = True) -> List[Location]:
        with self._lock:
            locs = list(self._locations.values())
            if active_only:
                locs = [l for l in locs if l.is_active]
            return sorted(locs, key=lambda l: l.display_order)

    def get_location(self, location_id: str) -> Optional[Location]:
        with self._lock:
            return self._locations.get(location_id)

    def create_location(self, location_id: str, name: Optional[str] = None) -> Location:
        with self._lock:
            if location_id in self._locations:
                return self._locations[location_id]
            # Calcular siguiente display_order
            existing_orders = [l.display_order for l in self._locations.values() if l.is_active]
            next_order = max(existing_orders, default=0) + 1
            now = self._now_iso()
            loc = Location(
                id=location_id,
                name=name or location_id,
                display_order=next_order,
                display_name=f"Pasillo {next_order}",
                is_active=True,
                created_at=now,
                updated_at=now
            )
            self._locations[location_id] = loc
            self._save_locations()
            return loc

    def reorder_locations_after_resolve(self, resolved_location_id: str) -> None:
        """
        Reordena el display_order de ubicaciones activas con incidencias activas.
        NO modifica location_id ni datos históricos.
        """
        with self._lock:
            # Obtener ubicaciones con incidencias activas (excluyendo la resuelta)
            active_locs_with_incidents = [
                loc_id for loc_id in self._active_incident_by_loc
                if loc_id != resolved_location_id and loc_id in self._locations
            ]
            # Reordenar secuencialmente por su display_order actual
            active_locs_with_incidents.sort(
                key=lambda lid: self._locations[lid].display_order
            )
            for i, lid in enumerate(active_locs_with_incidents, start=1):
                loc = self._locations[lid]
                # Solo actualizar si es necesario
                if loc.display_order != i:
                    self._locations[lid] = loc.model_copy(
                        update={"display_order": i, "updated_at": self._now_iso()}
                    )
            self._save_locations()

    # -------------------------------------------------------------------------
    # Core: Procesamiento de Frame
    # -------------------------------------------------------------------------

    def process_frame(
        self,
        detections: List[DetectionItem],
        frame: Optional[np.ndarray] = None,
        location_id: str = "GND-001"
    ) -> Optional[Incident]:
        """
        Procesa las detecciones de un frame y actualiza/crea incidencias.
        Reglas:
        1. Si no hay detecciones "missing" >= confidence_threshold, NO crear incidencia.
        2. Si hay detecciones missing >= threshold, crear o actualizar incidencia existente.
        3. Deduplicación: si la última detección fue en < duplicate_window_seconds, actualizar.
        4. Resolución automática: si la incidencia estaba ACTIVE pero ya no hay missing, resolverla.
        """
        with self._lock:
            # Asegurar que la ubicación existe
            if location_id not in self._locations:
                self._create_location_locked(location_id)

            # Filtrar detecciones missing con confianza suficiente
            missing_dets = [
                d for d in detections
                if d.class_name.lower() == MISSING_CLASS_NAME
                and d.confidence >= self.confidence_threshold
            ]
            has_missing = len(missing_dets) > 0

            # Calcular métricas de stock
            stock = compute_stock_metrics(detections, self.confidence_threshold)

            now = time.time()

            # Caso: NO hay missing -> resolver incidencia activa si existe
            if not has_missing:
                if location_id in self._active_incident_by_loc:
                    self._resolve_incident_locked(location_id, now)
                return None

            # Caso: HAY missing
            active_inc_id = self._active_incident_by_loc.get(location_id)
            last_time = self._last_detection_time.get(location_id, 0.0)
            within_window = (now - last_time) < self.duplicate_window_seconds

            if active_inc_id and within_window and active_inc_id in self._incidents:
                # Actualizar incidencia existente (no duplicar)
                inc = self._incidents[active_inc_id]
                max_conf = max(d.confidence for d in missing_dets)
                loc = self._locations[location_id]
                updated = inc.model_copy(update={
                    "missing_count": stock.missing_count,
                    "expected_count": stock.expected_count,
                    "remaining_count": stock.remaining_count,
                    "missing_percentage": stock.missing_percentage,
                    "remaining_percentage": stock.remaining_percentage,
                    "severity": compute_severity(stock.missing_percentage, loc.display_name).severity,
                    "confidence": round(max_conf, 4),
                })
                self._incidents[active_inc_id] = updated
                self._last_detection_time[location_id] = now
                self._append_incident(updated)
                return updated
            else:
                # Crear nueva incidencia
                if active_inc_id and active_inc_id in self._incidents:
                    # Resolver la anterior
                    self._resolve_incident_locked(location_id, now)

                incident = self._create_incident_locked(
                    location_id=location_id,
                    missing_dets=missing_dets,
                    stock=stock,
                    frame=frame,
                    now=now
                )
                self._last_detection_time[location_id] = now
                return incident

    def _create_location_locked(self, location_id: str) -> Location:
        """Crear location dentro de un bloque con lock ya adquirido."""
        existing_orders = [l.display_order for l in self._locations.values() if l.is_active]
        next_order = max(existing_orders, default=0) + 1
        now = self._now_iso()
        loc = Location(
            id=location_id,
            name=location_id,
            display_order=next_order,
            display_name=f"Pasillo {next_order}",
            is_active=True,
            created_at=now,
            updated_at=now
        )
        self._locations[location_id] = loc
        self._save_locations()
        return loc

    def _create_incident_locked(
        self,
        location_id: str,
        missing_dets: List[DetectionItem],
        stock: StockMetrics,
        frame: Optional[np.ndarray],
        now: float
    ) -> Incident:
        loc = self._locations[location_id]
        severity_info = compute_severity(stock.missing_percentage, loc.display_name)
        max_conf = max(d.confidence for d in missing_dets) if missing_dets else 0.0
        inc_id = f"INC-{str(uuid.uuid4())[:8].upper()}"
        now_iso = self._now_iso()

        image_path = None
        image_url = None
        if frame is not None:
            fname = f"incident_{inc_id}_{int(now)}.jpg"
            save_path = _IMAGES_DIR / fname
            try:
                cv2.imwrite(str(save_path), frame)
                image_path = str(save_path)
                image_url = f"/api/incidents/images/{fname}"
            except Exception as e:
                logger.error(f"Error guardando imagen de incidencia: {e}")

        inc = Incident(
            id=inc_id,
            location_id=location_id,
            image_path=image_path,
            image_url=image_url,
            missing_count=stock.missing_count,
            expected_count=stock.expected_count,
            remaining_count=stock.remaining_count,
            missing_percentage=stock.missing_percentage,
            remaining_percentage=stock.remaining_percentage,
            severity=severity_info.severity,
            status="ACTIVE",
            confidence=round(max_conf, 4),
            created_at=now_iso,
            resolved_at=None,
            alert_sent=False,
        )

        self._incidents[inc.id] = inc
        self._active_incident_by_loc[location_id] = inc.id
        self._append_incident(inc)
        logger.info(
            f"Nueva incidencia {inc_id} creada para {location_id} "
            f"({loc.display_name}) | {stock.missing_percentage:.1f}% faltantes | {severity_info.severity}"
        )
        return inc

    def _resolve_incident_locked(self, location_id: str, now: float) -> None:
        inc_id = self._active_incident_by_loc.get(location_id)
        if not inc_id or inc_id not in self._incidents:
            return
        inc = self._incidents[inc_id]
        resolved = inc.model_copy(update={
            "status": "RESOLVED",
            "resolved_at": self._now_iso()
        })
        self._incidents[inc_id] = resolved
        del self._active_incident_by_loc[location_id]
        self._append_incident(resolved)
        # Reordenar pasillos activos
        self.reorder_locations_after_resolve(location_id)
        logger.info(f"Incidencia {inc_id} resuelta para ubicación {location_id}.")

    # -------------------------------------------------------------------------
    # Dashboard / Estado actual
    # -------------------------------------------------------------------------

    def get_dashboard_summary(self, current_detections: List[DetectionItem]) -> DashboardSummary:
        """
        Construye el resumen del Dashboard usando el estado de detecciones actual.
        Las métricas son calculadas a partir de datos reales de inferencia.
        """
        with self._lock:
            locations = sorted(
                [l for l in self._locations.values() if l.is_active],
                key=lambda l: l.display_order
            )

            # Para el estado actual usamos GND-001 como única ubicación (sistema mono-cámara).
            # Arquitectura preparada para multi-ubicación.
            aisles: List[AisleStatus] = []

            total_missing = 0
            total_spaces = 0
            aisles_critical = 0
            aisles_moderate = 0
            aisles_low = 0
            aisles_ok = 0
            active_incidents = 0

            for loc in locations:
                # Calcular stock actual para esta ubicación
                stock = compute_stock_metrics(current_detections, self.confidence_threshold)
                severity_info = compute_severity(stock.missing_percentage, loc.display_name)

                active_inc_id = self._active_incident_by_loc.get(loc.id)
                has_active = active_inc_id is not None
                last_detected = None
                if has_active and active_inc_id in self._incidents:
                    last_detected = self._incidents[active_inc_id].created_at
                    active_incidents += 1

                aisle = AisleStatus(
                    location_id=loc.id,
                    display_order=loc.display_order,
                    display_name=loc.display_name,
                    stock=stock,
                    severity_info=severity_info,
                    active_incident_id=active_inc_id,
                    has_active_incident=has_active,
                    last_detected_at=last_detected
                )
                aisles.append(aisle)

                total_missing += stock.missing_count
                total_spaces += stock.expected_count

                if stock.expected_count == 0:
                    aisles_ok += 1
                elif severity_info.severity == "CRITICAL":
                    aisles_critical += 1
                elif severity_info.severity == "MODERATE":
                    aisles_moderate += 1
                else:
                    aisles_low += 1

            overall_missing_pct = (
                round((total_missing / total_spaces) * 100, 2) if total_spaces > 0 else 0.0
            )

            return DashboardSummary(
                total_aisles=len(locations),
                aisles_critical=aisles_critical,
                aisles_moderate=aisles_moderate,
                aisles_low=aisles_low,
                aisles_ok=aisles_ok,
                total_missing=total_missing,
                total_spaces=total_spaces,
                overall_missing_pct=overall_missing_pct,
                active_incidents=active_incidents,
                aisles=aisles
            )

    # -------------------------------------------------------------------------
    # Consultas de incidencias
    # -------------------------------------------------------------------------

    def get_incidents(
        self,
        status_filter: Optional[str] = None,
        location_id: Optional[str] = None,
        limit: int = 100
    ) -> List[IncidentSummary]:
        with self._lock:
            incidents = list(self._incidents.values())

            if status_filter:
                incidents = [i for i in incidents if i.status == status_filter]
            if location_id:
                incidents = [i for i in incidents if i.location_id == location_id]

            # Ordenar por fecha descendente
            incidents.sort(key=lambda i: i.created_at, reverse=True)
            incidents = incidents[:limit]

            summaries = []
            for inc in incidents:
                loc = self._locations.get(inc.location_id)
                display_name = loc.display_name if loc else inc.location_id
                summaries.append(IncidentSummary(
                    id=inc.id,
                    location_id=inc.location_id,
                    display_name=display_name,
                    missing_percentage=inc.missing_percentage,
                    missing_count=inc.missing_count,
                    expected_count=inc.expected_count,
                    remaining_count=inc.remaining_count,
                    severity=inc.severity,
                    status=inc.status,
                    created_at=inc.created_at,
                    resolved_at=inc.resolved_at,
                    image_url=inc.image_url,
                    alert_sent=inc.alert_sent,
                ))
            return summaries

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        with self._lock:
            return self._incidents.get(incident_id)

    def resolve_incident(self, incident_id: str) -> Optional[Incident]:
        with self._lock:
            inc = self._incidents.get(incident_id)
            if not inc or inc.status == "RESOLVED":
                return inc
            now = time.time()
            self._resolve_incident_locked(inc.location_id, now)
            return self._incidents.get(incident_id)

    # -------------------------------------------------------------------------
    # Alertas de reposición
    # -------------------------------------------------------------------------

    def send_replenishment_alert(
        self,
        incident_id: str,
        channel: str = "webhook"
    ) -> ReplenishmentAlertRecord:
        """
        Genera y envía una alerta de reposición para la incidencia dada.
        Registra el envío y evita duplicación (una alerta por incidencia por defecto).
        """
        with self._lock:
            inc = self._incidents.get(incident_id)
            if not inc:
                raise ValueError(f"Incidencia {incident_id} no encontrada.")

            if inc.alert_sent:
                raise ValueError(f"Ya se ha enviado una alerta de reposición para la incidencia {incident_id}. Evite envíos duplicados.")

            loc = self._locations.get(inc.location_id)
            display_name = loc.display_name if loc else inc.location_id

            severity_info = compute_severity(inc.missing_percentage, display_name)

            payload = {
                "event": "stock_replenishment_alert",
                "timestamp": self._now_iso(),
                "location": {
                    "location_id": inc.location_id,
                    "display_name": display_name,
                },
                "stock": {
                    "expected_count": inc.expected_count,
                    "missing_count": inc.missing_count,
                    "remaining_count": inc.remaining_count,
                    "missing_percentage": inc.missing_percentage,
                    "remaining_percentage": inc.remaining_percentage,
                },
                "alert": {
                    "severity": severity_info.severity,
                    "status": severity_info.status,
                    "action": severity_info.action,
                    "message": severity_info.message,
                },
                "source": {
                    "detection_model": "YOLOv8",
                    "incident_id": inc.id,
                }
            }

            rec_id = str(uuid.uuid4())[:8].upper()
            now_iso = self._now_iso()
            status: str = "pending"
            error_msg: Optional[str] = None

            # Intentar envío
            if channel == "webhook":
                webhook_url = settings.alerts.webhook_url
                if webhook_url:
                    try:
                        resp = requests.post(webhook_url, json=payload, timeout=5.0)
                        resp.raise_for_status()
                        status = "sent"
                        logger.info(f"Alerta de reposición enviada por webhook para {incident_id}.")
                    except Exception as e:
                        status = "failed"
                        error_msg = str(e)
                        logger.warning(f"Fallo webhook alerta reposición: {e}")
                else:
                    # Sin URL configurada, marcar como sent (registro interno)
                    status = "sent"
                    logger.info(f"Alerta de reposición registrada (sin webhook configurado) para {incident_id}.")

            rec = ReplenishmentAlertRecord(
                id=rec_id,
                incident_id=incident_id,
                channel=channel,
                payload=payload,
                status=status,
                sent_at=now_iso if status == "sent" else None,
                error_message=error_msg
            )

            self._alert_records.append(rec)
            self._append_alert_record(rec)

            # Marcar incidencia como alertada
            updated_inc = inc.model_copy(update={
                "alert_sent": True,
                "alert_sent_at": now_iso,
                "alert_channel": channel
            })
            self._incidents[incident_id] = updated_inc
            self._append_incident(updated_inc)

            return rec

    def get_alert_records(self, incident_id: Optional[str] = None, limit: int = 50) -> List[ReplenishmentAlertRecord]:
        with self._lock:
            recs = self._alert_records
            if incident_id:
                recs = [r for r in recs if r.incident_id == incident_id]
            return list(reversed(recs))[:limit]

    # -------------------------------------------------------------------------
    # Gestión de Carpeta /historica y Activación Condicional del Dashboard
    # -------------------------------------------------------------------------


    def _filter_shelf_detections(
        self,
        detections: List[DetectionItem],
        frame_shape: Tuple[int, int],
        camera_id: str = "CAM-01",
        shelf_id: str = "GND-01",
        filename: str = "image"
    ) -> Tuple[List[DetectionItem], List[DetectionItem], bool, bool, str, dict]:
        """
        Clasificación robusta basada en evidencia visual para góndolas:
        1. Confianza asimétrica / calibrada:
           - Para 'missing' (espacios vacíos): confidence >= 0.40
           - Para 'product' (productos): confidence >= 0.45 (evita falsos positivos por ruido)
        2. Filtro morfológico anti-ruido:
           - Descarta tiras horizontales / portaprecios (h < 22 y w/h > 2.2)
           - Descarta ganchos / ranuras de pegboard (w < 16 y h/w > 2.5)
           - Descarta bordes de encuadre (y1 <= 2 o y2 >= h-2 con h < 25)
           - Descarta cajas sobredimensionadas (area > 65% del fotograma) y motas (area < 400)
        3. Evaluación de evidencia de stock y ocupación real:
           - Si los productos válidos cubren < 1.5% del área y son <= 2 detecciones aisladas,
             se consideran ruido espurio en góndola vacía.
        4. Árbol de decisión:
           - ¿Hay evidencia creíble de productos?
             -> NO (0 productos) => SIN_STOCK (Góndola completamente vacía, 100% faltante)
             -> SÍ (productos presentes):
                - ¿Hay faltantes válidos? => FALTA_PRODUCTO
                - ¿No hay faltantes? => STOCK_CORRECTO
        5. Información de debug temporal estructurada y log obligatorio.
        """
        h_img, w_img = frame_shape
        total_area = float(h_img * w_img) if (h_img * w_img) > 0 else 1.0

        filtered_missing: List[DetectionItem] = []
        filtered_products: List[DetectionItem] = []

        min_product_conf = max(0.45, self.confidence_threshold)
        min_missing_conf = 0.40

        for d in detections:
            cls_lower = d.class_name.lower()
            x1, y1, x2, y2 = d.box
            w = max(1.0, x2 - x1)
            h = max(1.0, y2 - y1)
            area = w * h
            aspect_ratio = h / w

            # Descartar cajas que cubren casi toda la imagen (fondo/estante entero)
            if area > total_area * 0.65:
                continue

            # Descartar motas diminutas de ruido
            if area < 400:
                continue

            # Filtros según la clase
            if cls_lower == MISSING_CLASS_NAME:
                if d.confidence < min_missing_conf:
                    continue
                # Descartar ruido de agujeros de panel perforado (pegbord)
                if (w < 16 and aspect_ratio > 2.8) or (area < 450 and w < 16):
                    continue
                filtered_missing.append(d)

            elif cls_lower == PRODUCT_CLASS_NAME:
                if d.confidence < min_product_conf:
                    continue
                # Descartar porta-etiquetas / riel horizontal de precio
                if h < 22 and (w / h) > 2.2:
                    continue
                # Descartar ganchos metálicos verticales o perforaciones
                if w < 16 and (h / w) > 2.5:
                    continue
                # Descartar artefactos pegados al borde superior o inferior
                if (y1 <= 2 and h < 25) or (y2 >= h_img - 2 and h < 25):
                    continue
                filtered_products.append(d)

        # Cálculo de ocupación de productos
        valid_products_area = sum(
            max(0.0, d.box[2] - d.box[0]) * max(0.0, d.box[3] - d.box[1])
            for d in filtered_products
        )
        estimated_occupancy = round((valid_products_area / total_area) * 100.0, 2)

        # Protección contra falsos positivos débiles en góndola completamente vacía:
        # Si sólo hay 1 o 2 detecciones y ocupan menos del 1.5% de la superficie total,
        # representan un reflejo, etiqueta residual o borde metálico en un estante vacío.
        if len(filtered_products) <= 2 and estimated_occupancy < 1.5:
            filtered_products = []
            valid_products_area = 0.0
            estimated_occupancy = 0.0

        # Árbol de decisión de clasificación
        if len(filtered_products) == 0:
            # Góndola completamente vacía: no hay productos presentes
            is_totally_empty = True
            is_empty_shelf = True
            stock_status = "SIN_STOCK"
        else:
            is_totally_empty = False
            is_empty_shelf = False
            if len(filtered_missing) > 0:
                stock_status = "FALTA_PRODUCTO"
            else:
                stock_status = "STOCK_CORRECTO"

        raw_confs = [round(float(d.confidence), 3) for d in detections]
        avg_conf = round(float(sum(raw_confs) / len(raw_confs)), 3) if raw_confs else 0.0

        debug_info = {
            "camera_id": camera_id,
            "shelf_id": shelf_id,
            "filename": filename,
            "detections_count": len(detections),
            "valid_detections_count": len(filtered_products) + len(filtered_missing),
            "valid_products_count": len(filtered_products),
            "valid_missing_count": len(filtered_missing),
            "confidence_scores": raw_confs[:15],
            "average_confidence": avg_conf,
            "estimated_occupancy": f"{estimated_occupancy}%",
            "final_stock_status": stock_status
        }

        # Log de depuración obligatorio
        logger.info(
            f"\n============================================================\n"
            f"[GONDOLA EVALUATION DEBUG]\n"
            f"Camera: {camera_id}\n"
            f"Shelf: {shelf_id}\n"
            f"Source: {filename}\n"
            f"Raw detections: {debug_info['detections_count']}\n"
            f"Valid detections: {debug_info['valid_detections_count']} "
            f"(Products: {len(filtered_products)}, Missing: {len(filtered_missing)})\n"
            f"Confidence scores: {debug_info['confidence_scores']}\n"
            f"Average confidence: {avg_conf}\n"
            f"Estimated occupancy: {debug_info['estimated_occupancy']}\n"
            f"Final status: {stock_status}\n"
            f"============================================================"
        )

        return filtered_missing, filtered_products, is_empty_shelf, is_totally_empty, stock_status, debug_info

    def process_and_filter_upload(self, original_filename: str, image_bytes: bytes) -> ImageAnalysisDetail:
        """
        Procesa una imagen subida aplicando inferencia con YOLOv8 y clasificación basada en evidencia:
        - Si es 'SIN_STOCK' (góndola vacía) o 'FALTA_PRODUCTO' (faltantes presentes):
          Se guarda físicamente en /historica con su metadata asociada.
        - Si es 'STOCK_CORRECTO' (abastecida sin faltantes):
          Se DESCARTA y NO se guarda en /historica.
        """
        arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError(f"No se pudo decodificar la imagen {original_filename}")

        # Inferencia con YOLOv8
        from backend.app.services.detection_service import detection_service
        det_result = detection_service.model_mgr.predict(frame)

        # Clasificación basada en evidencia visual
        missing_dets, product_dets, is_empty_shelf, is_totally_empty, stock_status, debug_info = self._filter_shelf_detections(
            det_result.detections,
            frame.shape[:2],
            camera_id="CAM-01",
            shelf_id="A-01",
            filename=original_filename
        )

        if stock_status == "SIN_STOCK":
            # Góndola completamente vacía -> SIN STOCK
            missing_count = max(len(missing_dets), 1)
            product_count = 0
            expected_count = missing_count
            remaining_count = 0
            missing_pct = 100.0
            remaining_pct = 0.0
            sev = SeverityInfo(
                severity="CRITICAL",
                status="Sin Stock",
                action="Reposición total",
                message="Alerta Crítica: Góndola completamente vacía (Sin Stock). Atención urgente."
            )
        elif stock_status == "FALTA_PRODUCTO":
            missing_count = len(missing_dets)
            product_count = len(product_dets)
            expected_count = missing_count + product_count
            remaining_count = product_count
            missing_pct = round((missing_count / expected_count) * 100, 2) if expected_count > 0 else 100.0
            remaining_pct = round((remaining_count / expected_count) * 100, 2) if expected_count > 0 else 0.0
            sev = compute_severity(missing_pct, display_name="Pasillo")
        else:
            # STOCK_CORRECTO -> descartar de /historica
            missing_count = 0
            product_count = len(product_dets)
            expected_count = product_count
            remaining_count = product_count
            missing_pct = 0.0
            remaining_pct = 100.0
            logger.info(f"Imagen '{original_filename}' analizada: Stock correcto / Sin faltantes (descartada de /historica).")
            return ImageAnalysisDetail(
                filename=original_filename,
                saved_to_historica=False,
                missing_count=0,
                product_count=product_count,
                expected_count=expected_count,
                missing_percentage=0.0,
                severity=None,
                message="Descartada: Stock correcto. No se almacena en /historica."
            )

        missing_pct = max(0.0, min(100.0, missing_pct))
        remaining_pct = max(0.0, min(100.0, remaining_pct))

        # Guardar en /historica para estados con fallas (SIN_STOCK o FALTA_PRODUCTO)
        with self._lock:
            clean_stem = re.sub(r'[^a-zA-Z0-9_-]', '_', Path(original_filename).stem)
            ext = Path(original_filename).suffix.lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
                ext = ".jpg"
            safe_filename = f"{clean_stem}_{int(time.time() * 1000)}{ext}"
            save_path = _HISTORICA_DIR / safe_filename
            cv2.imwrite(str(save_path), frame)

            meta = {
                "filename": safe_filename,
                "original_name": original_filename,
                "uploaded_at": self._now_iso(),
                "missing_count": missing_count,
                "product_count": product_count,
                "expected_count": expected_count,
                "remaining_count": remaining_count,
                "missing_percentage": missing_pct,
                "remaining_percentage": remaining_pct,
                "severity": sev.severity,
                "status": sev.status,
                "action": sev.action,
                "alert_sent": False,
                "stock_status": stock_status,
                "debug_info": debug_info
            }
            meta_path = _HISTORICA_DIR / f"{safe_filename}.meta.json"
            try:
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2)
            except Exception as e:
                logger.error(f"Error guardando metadata para {safe_filename}: {e}")

            status_label = {"SIN_STOCK": "Sin Stock", "FALTA_PRODUCTO": "Falta Producto"}.get(stock_status, "Falla")
            logger.info(
                f"Falla detectada en '{original_filename}': {missing_count} faltantes ({missing_pct}%). "
                f"Estado: {status_label}. Guardada en /historica como '{safe_filename}'."
            )

            return ImageAnalysisDetail(
                filename=safe_filename,
                saved_to_historica=True,
                missing_count=missing_count,
                product_count=product_count,
                expected_count=expected_count,
                missing_percentage=missing_pct,
                severity=sev.severity,
                message=f"{status_label}: {missing_count} faltantes ({missing_pct}%). Guardada en /historica."
            )

    def _analyze_file_on_disk(self, img_path: Path) -> dict:
        """Helper para generar metadata aplicando filtrado estricto y protección de góndola vacía."""
        frame = cv2.imread(str(img_path))
        if frame is None:
            return {
                "filename": img_path.name,
                "original_name": img_path.name,
                "uploaded_at": self._now_iso(),
                "missing_count": 1,
                "product_count": 0,
                "expected_count": 1,
                "remaining_count": 0,
                "missing_percentage": 100.0,
                "remaining_percentage": 0.0,
                "severity": "CRITICAL",
                "status": "Sin Stock",
                "action": "Reposición total",
                "alert_sent": False,
                "stock_status": "SIN_STOCK",
                "debug_info": {
                    "camera_id": "CAM-01",
                    "shelf_id": "GND-01",
                    "filename": img_path.name,
                    "detections_count": 0,
                    "valid_detections_count": 0,
                    "valid_products_count": 0,
                    "valid_missing_count": 0,
                    "confidence_scores": [],
                    "average_confidence": 0.0,
                    "estimated_occupancy": "0.0%",
                    "final_stock_status": "SIN_STOCK"
                }
            }

        from backend.app.services.detection_service import detection_service
        det_result = detection_service.model_mgr.predict(frame)

        missing_dets, product_dets, is_empty_shelf, is_totally_empty, stock_status, debug_info = self._filter_shelf_detections(
            det_result.detections,
            frame.shape[:2],
            camera_id="CAM-01",
            shelf_id="GND-01",
            filename=img_path.name
        )

        if stock_status == "SIN_STOCK":
            m_count = max(len(missing_dets), 1)
            p_count = 0
            exp_count = m_count
            m_pct = 100.0
            rem_pct = 0.0
            sev = SeverityInfo(
                severity="CRITICAL",
                status="Sin Stock",
                action="Reposición total",
                message="Alerta Crítica: Góndola completamente vacía (Sin Stock). Atención urgente."
            )
        elif stock_status == "FALTA_PRODUCTO":
            m_count = len(missing_dets)
            p_count = len(product_dets)
            exp_count = m_count + p_count
            m_pct = round((m_count / exp_count) * 100, 2) if exp_count > 0 else 100.0
            rem_pct = round((p_count / exp_count) * 100, 2) if exp_count > 0 else 0.0
            sev = compute_severity(m_pct, "Pasillo")
        else:
            m_count = 0
            p_count = len(product_dets)
            exp_count = p_count
            m_pct = 0.0
            rem_pct = 100.0
            sev = compute_severity(0.0, "Pasillo")

        return {
            "filename": img_path.name,
            "original_name": img_path.name,
            "uploaded_at": self._now_iso(),
            "missing_count": m_count,
            "product_count": p_count,
            "expected_count": exp_count,
            "remaining_count": p_count,
            "missing_percentage": m_pct,
            "remaining_percentage": rem_pct,
            "severity": sev.severity,
            "status": sev.status,
            "action": sev.action,
            "alert_sent": False,
            "stock_status": stock_status,
            "debug_info": debug_info
        }


    def _find_image_path(self, filename: str) -> Optional[Path]:
        """Localiza un archivo de imagen en /historica o en las carpetas de dataset/entrenamiento."""
        for folder in [_HISTORICA_DIR, _APPROVED_DIR, _PENDING_DIR]:
            cand = folder / filename
            if cand.exists() and cand.is_file():
                return cand
        return None

    def get_historica_dashboard(self) -> DashboardSummary:
        """
        Dashboard Condicional alimentado por:
        1. Carpeta de análisis habitual (/historica)
        2. Carpetas de entrenamiento / dataset (data/approved, data/pending_review)

        Reglas:
        - El modelo YOLOv8 procesa las imágenes buscando la clase 'missing' (faltantes).
        - Filtro estricto: Solo se incluyen imágenes con fallas detectadas (missing_count > 0).
        - Las imágenes sin faltantes se descartan automáticamente.
        - Asignación dinámica: Alerta 1, Alerta 2, ... y Pasillo 1, Pasillo 2, ...
        - Calcula estadísticas analíticas completas para el gráfico interactivo.
        """
        with self._lock:
            valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
            
            # Recolectar archivos de todas las fuentes configuradas
            candidate_files: List[Path] = []
            source_folders = [_HISTORICA_DIR, _APPROVED_DIR, _PENDING_DIR]
            
            seen_names = set()
            for folder in source_folders:
                if folder.exists():
                    for p in folder.iterdir():
                        if p.is_file() and p.suffix.lower() in valid_exts and not p.name.endswith(".meta.json"):
                            if p.name not in seen_names:
                                seen_names.add(p.name)
                                candidate_files.append(p)

            if not candidate_files:
                return DashboardSummary(
                    is_active=False,
                    message="Dashboard Inactivo: No hay imágenes disponibles en /historica ni en las carpetas de entrenamiento.",
                    total_aisles=0,
                    aisles_critical=0,
                    aisles_moderate=0,
                    aisles_low=0,
                    aisles_ok=0,
                    total_missing=0,
                    total_spaces=0,
                    overall_missing_pct=0.0,
                    active_incidents=0,
                    aisles=[],
                    analytics=StockAnalyticsSummary(
                        total_active_alerts=0,
                        average_depletion_pct=0.0,
                        urgent_count=0,
                        quick_attention_count=0,
                        emptying_count=0,
                        categories=[]
                    )
                )

            # Ordenar archivos para asignación estable
            candidate_files.sort(key=lambda p: (p.stat().st_ctime, p.name))

            # Filtrar y analizar imágenes reteniendo ÚNICAMENTE aquellas con fallas (missing_count > 0)
            fault_entries: List[Tuple[Path, dict]] = []

            for img_path in candidate_files:
                meta_path = img_path.parent / f"{img_path.name}.meta.json"
                meta = None
                if meta_path.exists():
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                    except Exception:
                        meta = None

                # Re-analizar si no tiene stock_status o si es metadata antigua sin debug_info
                if not meta or "stock_status" not in meta or "debug_info" not in meta:
                    meta = self._analyze_file_on_disk(img_path)
                    try:
                        with open(meta_path, "w", encoding="utf-8") as f:
                            json.dump(meta, f, indent=2)
                    except Exception:
                        pass

                # Descartar si fue resuelta explícitamente
                if meta.get("resolved", False):
                    continue

                # LÓGICA DE FILTRADO: Retener imágenes con fallas (SIN_STOCK o FALTA_PRODUCTO)
                stock_st = meta.get("stock_status", "FALTA_PRODUCTO")
                if stock_st in ["SIN_STOCK", "FALTA_PRODUCTO"] or meta.get("missing_count", 0) > 0:
                    fault_entries.append((img_path, meta))

            if not fault_entries:
                return DashboardSummary(
                    is_active=False,
                    message="Dashboard Inactivo: No se detectaron fallas de stock en las imágenes analizadas.",
                    total_aisles=0,
                    aisles_critical=0,
                    aisles_moderate=0,
                    aisles_low=0,
                    aisles_ok=0,
                    total_missing=0,
                    total_spaces=0,
                    overall_missing_pct=0.0,
                    active_incidents=0,
                    aisles=[],
                    analytics=StockAnalyticsSummary(
                        total_active_alerts=0,
                        average_depletion_pct=0.0,
                        urgent_count=0,
                        quick_attention_count=0,
                        emptying_count=0,
                        categories=[]
                    )
                )

            aisles: List[AisleStatus] = []
            total_missing = 0
            total_spaces = 0
            aisles_critical = 0
            aisles_moderate = 0
            aisles_low = 0

            # Contadores para las 3 categorías requeridas en el gráfico
            # 🔴 Urgente (0% - 10% Stock)
            # 🟡 Atención Rápida (10% - 15% Stock)
            # 🟠 Góndola Vaciándose (15% - 20% Stock)
            urgent_count = 0
            quick_attention_count = 0
            emptying_count = 0

            for idx, (img_path, meta) in enumerate(fault_entries, start=1):
                alert_title = f"Alerta {idx}"
                aisle_label = f"Pasillo {idx}"

                stock = StockMetrics(
                    expected_count=meta["expected_count"],
                    missing_count=meta["missing_count"],
                    remaining_count=meta["remaining_count"],
                    missing_percentage=meta["missing_percentage"],
                    remaining_percentage=meta["remaining_percentage"]
                )

                remaining_pct = stock.remaining_percentage

                # Clasificación de categorías para el gráfico analítico
                if remaining_pct <= 10.0:
                    urgent_count += 1
                elif remaining_pct <= 15.0:
                    quick_attention_count += 1
                else:
                    emptying_count += 1

                sev = compute_severity(stock.missing_percentage, aisle_label)

                # Determinar stock_status y debug_info desde metadata guardada
                stock_status = meta.get("stock_status", "FALTA_PRODUCTO")
                debug_info = meta.get("debug_info", None)

                aisle = AisleStatus(
                    location_id=f"GND-{idx:03d}",
                    display_order=idx,
                    display_name=alert_title,  # Título Principal: Alerta 1, Alerta 2...
                    aisle_name=aisle_label,    # Sub-etiqueta: Pasillo 1, Pasillo 2...
                    filename=img_path.name,
                    image_url=f"/api/stock/historica/image/{img_path.name}",
                    stock=stock,
                    severity_info=sev,
                    stock_status=stock_status,
                    debug_info=debug_info,
                    active_incident_id=f"INC-{img_path.stem}",
                    has_active_incident=True,
                    last_detected_at=meta.get("uploaded_at"),
                    alert_sent=meta.get("alert_sent", False)
                )
                aisles.append(aisle)

                total_missing += stock.missing_count
                total_spaces += stock.expected_count

                if sev.severity == "CRITICAL":
                    aisles_critical += 1
                elif sev.severity == "MODERATE":
                    aisles_moderate += 1
                else:
                    aisles_low += 1

            total_alerts = len(aisles)
            overall_missing_pct = (
                round((total_missing / total_spaces) * 100, 2)
                if total_spaces > 0 else 0.0
            )

            # Promedio global de desabastecimiento detectado
            avg_depletion = (
                round(sum(a.stock.missing_percentage for a in aisles) / total_alerts, 2)
                if total_alerts > 0 else 0.0
            )

            # Categorías estructuradas para el componente de gráfico
            chart_categories = [
                StockChartCategory(
                    key="urgent",
                    name="Urgente",
                    label="🔴 Urgente (0% - 10% Stock)",
                    range_label="0% - 10% Stock",
                    count=urgent_count,
                    color="#ef4444",
                    percentage=round((urgent_count / total_alerts) * 100, 1) if total_alerts > 0 else 0.0
                ),
                StockChartCategory(
                    key="quick_attention",
                    name="Atención Rápida",
                    label="🟡 Atención Rápida (10% - 15% Stock)",
                    range_label="10% - 15% Stock",
                    count=quick_attention_count,
                    color="#eab308",
                    percentage=round((quick_attention_count / total_alerts) * 100, 1) if total_alerts > 0 else 0.0
                ),
                StockChartCategory(
                    key="emptying",
                    name="Góndola Vaciándose",
                    label="🟠 Góndola Vaciándose (15% - 20% Stock)",
                    range_label="15% - 20% Stock",
                    count=emptying_count,
                    color="#f97316",
                    percentage=round((emptying_count / total_alerts) * 100, 1) if total_alerts > 0 else 0.0
                )
            ]

            analytics = StockAnalyticsSummary(
                total_active_alerts=total_alerts,
                average_depletion_pct=avg_depletion,
                urgent_count=urgent_count,
                quick_attention_count=quick_attention_count,
                emptying_count=emptying_count,
                categories=chart_categories
            )

            return DashboardSummary(
                is_active=True,
                message=f"Dashboard Activo: Monitoreando {total_alerts} pasillo(s) con faltantes detectados.",
                total_aisles=total_alerts,
                aisles_critical=aisles_critical,
                aisles_moderate=aisles_moderate,
                aisles_low=aisles_low,
                aisles_ok=0,
                total_missing=total_missing,
                total_spaces=total_spaces,
                overall_missing_pct=overall_missing_pct,
                active_incidents=total_alerts,
                aisles=aisles,
                analytics=analytics
            )

    def resolve_historica_image(self, filename: str) -> dict:
        """
        Resuelve la falla eliminando la imagen o marcándola como resuelta.
        Los pasillos restantes se reordenan automáticamente:
        si se elimina Pasillo 1, Pasillo 2 pasa automáticamente a ser Pasillo 1.
        """
        with self._lock:
            img_path = self._find_image_path(filename)
            if not img_path:
                raise ValueError(f"La imagen '{filename}' no fue encontrada en las fuentes activas.")

            # Si está en /historica, se elimina físicamente
            if _HISTORICA_DIR in img_path.parents or img_path.parent == _HISTORICA_DIR:
                img_path.unlink(missing_ok=True)
                meta_path = _HISTORICA_DIR / f"{filename}.meta.json"
                if meta_path.exists():
                    meta_path.unlink(missing_ok=True)
            else:
                # Si está en dataset de entrenamiento, marcamos resolved: True en su metadata para no perder el original
                meta_path = img_path.parent / f"{filename}.meta.json"
                meta = {}
                if meta_path.exists():
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                    except Exception:
                        pass
                meta["resolved"] = True
                meta["resolved_at"] = self._now_iso()
                try:
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(meta, f, indent=2)
                except Exception as e:
                    logger.error(f"Error actualizando metadata de resolución para {filename}: {e}")

            logger.info(f"Falla resuelta para '{filename}'. Pasillos reordenados automáticamente.")

            new_dashboard = self.get_historica_dashboard()
            return {
                "success": True,
                "message": f"Falla resuelta para '{filename}'. Pasillos reordenados automáticamente.",
                "dashboard": new_dashboard
            }

    def send_historica_alert(self, filename: str, channel: str = "webhook") -> ReplenishmentAlertRecord:
        """Envía alerta de reposición para un pasillo basado en su imagen."""
        with self._lock:
            img_path = self._find_image_path(filename)
            if not img_path:
                raise ValueError(f"La imagen '{filename}' no fue encontrada en las fuentes activas.")

            meta_path = img_path.parent / f"{filename}.meta.json"
            meta = None
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                except Exception:
                    pass

            if not meta:
                meta = self._analyze_file_on_disk(img_path)

            if meta.get("alert_sent"):
                raise ValueError(f"Ya se ha enviado una alerta de reposición para esta imagen ({filename}).")

            # Determinar el nombre visual actual (Pasillo N) según orden en la carpeta
            dash = self.get_historica_dashboard()
            current_aisle = next((a for a in dash.aisles if a.filename == filename), None)
            display_name = current_aisle.display_name if current_aisle else "Pasillo"
            location_id = current_aisle.location_id if current_aisle else "GND-001"

            sev = compute_severity(meta["missing_percentage"], display_name)

            payload = {
                "event": "stock_replenishment_alert",
                "timestamp": self._now_iso(),
                "location": {
                    "location_id": location_id,
                    "display_name": display_name
                },
                "stock": {
                    "expected_count": meta["expected_count"],
                    "missing_count": meta["missing_count"],
                    "remaining_count": meta["remaining_count"],
                    "missing_percentage": meta["missing_percentage"],
                    "remaining_percentage": meta["remaining_percentage"]
                },
                "alert": {
                    "severity": sev.severity,
                    "status": sev.status,
                    "action": sev.action,
                    "message": sev.message
                },
                "source": {
                    "detection_model": "YOLOv8",
                    "image_file": filename
                }
            }

            rec_id = str(uuid.uuid4())[:8].upper()
            now_iso = self._now_iso()
            status: str = "pending"
            error_msg: Optional[str] = None

            if channel == "webhook":
                webhook_url = settings.alerts.webhook_url
                if webhook_url:
                    try:
                        resp = requests.post(webhook_url, json=payload, timeout=5.0)
                        resp.raise_for_status()
                        status = "sent"
                        logger.info(f"Alerta de reposición enviada por webhook para {filename}.")
                    except Exception as e:
                        status = "failed"
                        error_msg = str(e)
                else:
                    status = "sent"
                    logger.info(f"Alerta de reposición registrada internamente para {filename}.")
            else:
                status = "sent"

            rec = ReplenishmentAlertRecord(
                id=rec_id,
                incident_id=f"INC-{img_path.stem}",
                channel=channel,
                payload=payload,
                status=status,
                sent_at=now_iso if status == "sent" else None,
                error_message=error_msg
            )

            # Actualizar meta
            meta["alert_sent"] = True
            meta["alert_sent_at"] = now_iso
            try:
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2)
            except Exception as e:
                logger.error(f"Error actualizando metadata de alerta: {e}")

            self._alert_records.append(rec)
            self._append_alert_record(rec)
            return rec


# Singleton
incident_service = IncidentService()

