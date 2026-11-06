# Retrospectivas — Computer Vision Walmart (CVW)

> **Fuentes:** Guía 2 de Desarrollo del Proyecto (2.4: facilitadores, dificultades y ajustes), Informe técnico de avance del equipo (sección 4.9, dificultades y decisiones), Informe Intermedio de Avance e historial del repositorio.
> Formato por sprint: **qué funcionó**, **qué no funcionó o costó** y **qué cambiamos**.

## Sprint 1 — Adquisición y preparación de datos

| Qué funcionó | Qué no funcionó o costó | Qué cambiamos |
|---|---|---|
| Usar un dataset público ya etiquetado en Roboflow Universe aceleró la etapa de datos. | El dataset era reducido por limitaciones de infraestructura y muy desbalanceado: muchos más productos que espacios vacíos. | Se aplicó aumento de datos con Albumentations al set de entrenamiento. |
| Fijar la semilla (42) hizo reproducibles la partición y el entrenamiento. | Las imágenes casi idénticas de una misma góndola podían quedar repartidas entre entrenamiento y prueba, inflando las métricas. | En la versión 2 se pasó al dataset v4 (349 imágenes) y se agruparon las imágenes similares con hashes perceptuales (pHash) antes de particionar. |

## Sprint 2 — Entrenamiento y prototipado del modelo IA

| Qué funcionó | Qué no funcionó o costó | Qué cambiamos |
|---|---|---|
| Google Colab con GPU T4 y la librería Ultralytics permitieron entrenar sin hardware propio. | La segmentación con polígonos era más compleja y lenta de integrar. | Se priorizó la detección con cajas delimitadoras en dos clases (product y missing), por simplicidad y velocidad. |
| Se obtuvieron métricas estándar (Precisión, Recall, mAP) por clase. | La clase missing (espacio vacío) es la más difícil: en la v2 el modelo detecta menos de la mitad de los vacíos (recall 47,9 %). | Se entrenó YOLOv8s v2 y se creó un set de prueba degradado tipo cámara (`test_cam`) para medir la robustez. |
| | Los resultados de YOLOv8n y YOLOv8s no se pueden comparar directamente: usan datasets y particiones distintas. | Se dejó documentado que para compararlos hay que evaluarlos sobre las mismas imágenes. |

## Sprint 3 — Semáforo operativo y ubicaciones

| Qué funcionó | Qué no funcionó o costó | Qué cambiamos |
|---|---|---|
| La lógica de cálculo del % de stock es ligera y no agrega procesos complejos. | Una base de datos externa agregaba componentes innecesarios para el alcance del proyecto. | Se reemplazó por una carpeta de ubicaciones dentro del propio proyecto. |
| | Los rangos iniciales del semáforo no estaban acordados por todo el equipo. | Se acordaron los rangos: Verde 100–41 %, Amarillo 40–21 % y Rojo 20–0 %. |
| | El módulo de incidencias de la API usa otros umbrales de severidad (por % de faltantes). | Queda pendiente unificar ambos criterios. |

## Sprint 4 — Modularización en VS Code, API y alertas

| Qué funcionó | Qué no funcionó o costó | Qué cambiamos |
|---|---|---|
| Pasar del notebook a una estructura modular (backend FastAPI y frontend React) ordenó el código y permitió trabajar en paralelo. | La creación de la API se retrasó respecto de lo planificado. | Se priorizó terminar los módulos principales antes de la presentación. |
| Las alertas quedan registradas con captura y archivo de eventos. | El canal de notificación cambió durante el proyecto (Telegram → correo electrónico → webhook en el código actual). | Falta definir el canal definitivo con el cliente. |
| Trabajar con ramas por integrante y Pull Requests evitó pisar el trabajo de otros. | | |

## Sprint 5 — Integración y pruebas

| Qué funcionó | Qué no funcionó o costó | Qué cambiamos |
|---|---|---|
| Pruebas automatizadas con pytest para inventario, alertas, incidencias y dataset. | Sin acceso a cámaras reales: las pruebas usan imágenes públicas y simulaciones. | Se generaron versiones degradadas de las imágenes para simular cámaras de seguridad. |
| El análisis de los 10 mejores y 10 peores casos mostró dónde falla el modelo (sombras, escala de grises, vistas oblicuas o lejanas, góndolas muy densas). | Sombras y oclusiones generan falsos positivos y vacíos no detectados. | Se agregó la verificación de la latencia de inferencia a las pruebas de integración. Acciones propuestas: aumentar la resolución de inferencia, inferencia por cuadrantes (SAHI) y validar SAM con anotaciones manuales. |

## Acuerdos para la siguiente fase

1. Conseguir imágenes reales de sala para evaluar y reentrenar el modelo.
2. Unificar los umbrales del semáforo y de la severidad de incidencias.
3. Definir con el cliente el canal definitivo de notificación.
4. Registrar una retrospectiva al cierre de cada sprint en este mismo documento.
