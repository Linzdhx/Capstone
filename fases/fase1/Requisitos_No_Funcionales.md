# Requisitos No Funcionales — Computer Vision Walmart (CVW)

> **Fuente:** `SRS_Especificacion_de_Requisitos.docx` (ERS v4, IEEE 830), sección 13.3 y sección 10.4.
> Este documento extrae los requisitos no funcionales para tenerlos en un archivo propio.

## 1. Requisitos no funcionales

| ID | Categoría | Descripción |
|---|---|---|
| RNF-01 | Rendimiento | El tiempo de inferencia por imagen debe ser menor a 5 s. Medido: 8,7 ms en GPU T4; se debe validar también en el equipo de ejecución. |
| RNF-02 | Calidad del modelo | Toda nueva versión del modelo debe igualar o superar la línea base v1 (mAP50 global 72,8 %; mAP50 missing 59,9 %). |
| RNF-03 | Seguridad | El sistema no accede a cámaras, CCTV ni a la red corporativa; solo procesa imágenes entregadas por lotes. |
| RNF-04 | Privacidad | Las imágenes se usan solo para analizar góndolas; no se almacenan ni procesan datos personales de clientes. |
| RNF-05 | Gestión de credenciales | Las claves y credenciales (API de Roboflow, cuenta de correo de alertas) se guardan en variables de entorno o secretos, nunca en el código. |
| RNF-06 | Fiabilidad | Una imagen que no se puede leer se omite sin detener el lote (comportamiento ya implementado en la aumentación). |
| RNF-07 | Reproducibilidad | Semilla fija (42) en la partición y el entrenamiento; validación sobre imágenes limpias no aumentadas. |
| RNF-08 | Disponibilidad | El sistema opera bajo demanda al recibir cada lote; no requiere funcionamiento 24/7. |
| RNF-09 | Mantenibilidad | Parámetros centralizados (dataset, versión, N de aumentos, modelo base) y código modular en VS Code; el modelo base se puede cambiar (n/s/m/l) sin modificar el pipeline. |
| RNF-10 | Portabilidad | Modelo liviano (best.pt de 6,3 MB) ejecutable en CPU o GPU sobre cualquier sistema con Python. |

## 2. Restricciones del sistema

- Sin acceso a streaming RTSP/CCTV por políticas de ciberseguridad corporativa: solo imágenes pregrabadas por lotes.
- Sin hardware adicional (básculas o sensores IoT) por costo y problemas de descalibración.
- Clasificación limitada a dos clases (nc = 2): 0 = missing, 1 = product; no se identifican SKU.
- Modelo de detección con bounding boxes (YOLOv8 Nano); se descartó la segmentación de polígonos y SAM por simplicidad y velocidad.
- Entrenamiento sujeto a los recursos y límites de sesión de Google Colab (GPU Tesla T4).
- El dataset de entrenamiento es público (Roboflow Universe) y no proviene de salas de Walmart.
- Sin base de datos externa: la información de ubicación de las góndolas se guarda en una carpeta dentro del propio proyecto.
