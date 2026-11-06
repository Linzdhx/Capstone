# Innovación — Computer Vision Walmart (CVW)

> **Fuentes:** Informe Final del proyecto, ERS v4, código del repositorio (`backend/app/`), Informe Intermedio de Avance e informe técnico del equipo.

## 1. Detectar el hueco, no el producto ("void detection")

En lugar de reconocer miles de productos (SKU) distintos, el modelo distingue solo **dos clases: `product` y `missing`**. Esto reduce drásticamente el volumen de etiquetado necesario y permite medir directamente lo que le importa al negocio: cuánto espacio está vacío.

## 2. Sin hardware adicional

La solución usa imágenes de la góndola en vez de sensores físicos. A diferencia de soluciones con básculas o sensores IoT en cada estante, **no requiere hardware costoso**, y al operar desacoplada de las cámaras en directo no compromete la ciberseguridad corporativa.

## 3. De la detección a una acción operativa

El sistema no se queda en las cajas detectadas:
- Calcula el **% de stock visible** de cada góndola.
- Lo clasifica en un **semáforo operativo** (Verde / Amarillo / Rojo).
- Asocia cada detección a una **ubicación** (Pasillo / Góndola).
- Genera **incidencias con severidad**, sin duplicados, y **alertas** con captura y registro.

Así el reponedor recibe dónde ir y qué tan urgente es, en vez de hacer rondas a ciegas.

## 4. Aprendizaje continuo con revisión humana (active learning)

El sistema mejora con su propio uso:

1. **Captura automática** de imágenes difíciles: confianza menor a 0,40 o vacío de 70 % o más.
2. **Revisión humana** en el dashboard: aprobar, rechazar o corregir etiquetas.
3. **Reentrenamiento** cuando hay al menos 5 muestras aprobadas.
4. **Evaluación automática** del modelo candidato (mAP50 ≥ 0,80).
5. **Cambio en caliente** (*hot-swap*) del modelo sin detener el sistema, con **rollback** inmediato a la versión anterior.

## 5. Evaluación honesta y robusta del modelo

- **Partición agrupada por similitud (pHash):** evita que fotos casi iguales queden en entrenamiento y prueba a la vez, lo que inflaría las métricas.
- **Simulación de cámara de seguridad:** copias degradadas de las imágenes (compresión, baja resolución, ruido, sombras y escala de grises) para medir cómo se comportaría el modelo en tienda.
- **Análisis por imagen:** ranking de los 10 mejores y 10 peores casos, con emparejamiento uno a uno por clase, para identificar en qué condiciones falla.

## 6. Arquitectura lista para crecer

- Backend modular en **FastAPI** y dashboard en **React**.
- Varias fuentes de imagen (webcam, USB, RTSP, fuente sintética e ingesta de imágenes por lotes).
- Despliegue con **Docker**.
- Versionado de modelos (producción, candidatos y archivo).
