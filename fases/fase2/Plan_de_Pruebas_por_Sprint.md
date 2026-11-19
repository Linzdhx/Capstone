# Plan de Pruebas por Sprint — Computer Vision Walmart (CVW)

> **Metodología:** Scrum · 5 Sprints · Proyecto Capstone APT (Walmart Chile).  
> **Fuentes de trazabilidad:** `Sprint_Backlog.md`, `Retrospectivas.md`, historial de Git, suite de pruebas automatizadas y evidencias de ejecución en `fases/fase2/evidencias_pruebas/`.

---

## Sprint 1 — Adquisición y preparación de datos

- **Objetivo del sprint:** Obtener un dataset estructurado y balanceado de góndolas de supermercado con particiones limpias para entrenamiento y validación.
- **Ítems del Product Backlog asociados:** PB-01, PB-02, PB-03, PB-04.

| Campo | Detalle |
|---|---|
| **Pruebas del sprint** | Validación visual y cuantitativa del dataset Roboflow Universe v4. Verificación de etiquetas (`product` y `missing`). Detección y mitigación de fuga de datos mediante hashes perceptuales (pHash) para evitar casi-duplicados entre train y valid/test. Verificación de aumentos sintéticos (Albumentations). |
| **Criterio de aceptación** | 349 imágenes base agrupadas sin duplicados; partición estratificada 70/15/15 preservando proporción de cajas `missing`; reproducibilidad estricta con semilla fija (`SEED = 42`). |
| **Resultado** | Aprobado. Particiones generadas: Train (243 originales + 1.352 aumentadas = 1.595 imágenes), Valid (53 limpias), Test (53 limpias), Valid_cam (53 degradadas) y Test_cam (53 degradadas). |
| **Evidencia** | Notebook `fases/fase2/Proyecto_CVW_modelo_v2.ipynb`, documentación en `fases/fase2/Manual_Tecnico.md` (sección 5). |

---

## Sprint 2 — Entrenamiento y prototipado del modelo IA

- **Objetivo del sprint:** Entrenar modelo de detección de objetos en Google Colab con GPU y evaluar métricas cuantitativas estándar por clase.
- **Ítems del Product Backlog asociados:** PB-05, PB-06, PB-07, PB-12.

| Campo | Detalle |
|---|---|
| **Pruebas del sprint** | Evaluación cuantitativa de YOLOv8s tras 100 épocas de entrenamiento en Google Colab (GPU Tesla T4). Medición de Precisión, Recall, mAP50 y mAP50-95 sobre partición limpia de test y partición degradada (`test_cam`). Análisis de los 10 mejores y 10 peores casos con IoU ≥ 0,5. |
| **Criterio de aceptación** | Superar limitaciones de la versión nano (mAP50-95 > 0,30 en test). Inferencia menor a 5 s (RNF-01). Cajas delimitadoras de dos clases (`product` y `missing`). |
| **Resultado** | Aprobado. Test (53 imágenes no vistas): Precisión 69,2 %, Recall 62,9 %, mAP50 63,3 %, mAP50-95 33,6 % (Recall `product` 77,9 %, Recall `missing` 47,9 %). En `test_cam`: mAP50 58,2 %, mAP50-95 28,1 %. |
| **Evidencia** | `fases/fase2/Informe_Tecnico_Evolucion_Modelo_IA.pdf`, `fases/fase3/Dashboard_Metricas_YOLOv8s.html`, notebook `Proyecto_CVW_modelo_v2.ipynb`. |

---

## Sprint 3 — Semáforo operativo y ubicaciones

- **Objetivo del sprint:** Programar y validar la lógica matemática del semáforo operativo de abastecimiento e integrarlo al inventario y a la jerarquía de ubicaciones físicas de tienda.
- **Ítems del Product Backlog asociados:** PB-08, PB-09, PB-10.

| Campo | Detalle |
|---|---|
| **Pruebas del sprint** | Pruebas unitarias de clasificación determinista del semáforo según el porcentaje de stock visible: Verde (100 %–41 %), Amarillo (40 %–21 %), Rojo (20 %–0 %) y "Sin datos" (cuando `total_spaces <= 0`). Pruebas de casos borde (0 %, 20 %, 21 %, 40 %, 41 %, 100 % y lista vacía de detecciones). Integración con `InventoryService.calculate_metrics()`. |
| **Criterio de aceptación** | Clasificación exacta en umbrales límite sin errores de división por cero ni ralentización del cálculo. Integración verificada en el schema `InventoryMetrics`. |
| **Resultado** | Aprobado. 7 de 7 pruebas unitarias de semáforo pasadas en `backend/tests/test_semaforo.py` y 4 de 4 en `backend/tests/test_inventory_service.py` (11 de 11 pasadas). |
| **Evidencia** | `backend/tests/test_semaforo.py`, commit PR #1 (rama `Dsalvatierra`), registro de ejecución en `fases/fase2/evidencias_pruebas/pytest_backend_completo_20261118.txt`. |

---

