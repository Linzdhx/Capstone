# Product Backlog — Computer Vision Walmart (CVW)

> **Fuentes:** ERS v4 (sección 13.2, requisitos funcionales; sección 10.3, usuarios; sección 10.6, requisitos futuros) y Guía 1.5 (sprints).
> Cada ítem corresponde a un requisito funcional del ERS. La prioridad y el sprint vienen del ERS; la historia de usuario reformula el requisito desde el punto de vista del usuario.

| ID | Historia de usuario | Requisito | Prioridad | Sprint | Estimación (pts) |
|---|---|---|---|---|---|
| PB-01 | Como administrador técnico, quiero descargar el dataset de Roboflow en formato YOLOv8 para entrenar el modelo. | RF-01 | Alta | 1 | 1 |
| PB-02 | Como administrador técnico, quiero generar un split de validación del 15 % con semilla 42, antes de aumentar, para evaluar el modelo con datos limpios. | RF-02 | Alta | 1 | 2 |
| PB-03 | Como administrador técnico, quiero generar 3 copias aumentadas por imagen de entrenamiento (degradación y geometría) para robustecer el modelo. | RF-03 | Alta | 1 | 3 |
| PB-04 | Como administrador técnico, quiero crear el `data.yaml` con rutas, nc = 2 y nombres de clases para configurar el entrenamiento. | RF-04 | Alta | 1 | 1 |
| PB-05 | Como administrador técnico, quiero entrenar YOLOv8 (100 épocas, 640 px, batch 16, patience 20) y guardar `best.pt`. | RF-05 | Alta | 2 | 8 |
| PB-06 | Como administrador técnico, quiero obtener Precisión, Recall, mAP50 y mAP50-95 globales y por clase para validar el modelo. | RF-06 | Alta | 2 | 3 |
| PB-07 | Como supervisor, quiero procesar un conjunto de imágenes y obtener por cada una las detecciones y la imagen anotada. | RF-07 | Alta | 2 | 3 |
| PB-08 | Como supervisor, quiero conocer el % de stock visible de cada imagen para saber el estado de la góndola. | RF-08 | Alta | 3 | 2 |
| PB-09 | Como supervisor, quiero que cada bandeja se clasifique en Verde (100–41 %), Amarillo (40–21 %) o Rojo (20–0 %) para priorizar las rondas de reposición. | RF-09 | Alta | 3 | 2 |
| PB-10 | Como reponedor, quiero saber el Pasillo / Góndola / Nivel de cada imagen para ir directo al lugar. | RF-10 | Alta | 3 | 3 |
| PB-11 | Como reponedor, quiero recibir una alerta con la ubicación y el % de stock cuando una góndola queda en Rojo. | RF-11 | Alta | 4 | 5 |
| PB-12 | Como administrador técnico, quiero descargar `best.pt` para usar el modelo fuera de Colab. | RF-12 | Media | 2 | 1 |
| PB-13 | Como supervisor, quiero ver las detecciones y el semáforo en una interfaz web. | RF-13 | Media | 4–5 | 8 |
| PB-14 | Como equipo de desarrollo, queremos contar con una API propia del sistema para integrar los módulos. | RF-14 | Media | 4 | 8 |

**Escala:** puntos de historia (1, 2, 3, 5, 8, 13), según el esfuerzo relativo estimado por el equipo. **Total:** 50 puntos.
## Requisitos futuros (backlog de largo plazo)

| ID | Ítem | Fuente |
|---|---|---|
| PB-F1 | Incorporar imágenes reales de salas Walmart etiquetadas para reentrenar el modelo. | ERS 10.6 |
| PB-F2 | Crear un set de prueba (test) independiente y ampliar el set de validación. | ERS 10.6 |
| PB-F3 | Evaluar variantes de mayor capacidad (YOLOv8s/m) si el hardware lo permite. | ERS 10.6 |
| PB-F4 | Evaluar un cálculo del % de stock ponderado por área de las cajas. | ERS 10.6 |
| PB-F5 | Exportar el modelo a formatos optimizados (ONNX) para ejecución en equipos de sala. | ERS 10.6 |
| PB-F6 | Integración con los sistemas de inventario del cliente. | ERS 10.6 |

## Notas

- La columna **Estimación** no está definida en los documentos del proyecto. El equipo debe completarla (por ejemplo, con puntos de historia).
- En la Fase 1 (Guía 1.5) el proyecto se planteó con segmentación de instancias, base de datos SQLite/PostgreSQL y alertas por Telegram/Webhook. El ERS v4 actualizó esos puntos a detección con bounding boxes, carpeta de ubicaciones dentro del proyecto y alertas por correo electrónico. Este backlog sigue el ERS v4.
