# Sprint Backlog — Computer Vision Walmart (CVW)

> **Fuentes:** Guía 1.5 (secciones 5, 6 y 7: metodología, evidencias y plan de trabajo) y ERS v4 (secciones 5 y 7).
> Planificación de 5 sprints de 2 a 3 semanas, dentro de las 18 semanas de la asignatura.

## Sprint 1 — Adquisición y preparación de datos

- **Duración:** 1–2 semanas
- **Objetivo:** contar con un dataset de góndolas listo para entrenar.
- **Ítems del Product Backlog:** PB-01, PB-02, PB-03, PB-04

| Tarea | Recursos | Responsable |
|---|---|---|
| Descargar el dataset de Roboflow, validar las imágenes de góndolas, generar el split train/valid y aplicar data augmentation. | Roboflow Universe, Google Colab, Python, Albumentations | David Yañez, Francisco Fernández, David Salvatierra, Francisco Merino |

- **Observación:** asegurar que las imágenes tengan diversidad de ángulos y luces.

## Sprint 2 — Entrenamiento y prototipado del modelo IA

- **Duración:** 3 semanas
- **Objetivo:** entrenar el modelo y medir su desempeño.
- **Ítems del Product Backlog:** PB-05, PB-06, PB-07, PB-12
- **Entregable (evidencia de avance):** dataset y modelo base con métricas de desempeño.

| Tarea | Recursos | Responsable |
|---|---|---|
| Entrenar el modelo YOLOv8 en Google Colab y medir Precisión, Recall y mAP por clase. | Python, Ultralytics, Google Colab (GPU T4) | Francisco Fernández / David Yañez |

- **Observación:** requerirá varias iteraciones de ajuste de hiperparámetros.

## Sprint 3 — Semáforo operativo y ubicaciones

- **Duración:** 3–4 semanas
- **Objetivo:** validar la lógica de negocio antes de la integración.
- **Ítems del Product Backlog:** PB-08, PB-09, PB-10
- **Entregable (evidencia de avance):** estructura de ubicaciones y script del semáforo.

| Tarea | Recursos | Responsable |
|---|---|---|
| Organizar la carpeta de ubicaciones (pasillos / góndolas / niveles) y programar el cálculo del % de stock visible con los umbrales del semáforo. | Python, carpeta de ubicaciones del proyecto | Francisco Fernández / David Yañez |

- **Observación:** mantener la fórmula de cálculo ligera para no ralentizar el procesador.

## Sprint 4 — Modularización en VS Code y servicio de alertas

- **Duración:** 3–4 semanas
- **Objetivo:** pasar del notebook a una estructura modular con API y alertas.
- **Ítems del Product Backlog:** PB-11, PB-13, PB-14
- **Entregable (evidencia final):** proyecto modular integrado en VS Code.

| Tarea | Recursos | Responsable |
|---|---|---|
| Estructurar el proyecto en VS Code en módulos limpios, crear la API e integrar el envío de alertas automáticas. | VS Code, servicio de alertas, API del sistema | David Salvatierra / Francisco Merino |

- **Observación:** facilitador: uso de librerías estándar de Python.

## Sprint 5 — Integración, pruebas y validación

- **Duración:** "6 semana", según el Plan de Trabajo de la Guía 1.5 [VERIFICAR si es duración o semana del calendario]
- **Objetivo:** probar el flujo completo y corregir falsas alarmas.
- **Entregable (evidencia final):** demostración funcional e informe final.

| Tarea | Recursos | Responsable |
|---|---|---|
| Realizar pruebas completas con imágenes de góndolas con distintos niveles de stock, verificar la latencia de inferencia y corregir posibles falsas alarmas. | Lotes de imágenes de prueba, entorno VS Code | David Salvatierra / Francisco Merino |

- **Observación:** analizar el comportamiento ante sombras y oclusiones por personas pasando.

## Seguimiento

## Seguimiento

> Fechas aproximadas, reconstruidas a partir del historial del repositorio en GitHub y de las fechas de los documentos del proyecto. El equipo entregó avances cada una o dos semanas.

| Sprint | Fechas (aprox.) | Estado | Evidencia de avance |
|---|---|---|---|
| 1 – Datos | Agosto – mediados de septiembre 2026 | Terminado | Dataset de Roboflow descargado, particionado y aumentado; incluido en el notebook de entrenamiento subido el 22/09. |
| 2 – Modelo IA | Mediados de septiembre – octubre 2026 | Terminado | YOLOv8n entrenado (notebook subido el 22/09; métricas en ERS v3 del 25/09). Segunda versión YOLOv8s v2 con dataset v4 de 349 imágenes (informe de avance del 23/10). |
| 3 – Semáforo y ubicaciones | Octubre – noviembre 2026 | En revisión | Lógica del semáforo con 6 pruebas automatizadas (rama `Dsalvatierra`, Pull Request #1, 02/11). Registro de ubicaciones e incidencias en `main` (05/11). |
| 4 – Modularización, API y alertas | Septiembre – noviembre 2026 | En curso | Sistema modular inicial con backend y frontend (23/09); implementación de la API (05/11); alertas con captura, registro de eventos y webhook. |
| 5 – Integración y pruebas | Noviembre 2026 | En curso | Pruebas unitarias con pytest en el backend; análisis de los 10 mejores y 10 peores casos del modelo (informe intermedio). Pendientes: pruebas del flujo completo. |