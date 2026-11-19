# Plan de Pruebas — Computer Vision Walmart (CVW)

> **Fuentes:** pruebas del repositorio (`backend/tests/`, `test_all_scenarios.py`, `test_historica_flow.py`, `tools/image_sender_test.py`), requisitos no funcionales del ERS v4, evaluación del modelo YOLOv8s v2 (notebook de entrenamiento e Informe Intermedio de Avance) y Definition of Done.

## 1. Objetivo

Verificar que cada componente del sistema funcione según los requisitos del ERS y que el modelo de detección tenga un desempeño medible y reproducible, antes de integrar cambios a la rama `main`.

## 2. Alcance

| Incluye | No incluye (por ahora) |
|---|---|
| Lógica de inventario, semáforo, alertas, incidencias, dataset e ingesta de imágenes | Pruebas con cámaras reales de tienda (no hay acceso a CCTV) |
| Evaluación del modelo con métricas estándar y análisis por imagen | Pruebas de carga con muchas cámaras simultáneas |
| Flujo de la API con imágenes de prueba | Pruebas de interfaz automatizadas del frontend |

## 3. Tipos de prueba

| Tipo | Qué se prueba | Herramienta | Dónde está |
|---|---|---|---|
| Unitarias | Funciones aisladas del backend | pytest | `backend/tests/` |
| Integración | Varios servicios trabajando juntos (incidencias, severidad, alertas) | pytest / unittest | `test_all_scenarios.py` |
| Flujo de API (sistema) | Endpoints de `/api/stock` con el servidor corriendo | requests | `test_historica_flow.py` |
| Evaluación del modelo | Precisión, Recall, mAP50 y mAP50-95 por clase | Ultralytics (Google Colab) | Notebook `Proyecto_CVW_modelo_v2.ipynb` |
| Robustez | Desempeño con imágenes degradadas tipo cámara (compresión, baja resolución, ruido, sombras, escala de grises) | Albumentations + Ultralytics | Particiones `valid_cam` y `test_cam` del notebook |
| Rendimiento | Tiempo de inferencia por imagen (RNF-01: < 5 s) y latencia API punta a punta | pytest / script benchmark | `backend/tests/test_performance.py`, `tools/benchmark_inference.py` |
| Seguridad | Ausencia de secretos y credenciales (RNF-05), `.env` fuera de git, hallazgo CORS, path traversal y resiliencia ante archivos anómalos | pytest, bandit, pip-audit | `backend/tests/test_security.py`, `tools/security_audit.sh` |
| Manual / exploratoria | Envío periódico de imágenes desde una carpeta al sistema | Cliente de escritorio | `tools/image_sender_test.py` |

## 4. Casos de prueba automatizados

### 4.1 Unitarias (`backend/tests/`)

| ID | Archivo | Caso | Requisito |
|---|---|---|---|
| PU-01 | `test_inventory_service.py` | Con 0 detecciones no hay división por cero | RF-08 |
| PU-02 | `test_inventory_service.py` | Cálculo correcto de ocupación y vacío con detecciones mixtas | RF-08 |
| PU-03 | `test_inventory_service.py` | Caso de 80 % o más de vacío | RF-09 / RF-11 |
| PU-04 | `test_inventory_service.py` | El filtro por región de interés (ROI) excluye detecciones fuera del área | RF-08 |
| PU-05 | `test_alert_service.py` | Una sola imagen sobre el umbral no dispara alerta de inmediato | RF-11 |
| PU-06 | `test_alert_service.py` | La alerta se dispara si la condición se mantiene 3 segundos | RF-11 |
| PU-07 | `test_alert_service.py` | El tiempo de espera (cooldown) evita alertas repetidas | RF-11 |
| PU-08 | `test_alert_service.py` | Con 0 espacios no se calcula alerta ni se produce error | RNF-06 |
| PU-09 | `test_dataset_service.py` | Ciclo de una muestra: captura → revisión → aprobación | Active learning |
| PU-10 | `test_image_ingestion_service.py` | Los lotes recientes se listan del más nuevo al más antiguo y con límite | RF-07 |
| PU-11 a PU-13 | `test_model_manager.py` | Clases del modelo, actualización de umbrales y listado de versiones | RF-12 |
| PU-14 a PU-20 | `test_semaforo.py` | Clasificación Verde / Amarillo / Rojo / Sin datos, casos límite y su integración con inventario | RF-09 |
| PU-21 a PU-22 | `test_performance.py` | Cumplimiento RNF-01 (< 5 s) en inferencia YOLOv8s y latencia punta a punta API | RNF-01 |
| PU-23 a PU-36 | `test_security.py` | Bloqueo de path traversal, subida de archivos anómalos, .env fuera de git, ausencia de secretos y hallazgo CORS | RNF-05 |

### 4.2 Integración (`test_all_scenarios.py`)

