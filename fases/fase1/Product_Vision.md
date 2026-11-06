# Product Vision — Computer Vision Walmart (CVW)

> **Fuentes:** Guía 1.5 (Definición del Proyecto APT), `Presentación Proyecto.pptx` y ERS v4 (secciones 3 y 10).

## Declaración de visión

| | |
|---|---|
| **Para** | el personal de reposición y logística de sala, la administración y supervisión de tienda de supermercados (contexto Walmart Chile) |
| **Que** | necesitan identificar con rapidez cuándo una góndola se está quedando vacía, porque los quiebres de stock no detectados a tiempo generan pérdidas económicas y deterioran la experiencia del cliente |
| **El producto** | Computer Vision Walmart (CVW) |
| **Es** | un sistema de visión por computador que detecta productos y espacios vacíos en imágenes de góndolas |
| **Que** | calcula el porcentaje de stock visible por bandeja, lo clasifica en un semáforo operativo y dispara alertas automáticas con la ubicación exacta (Pasillo / Góndola / Nivel) cuando el stock visible cae al 20 % o menos |
| **A diferencia de** | soluciones basadas en hardware adicional, como básculas o sensores IoT en estantes |
| **Nuestro producto** | no requiere hardware costoso ni compromete la ciberseguridad corporativa, ya que opera desacoplado de las cámaras en directo y procesa imágenes por lotes |

## Problema, necesidad y solución

- **Problema:** pérdidas económicas y mala experiencia de compra por el desabastecimiento de las góndolas y por quiebres de stock no detectados a tiempo.
- **Necesidad:** identificar con rapidez cuándo la góndola se está quedando vacía.
- **Solución:** monitoreo mediante visión artificial para alertar al personal cuando una repisa baje a un umbral crítico de stock.

## Usuarios y beneficios

| Usuario | Beneficio |
|---|---|
| Reponedor | Optimiza sus tiempos al evitar rondas visuales a ciegas y dirigirse directamente al pasillo crítico. Recibe las alertas de estado Rojo con la ubicación. |
| Supervisor / Jefe de sala | Revisa el semáforo de las góndolas y prioriza las rondas de reposición. Reduce las ventas perdidas y mejora el cumplimiento del planograma. |
| Cliente | Encuentra los productos exhibidos y disponibles para su compra. |
| Administrador técnico (equipo) | Carga los lotes de imágenes, mantiene la carpeta de ubicaciones y reentrena o actualiza el modelo. |

## Objetivo del producto

Desarrollar un sistema automatizado de monitoreo e identificación de quiebres de stock en góndolas de supermercado que, mediante visión por computador, procese lotes de imágenes, calcule el porcentaje de stock visible por góndola y lo clasifique según el criterio designado para el recinto en que se implementará.

## Alcance

- **Incluye:** procesamiento por lotes de imágenes de góndolas; detección de productos y espacios vacíos; cálculo del % de stock visible; semáforo operativo (Verde 100–41 %, Amarillo 40–21 %, Rojo 20–0 %); consulta de ubicación; alertas automáticas; API del sistema; demo web de visualización.
- **No incluye:** conexión a cámaras en vivo (CCTV/RTSP); sensores IoT o básculas; reconocimiento de SKU o marcas individuales; reposición automática ni integración con el sistema de inventario de Walmart.