## Sprint 4 — Modularización en VS Code, API y alertas

- **Objetivo del sprint:** Migrar código del notebook a una arquitectura modular en VS Code con backend FastAPI, servicio de alertas con cooldown y ciclo de vida de modelos.
- **Ítems del Product Backlog asociados:** PB-11, PB-13, PB-14.

| Campo | Detalle |
|---|---|
| **Pruebas del sprint** | Pruebas unitarias de servicios aislados: `AlertService` (filtro temporal de 3 s consecutivos, cooldown de 30 s para evitar spam, protección ante 0 espacios), `DatasetService` (ciclo captura → revisión → aprobación HITL), `ImageIngestionService` (orden y límite de lotes), `ModelManager` (inspección de metadatos, actualización de umbrales en caliente y listado de versiones). |
| **Criterio de aceptación** | Ninguna alerta disparada por un único fotograma aislado; cooldown bloquea duplicados; hot-swap no detiene el servidor; persistencia JSONL correcta. |
| **Resultado** | Aprobado. 11 de 11 pruebas unitarias aprobadas en `test_alert_service.py`, `test_dataset_service.py`, `test_image_ingestion_service.py` y `test_model_manager.py`. |
| **Evidencia** | `fases/fase2/evidencias_pruebas/pytest_backend_completo_20261118.txt`. |

---

## Sprint 5 — Integración y pruebas

- **Objetivo del sprint:** Ejecutar pruebas integrales de punta a punta, validar el flujo de incidencias y el Dashboard condicional, pruebas de seguridad automatizadas y auditoría de rendimiento bajo RNF-01.
- **Ítems del Product Backlog asociados:** PB-15, PB-16, PB-17.

| Campo | Detalle |
|---|---|
| **Pruebas del sprint** | 1. **Integración (`test_all_scenarios.py`):** 8 escenarios de negocio (descarte de imágenes sin faltantes, severidades CRITICAL/MODERATE/LOW, deduplicación de incidencias, resolución y reordenamiento de pasillos, registro de alertas).<br>2. **Flujo de API (`test_historica_flow.py`):** Ciclo completo con servidor FastAPI activo (dashboard inactivo inicial, carga de góndola correcta descartada, activación ante fallas en `/historica`, resolución de pasillos y retorno a estado inactivo).<br>3. **Seguridad (`test_security.py` + Bandit + pip-audit):** Escaneo de secretos en archivos versionados (`git ls-files`), verificación de exclusión de `.env`, revisión de `.env.example`, detección de hallazgo CORS wildcard con credenciales, protección contra path traversal (`..%2F`) y resiliencia ante subida de archivos no imagen, vacíos o corruptos.<br>4. **Rendimiento (`test_performance.py` + `benchmark_inference.py`):** Latencia de inferencia con YOLOv8s real sobre 20 imágenes y latencia API punta a punta bajo criterio RNF-01 (< 5 s). |
| **Criterio de aceptación** | 100 % pruebas de integración aprobadas; servidor arranca y apaga limpiamente con fixture; inferencia máxima < 5000 ms; 0 credenciales versionadas; 0 vulnerabilidades conocidas en dependencias backend. |
| **Resultado** | **Aprobado en su totalidad:**<br>• Integración: **8 de 8 aprobadas** (`test_all_scenarios.py`).<br>• Flujo API: **5 de 5 etapas aprobadas** (`test_historica_flow.py`).<br>• Suite Backend (`pytest backend/tests`): **36 de 36 aprobadas**.<br>• Rendimiento YOLOv8s (GPU RTX 3060): Mediana **36,82 ms**, p95 **82,78 ms**, Máximo **91,61 ms** (RNF-01 cumplido ampliamente). Latencia API punta a punta promedio: **176,50 ms**.<br>• Seguridad: 14 de 14 pruebas aprobadas; Bandit 0 alertas altas; pip-audit 0 vulnerabilidades conocidas en `requirements.txt`. |
| **Evidencia** | `fases/fase2/evidencias_pruebas/` (`pytest_backend_completo_20261118.txt`, `test_all_scenarios_20261118.txt`, `test_historica_flow_20261118.txt`, `rendimiento.txt`, `bandit.txt`, `pip_audit.txt`, `seguridad_pytest.txt`). |

---

## Resumen de Trazabilidad por Sprint

| Sprint | Enfoque Principal | Pruebas Clave | Estado |
|---|---|---|---|
| **Sprint 1** | Datos y aumento | Verificación de particiones y pHash anti-fuga | Completado |
| **Sprint 2** | Entrenamiento IA | Métricas mAP50 / mAP50-95 YOLOv8s | Completado |
| **Sprint 3** | Lógica de semáforo | Pruebas unitarias de semáforo (Verde/Amarillo/Rojo/Sin datos) | Completado |
| **Sprint 4** | Arquitectura y alertas | Pruebas unitarias de servicios modulares y cooldown | Completado |
| **Sprint 5** | Integración y validación | Pruebas de integración, flujo API, seguridad y rendimiento RNF-01 | Completado |