| ID | Caso |
|---|---|
| PI-01 | Imagen sin faltantes → no se crea incidencia ni se guarda la imagen |
| PI-02 | Imagen con faltantes → se crea o actualiza la incidencia con métricas y severidad |
| PI-03 | Varias imágenes seguidas con el mismo faltante → no se duplican incidencias |
| PI-04 | Al resolver un pasillo, el orden visual se reasigna y el histórico queda intacto |
| PI-05 | 25 % de faltantes → severidad CRITICAL |
| PI-06 | 15 % de faltantes → severidad MODERATE |
| PI-07 | 5 % de faltantes → severidad LOW |
| PI-08 | Envío de alerta → queda registrado y se evita el envío duplicado |

### 4.3 Flujo de API (`test_historica_flow.py`)

Automatizado con fixture para arranque y apagado del servidor (`python run.py`) y aislamiento de `/historica`. Verifica que el dashboard inicie inactivo, que una imagen de góndola correcta se descarte y que las imágenes con faltantes activen el dashboard, se resuelvan y se reordenen dinámicamente.

## 5. Evaluación del modelo (YOLOv8s v2)

Partición de prueba de 53 imágenes no vistas en el entrenamiento, más su copia degradada tipo cámara (`test_cam`). Umbral de confianza recomendado: 0,38.

| Métrica | Test | Test cámara |
|---|---|---|
| Precisión | 69,2 % | 63,5 % |
| Recall | 62,9 % | 56,8 % |
| mAP50 | 63,3 % | 58,2 % |
| mAP50-95 | 33,6 % | 28,1 % |
| Recall clase missing (vacío) | 47,9 % | 43,7 % |
| Recall clase product | 77,9 % | 70,0 % |

Además se analizaron por imagen los **10 mejores y 10 peores casos** de `test_cam` (emparejamiento uno a uno por clase con IoU ≥ 0,5). Ver el Informe Intermedio de Avance.

**Rendimiento:** inferencia real con el modelo de producción activo YOLOv8s medida sobre 20 imágenes del repositorio: mediana de 36,82 ms, p95 de 82,78 ms y máximo de 91,61 ms en GPU NVIDIA GeForce RTX 3060 Laptop (y ~176,50 ms punta a punta en la API), cumpliendo holgadamente el límite de 5 s del RNF-01 (el valor preliminar de 8,7 ms del ERS 11.4 correspondía a YOLOv8n en Colab T4).

## 6. Resultados de la última ejecución

| Conjunto | Resultado | Fecha | Observación |
|---|---|---|---|
| `backend/tests/` completo (con `test_model_manager.py`, `test_semaforo.py`, `test_security.py` y `test_performance.py`) | **36 de 36 aprobadas** | 18/11/2026 | Rama `fix/tests-docker` |
| `test_all_scenarios.py` | **8 de 8 aprobadas** | 18/11/2026 | Rama `fix/tests-docker` |
| `test_historica_flow.py` | **5 de 5 etapas aprobadas** | 18/11/2026 | Automatizado con fixture y gestión de servidor |
| Benchmark YOLOv8s (`tools/benchmark_inference.py`) | **Aprobado (p50: 36,8 ms, max: 91,6 ms)** | 18/11/2026 | GPU NVIDIA RTX 3060 Laptop; cumple RNF-01 |
| Auditoría Bandit (`tools/security_audit.sh`) | **0 vulnerabilidades altas** | 18/11/2026 | B104 (bind 0.0.0.0 esperado por Docker), B110 bajos |
| Auditoría pip-audit (`tools/security_audit.sh`) | **0 vulnerabilidades conocidas** | 18/11/2026 | Auditado contra requirements.txt |

## 7. Cómo ejecutar las pruebas

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Pruebas unitarias y de backend (incluye seguridad y rendimiento)
python -m pytest backend/tests -v

# Solo rendimiento
python -m pytest -m performance -v

# Pruebas de integración de negocio
python -m pytest test_all_scenarios.py -v

# Flujo de API de punta a punta (arranca y detiene el servidor automáticamente):
python test_historica_flow.py

# Auditorías de seguridad estática y dependencias
bash tools/security_audit.sh
```

## 8. Criterios de aceptación

- Todas las pruebas automatizadas pasan antes de mezclar un Pull Request a `main` (ver `Definition_of_Done.md`).
- Inferencia menor a 5 s por imagen (RNF-01).
- El evaluador del sistema marca un modelo candidato como aprobado si su mAP50 de validación es al menos 0,80 (`eval_pass_map50` en la configuración). Según el ERS, además debe igualar o superar la línea base anterior (RNF-02).
- Sin credenciales en el código (RNF-05).

## 9. Pendientes

- Probar con imágenes reales de cámaras de tienda cuando estén disponibles.
- Agregar pruebas de interfaz del frontend (Cypress o Playwright).
- Corregir hallazgo de seguridad S-10 en despliegue (restringir CORS a orígenes específicos del cliente en lugar de comodín con credenciales).
