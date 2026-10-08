"""API Router para stock, carga de imágenes a /historica y Dashboard condicional."""
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse

from backend.app.services.incident_service import incident_service, _HISTORICA_DIR
from backend.app.schemas.incident import (
    DashboardSummary, Incident, IncidentSummary, Location,
    LocationCreate, LocationUpdate, ReplenishmentAlertRecord,
    ReplenishmentAlertRequest, UploadAnalysisResponse, ImageAnalysisDetail
)
from backend.app.core.config import BASE_DIR

router = APIRouter(tags=["Stock & Incidents"])


# ---------------------------------------------------------------------------
# 1. Carga de Imágenes (Zona de Análisis)
# ---------------------------------------------------------------------------

@router.post("/api/stock/upload", response_model=UploadAnalysisResponse)
async def upload_and_analyze_images(files: List[UploadFile] = File(...)):
    """
    Zona de Análisis: recibe una o varias imágenes para inferencia con YOLOv8.
    REGLA:
    - Las imágenes con faltantes (clase 'missing') se guardan en /historica.
    - Las imágenes sin faltantes se descartan y NO se guardan en /historica.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No se enviaron archivos para analizar.")

    results: List[ImageAnalysisDetail] = []
    faults_count = 0
    discarded_count = 0

    for file in files:
        try:
            content = await file.read()
            analysis = incident_service.process_and_filter_upload(
                original_filename=file.filename or "imagen.jpg",
                image_bytes=content
            )
            results.append(analysis)
            if analysis.saved_to_historica:
                faults_count += 1
            else:
                discarded_count += 1
        except Exception as e:
            results.append(ImageAnalysisDetail(
                filename=file.filename or "desconocido",
                saved_to_historica=False,
                missing_count=0,
                product_count=0,
                expected_count=0,
                missing_percentage=0.0,
                severity=None,
                message=f"Error al procesar: {str(e)}"
            ))

    current_dash = incident_service.get_historica_dashboard()

    return UploadAnalysisResponse(
        total_analyzed=len(files),
        faults_detected=faults_count,
        discarded_clean=discarded_count,
        results=results,
        dashboard_active=current_dash.is_active
    )


# ---------------------------------------------------------------------------
# 2. Dashboard Condicional (alimentado por /historica)
# ---------------------------------------------------------------------------

@router.get("/api/stock/dashboard", response_model=DashboardSummary)
def get_stock_dashboard():
    """
    Retorna el estado del Dashboard basado estrictamente en las imágenes
    defectuosas almacenadas en /historica:
    - Inactivo si /historica está vacía.
    - Activo con numeración Pasillo 1, Pasillo 2... si hay imágenes con fallas.
    """
    return incident_service.get_historica_dashboard()


# ---------------------------------------------------------------------------
# 3. Resolución y Reordenamiento de Pasillos (/historica)
# ---------------------------------------------------------------------------

@router.delete("/api/stock/historica/{filename}")
@router.post("/api/stock/historica/{filename}/resolve")
def resolve_historica_file(filename: str):
    """
    Resuelve la falla eliminando la imagen de /historica.
    Los pasillos restantes se reordenan automáticamente:
    si se elimina Pasillo 1, Pasillo 2 pasa automáticamente a ser Pasillo 1.
    """
    try:
        res = incident_service.resolve_historica_image(filename)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al resolver falla: {e}")


@router.get("/api/stock/historica/image/{filename}")
def get_historica_image(filename: str):
    """Retorna la imagen física de la falla almacenada en /historica o en las carpetas de dataset/entrenamiento."""
    file_path = incident_service._find_image_path(filename)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Imagen no encontrada en las fuentes activas.")
    suffix = file_path.suffix.lower()
    media_type = "image/png" if suffix == ".png" else "image/jpeg"
    return FileResponse(file_path, media_type=media_type)


@router.post("/api/stock/historica/{filename}/alert", response_model=ReplenishmentAlertRecord)
def send_historica_alert(filename: str, body: ReplenishmentAlertRequest):
    """Envía alerta de reposición para el pasillo correspondiente a la imagen en /historica."""
    try:
        rec = incident_service.send_historica_alert(filename, channel=body.channel)
        return rec
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar alerta: {e}")


# ---------------------------------------------------------------------------
# 4. Compatibilidad con endpoints de locations y alertas
# ---------------------------------------------------------------------------

@router.get("/api/locations", response_model=List[Location])
@router.get("/api/stock/locations", response_model=List[Location], include_in_schema=False)
def get_locations(active_only: bool = True):
    return incident_service.get_locations(active_only=active_only)


@router.get("/api/locations/{location_id}", response_model=Location)
@router.get("/api/stock/locations/{location_id}", response_model=Location, include_in_schema=False)
def get_location(location_id: str):
    loc = incident_service.get_location(location_id)
    if not loc:
        raise HTTPException(status_code=404, detail=f"Ubicación '{location_id}' no encontrada.")
    return loc


@router.post("/api/locations", response_model=Location, status_code=201)
@router.post("/api/stock/locations", response_model=Location, status_code=201, include_in_schema=False)
def create_location(body: LocationCreate):
    existing = incident_service.get_location(body.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Ubicación '{body.id}' ya existe.")
    return incident_service.create_location(body.id, body.name)


@router.get("/api/incidents", response_model=List[IncidentSummary])
@router.get("/api/stock/incidents", response_model=List[IncidentSummary], include_in_schema=False)
def get_incidents(
    status: Optional[str] = Query(default=None),
    location_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500)
):
    return incident_service.get_incidents(status_filter=status, location_id=location_id, limit=limit)


@router.patch("/api/incidents/{incident_id}/resolve", response_model=Incident)
@router.patch("/api/stock/incidents/{incident_id}/resolve", response_model=Incident, include_in_schema=False)
def resolve_incident(incident_id: str):
    resolved = incident_service.resolve_incident(incident_id)
    if not resolved:
        raise HTTPException(status_code=404, detail=f"Incidencia '{incident_id}' no encontrada.")
    return resolved


@router.post("/api/incidents/{incident_id}/alert", response_model=ReplenishmentAlertRecord)
@router.post("/api/stock/incidents/{incident_id}/alert", response_model=ReplenishmentAlertRecord, include_in_schema=False)
def send_replenishment_alert(incident_id: str, body: ReplenishmentAlertRequest):
    try:
        rec = incident_service.send_replenishment_alert(incident_id, channel=body.channel)
        return rec
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar alerta: {e}")
