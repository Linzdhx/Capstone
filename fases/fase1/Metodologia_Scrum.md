# Metodología — Scrum

> **Fuentes:** Guía 1.5 (sección 5, Metodología, y Factibilidad), ERS v4 (sección 5, Metodología y pertinencia) e Informe técnico de avance del equipo (sección 3.3, Pertinencia de la metodología).

## 1. Metodología declarada

Se implementa una metodología ágil basada en el marco **Scrum**, organizada en **5 sprints iterativos de 2 a 3 semanas** de duración a lo largo de las 18 semanas de la asignatura. Esto permite realizar entregas incrementales del sistema, validar el rendimiento de la IA de manera continua y ajustar la solución rápidamente según los resultados obtenidos.

## 2. Justificación

- **Naturaleza empírica de los proyectos de IA:** Scrum fue indispensable porque los resultados del modelo no se conocen hasta entrenarlo y evaluarlo. Los sprints permiten validar el rendimiento en cada iteración y ajustar la solución según los resultados obtenidos.
- **Trabajo en paralelo:** permitió desacoplar las pruebas de entrenamiento intensivo en la nube del desarrollo del software de integración local, evitando que ambas actividades dependieran completamente una de otra.
- **Decisiones rápidas:** facilitó la toma de decisiones sin retrasar los entregables de ingeniería. Ejemplo: el cambio desde la propuesta inicial de segmentación de instancias hacia una estrategia de detección de objetos con cajas delimitadoras.
- **Seguimiento con docente y cliente:** permite sostener reuniones de avance con el docente y, si es posible, con el cliente, presentando iteraciones constantes sin comprometer la calidad del producto final.
- **Factibilidad en el semestre:** la duración acotada del semestre se aborda con sprints e incrementos funcionales, combinando las horas de la asignatura con trabajo autónomo.

## 3. Ciclo de sprints

| Sprint | Nombre | Contenido |
|---|---|---|
| 1 | Adquisición y preparación de datos | Descarga del dataset de góndolas desde Roboflow Universe, partición y aumento de datos. |
| 2 | Entrenamiento y prototipado del modelo IA | Entrenamiento de YOLOv8 en Google Colab y evaluación de Precisión, Recall y mAP por clase. |
| 3 | Semáforo operativo y ubicaciones | Cálculo del % de stock visible, clasificación en el semáforo y asociación con la ubicación. |
| 4 | Modularización en VS Code y alertas | Traslado del código a una estructura modular, creación de la API e integración de alertas. |
| 5 | Integración y pruebas | Pruebas del flujo completo, latencia de inferencia y ajuste de falsos positivos. |

Detalle de tareas y responsables: ver `Sprint_Backlog.md`.

## 4. Roles

### Roles del equipo de desarrollo

| Rol | Integrantes | Responsabilidad |
|---|---|---|
| Desarrollador de IA / Data Engineer | Francisco Fernández, David Yañez | Gestión de la base de datos de imágenes, entrenamiento del modelo YOLO y ajuste de parámetros. |
| Desarrollador Backend e Integración | Francisco Merino, David Salvatierra | Estructura en VS Code, ubicaciones, lógica del cálculo porcentual e integración de las alertas. |

### Roles Scrum

| Rol Scrum | Integrante |
|---|---|
| Product Owner | Direcion de walmart op 
| Scrum Master | Ceferino Anibal Sotelo 
| Equipo de desarrollo | Francisco Fernández, David Yañez, David Salvatierra, Francisco Merino |

## 5. Eventos

| Evento | Cómo se realiza en el proyecto |
|---|---|
| Sprint Planning | Al inicio de cada sprint el equipo se reúne (presencial en la sede o por Discord) para revisar el objetivo del sprint según el `Sprint_Backlog.md`, dividirlo en tareas y repartirlas en conjunto, considerando los roles: IA / Data Engineer (Francisco Fernández, David Yañez) y Backend e Integración (Francisco Merino, David Salvatierra). |
| Reuniones de seguimiento | 2 a 3 veces por semana, de forma presencial en la sede o por Discord. Cada integrante comenta qué avanzó, qué hará a continuación y si tiene algún bloqueo. La coordinación diaria se mantiene por el grupo de WhatsApp del equipo. |
| Sprint Review | Al cierre de cada sprint se revisa el incremento con el docente en las reuniones de avance de la asignatura y, cuando es posible, con el cliente (por ejemplo, el semi-avance presentado a Walmart). |
| Sprint Retrospective | Al cierre de cada sprint el equipo conversa qué funcionó, qué no y qué mejorar en el siguiente sprint.

### Herramientas de seguimiento

| Herramienta | Uso |
|---|---|
| GitHub | Repositorio del código y la documentación; ramas por integrante y Pull Requests hacia `main` para integrar los avances. |
| WhatsApp | Coordinación diaria, avisos y acuerdos rápidos del equipo. |
| Discord | Reuniones de seguimiento y de planificación a distancia. |
## 6. Artefactos

| Artefacto | Archivo |
|---|---|
| Visión del producto | `Product_Vision.md` |
| Product Backlog | `Product_Backlog.md` |
| Sprint Backlog | `Sprint_Backlog.md` |
| Definición de terminado | `Definition_of_Done.md` |
| Planificación (Carta Gantt) | Guía 1.5, sección 8 |
| Requisitos | `SRS_Especificacion_de_Requisitos.docx` y `Requisitos_No_Funcionales.md` |
