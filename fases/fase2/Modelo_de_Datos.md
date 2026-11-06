# Modelo de Datos — Computer Vision Walmart (CVW)

> **Fuentes:** esquemas Pydantic del backend (`backend/app/schemas/`), configuración (`backend/app/core/config.py`) y archivos de datos del repositorio (`data/incidents/`, `alerts/`, `models/`).
> El sistema **no usa una base de datos externa**: tal como se decidió en el Sprint 3, la información se guarda en archivos dentro del propio proyecto (JSON y JSONL).

## 1. Diagrama entidad–relación

```mermaid
erDiagram
    LOCATION ||--o{ INCIDENT : "tiene"
    INCIDENT ||--o{ ALERT_SEND : "genera"
    DETECTION_RESULT ||--|{ DETECTION_ITEM : "contiene"
    DETECTION_RESULT ||--|| INVENTORY_METRICS : "se resume en"
    INVENTORY_METRICS ||--o| ALERT_EVENT : "puede disparar"
    DATASET_ITEM ||--|{ BBOX_ANNOTATION : "tiene"
    MODEL_VERSION ||--o{ DATASET_ITEM : "generó"

    LOCATION {
        string id PK "ej. GND-001"
        string name
        int display_order
        string display_name "ej. Pasillo 1"
        bool is_active
        string created_at
        string updated_at
    }
    INCIDENT {
        string id PK "ej. INC-1771470A"
        string location_id FK
        string image_path
        int missing_count
        int expected_count
        int remaining_count
        float missing_percentage
        string severity "CRITICAL / MODERATE / LOW"
        string status "ACTIVE / RESOLVED"
        float confidence
        string created_at
        string resolved_at
        bool alert_sent
        string alert_channel
    }
    ALERT_SEND {
        string id PK
        string incident_id FK
        string channel "webhook"
        json payload
    }
    ALERT_EVENT {
        string id PK
        string timestamp
        float empty_rate
        float occupancy_rate
        int products
        int missing
        string snapshot_filename
        string message
    }
    DETECTION_RESULT {
        string model_version
        int frame_width
        int frame_height
        json timings "pre / inferencia / post (ms)"
    }
    DETECTION_ITEM {
        int class_id "0 = missing, 1 = product"
        string class_name
        float confidence
        float[] box "x1, y1, x2, y2"
    }
    INVENTORY_METRICS {
        int products
        int missing
        int total_spaces
        float occupancy_rate
        float empty_rate
        bool roi_applied
    }
    DATASET_ITEM {
        string id PK
        string stage "collected / pending_review / approved / rejected / validation"
        string image_path
        string source
        string model_version
        float empty_rate
    }
    BBOX_ANNOTATION {
        int class_id
        string class_name
        float confidence
        float[] box
    }
    MODEL_VERSION {
        string version PK "ej. v001"
        string status "production / candidate / archive"
        string base_model
        float confidence_threshold
        float iou_threshold
        json metrics
        string parent_model
        string path
    }
```

## 2. Dónde se guarda cada entidad

| Entidad | Archivo / carpeta | Formato |
|---|---|---|
| Ubicaciones (pasillos / góndolas) | `data/incidents/locations.json` | JSON (lista) |
| Incidencias de stock | `data/incidents/incidents.jsonl` | JSONL (una línea por incidencia) |
| Envíos de alerta | `data/incidents/alert_sends.jsonl` | JSONL |
| Eventos de alerta del monitoreo en vivo | `alerts/logs/alerts.jsonl` + capturas en `alerts/images/` | JSONL + JPG |
| Imágenes analizadas con faltantes | `historica/` (imagen + `.meta.json`) | JPG + JSON |
| Muestras para reentrenamiento | `data/collected`, `data/pending_review`, `data/approved`, `data/rejected`, `data/validation` | Imágenes + etiquetas |
| Versiones del modelo | `models/production/`, `models/candidates/vNNN/`, `models/archive/` | `best.pt` + `metadata.json` |

## 3. Reglas de negocio asociadas

| Regla | Valor | Dónde |
|---|---|---|
| % de stock visible | `product ÷ (product + missing)` | `inventory_service.py` |
| Alerta del monitoreo en vivo | vacío ≥ 80 % sostenido 3 s; espera de 30 s entre alertas | `config.py` (`AlertsConfig`) |
| Severidad de incidencias | faltantes > 20 % → CRITICAL; > 10 % → MODERATE; resto → LOW | `incident_service.py` |
| Semáforo (Informe Final) | Verde 100–41 %, Amarillo 40–21 %, Rojo 20–0 % de stock visible | `semaforo_service.py` (PR #1) |
| Captura para active learning | confianza < 0,40 o vacío ≥ 70 % | `config.py` (`ActiveLearningConfig`) |
| Mínimo para reentrenar | 5 muestras aprobadas | `config.py` (`TrainingConfig`) |
| Aprobación de un modelo candidato | mAP50 ≥ 0,80 | `config.py` / `evaluator.py` |

> **Nota:** los umbrales de severidad del módulo de incidencias (por % de faltantes) son distintos de los del semáforo del Informe Final (por % de stock visible). Está pendiente unificar ambos criterios.

## 4. Ejemplo de registro (incidencia)

```json
{
  "id": "INC-1771470A",
  "location_id": "GND-TEST-2",
  "missing_count": 1,
  "expected_count": 3,
  "remaining_count": 2,
  "missing_percentage": 33.33,
  "remaining_percentage": 66.67,
  "severity": "CRITICAL",
  "status": "ACTIVE",
  "confidence": 0.88,
  "created_at": "2026-09-25T15:35:13Z",
  "alert_sent": false
}
```
