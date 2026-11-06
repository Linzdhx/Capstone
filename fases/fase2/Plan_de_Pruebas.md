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
| Rendimiento | Tiempo de inferencia por imagen (RNF-01: < 5 s) | Ultralytics | Notebook / ERS 11.4 |
| Seguridad | Que no haya credenciales en el código (RNF-05) ni acceso a cámaras o red corporativa (RNF-03) | Revisión manual | Revisión de Pull Requests |
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
| PU-14 a PU-19 | `test_semaforo.py` (PR #1) | Clasificación Verde / Amarillo / Rojo / Sin datos y su integración con el inventario | RF-09 |

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

Requiere el servidor corriendo en `http://localhost:8000`. Verifica que el dashboard inicie inactivo, que una imagen sin faltantes se descarte y que las imágenes con faltantes se guarden en `historica/` y activen el dashboard.

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

**Rendimiento:** inferencia de 8,7 ms por imagen en GPU T4 con YOLOv8n (ERS 11.4), muy por debajo del límite de 5 s del RNF-01.

## 6. Resultados de la última ejecución

| Conjunto | Resultado | Fecha | Observación |
|---|---|---|---|
| `backend/tests/` (sin `test_model_manager.py`) | **10 de 10 aprobadas** | 06/11/2026 | Rama `main` |
| `test_all_scenarios.py` | **8 de 8 aprobadas** | 06/11/2026 | Rama `main` |
| `test_semaforo.py` + `test_inventory_service.py` | **10 de 10 aprobadas** | 31/10/2026 | Rama `Dsalvatierra` (PR #1) |
| `test_model_manager.py` | No ejecutada en esta corrida | — | Requiere PyTorch y los pesos del modelo instalados |
| `test_historica_flow.py` | No ejecutada en esta corrida | — | Requiere el servidor corriendo |

## 7. Cómo ejecutar las pruebas

```bash
pip install -r requirements.txt
python -m pytest backend/tests -v
python -m pytest test_all_scenarios.py -v
# Con el servidor corriendo (python run.py):
python test_historica_flow.py
```

## 8. Criterios de aceptación

- Todas las pruebas automatizadas pasan antes de mezclar un Pull Request a `main` (ver `Definition_of_Done.md`).
- Inferencia menor a 5 s por imagen (RNF-01).
- El evaluador del sistema marca un modelo candidato como aprobado si su mAP50 de validación es al menos 0,80 (`eval_pass_map50` en la configuración). Según el ERS, además debe igualar o superar la línea base anterior (RNF-02).
- Sin credenciales en el código (RNF-05).

## 9. Pendientes

- Probar con imágenes reales de cámaras de tienda cuando estén disponibles.
- Automatizar `test_historica_flow.py` levantando el servidor dentro de la prueba.
- Ejecutar `test_model_manager.py` en un entorno con PyTorch y registrar el resultado.
- Agregar pruebas de interfaz del frontend.
