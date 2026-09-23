# CVW Inventory Monitor - YOLOv8 Supermarket Stock & Active Learning

Sistema profesional, modular y de alto rendimiento para monitoreo automatizado de inventario en góndolas y estanterías de supermercados mediante visión computacional con **YOLOv8** (`product` y `missing`), análisis de tasa de ocupación/vacío, sistema de alertas persistente con cooldown, Active Learning con flujo Human-in-the-Loop, reentrenamiento desacoplado en segundo plano, evaluación automática y gestión de modelos con **Hot-Swap** y **Rollback**.

---

## 1. Requisitos del Sistema

- **Sistema Operativo:** Windows 10/11 o Linux (Ubuntu 20.04/22.04 LTS).
- **Python:** 3.10 o superior (validado en Python 3.12 con aceleración CUDA).
- **Node.js:** v18 o superior y npm (para compilación del frontend).
- **Aceleración GPU (Opcional pero recomendada):** Tarjeta NVIDIA con soporte CUDA (ej: NVIDIA GeForce RTX 3060 Laptop GPU detectada y soportada). CPU fallback automático si no hay GPU presente.
- **Docker y Docker Compose (Opcional):** Para despliegue contenerizado.

---

## 2. Arquitectura del Proyecto

El sistema aplica una estricta separación de responsabilidades:

```text
Camera Service (Webcam / USB / RTSP / Synthetic)
      ↓
Detection Service (YOLOv8 Inference + ROI Filter + Timing HUD)
      ↓
Inventory Service (Products, Missing, Occupancy %, Empty %)
      ↓
Alert Service (80% Threshold, 3s Consecutive Window, 30s Cooldown, Snapshots)
```

Y el ciclo de mejora continua (Active Learning & Reentrenamiento):

```text
Collected Samples (Low Confidence / High Missing / Manual Trigger)
      ↓
Pending Review (Human Inspection & BBox Class Correction: product ↔ missing)
      ↓
Approved Dataset (YOLO normalized labels export)
      ↓
Training Worker (Background Subprocess / Thread - Non-blocking)
      ↓
Candidate Model Evaluation (mAP50, mAP50-95, Precision, Recall)
      ↓
ModelManager (Hot-Swap to Production & Rollback to Archive)
```

### Estructura de Directorios

```text
├── backend/
│   ├── app/
│   │   ├── api/            # Routers FastAPI (camera, inventory, alerts, models, dataset, training, system, ws)
│   │   ├── core/           # Configuración unificada (config.py) y logging estructurado (logging.py)
│   │   ├── ml/             # ModelManager (hot-swap, rollback, inferencia) y ModelEvaluator (métricas mAP)
│   │   ├── services/       # CameraService, DetectionService, InventoryService, AlertService, DatasetService, TrainingWorker
│   │   ├── schemas/        # Modelos de validación Pydantic (detections, inventory, alerts, models, dataset)
│   │   └── main.py         # Aplicación principal FastAPI con CORS, WebSockets y montaje estático
│   └── tests/              # Suite de pruebas unitarias e integración con Pytest
│
├── frontend/               # Aplicación React + TypeScript + TailwindCSS
│   ├── src/
│   │   ├── components/     # VideoPlayer, Navbar, StatusBadge, MetricCard, SystemMonitor, AlertBanner
│   │   ├── pages/          # Dashboard, Camera, Alerts, DatasetReview, Training, Models, Settings
│   │   ├── services/       # Clientes REST (api.ts) y WebSocket
│   │   ├── hooks/          # useTelemetry (telemetría a 10 Hz)
│   │   └── types/          # Definiciones de tipos TypeScript
│   └── dist/               # Bundle optimizado servido por FastAPI
│
├── models/
│   ├── production/         # Modelo activo en producción (best.pt + metadata.json)
│   ├── candidates/         # Modelos generados tras reentrenamiento esperando activación
│   └── archive/            # Historial de versiones anteriores para rollback instantáneo
│
├── data/
│   ├── collected/          # Capturas automáticas por incertidumbre o reglas
│   ├── pending_review/     # Muestras esperando verificación humana
│   ├── approved/           # Muestras aprobadas con etiquetas YOLO (.txt)
│   └── validation/         # Conjunto de validación para evaluación de candidatos
│
├── alerts/
│   ├── images/             # Snapshots capturados en eventos de alerta
│   └── logs/               # Registro continuo en JSONL (alerts.jsonl)
│
├── configs/
│   └── app_config.yaml     # Configuración externa de la aplicación
├── Dockerfile              # Contenedor de producción
├── docker-compose.yml      # Orquestación con soporte GPU y volúmenes
├── requirements.txt        # Dependencias backend de Python
├── .env.example            # Plantilla de variables de entorno
└── .env                    # Configuración activa local
```

---

## 3. Instalación

### Paso 1: Clonar o posicionarse en el proyecto
```bash
cd "d:\trabajo\Proyecto CVW v1\Modelo entrenado"
```

### Paso 2: Instalar dependencias backend de Python
```bash
python -m pip install -r requirements.txt
```

### Paso 3: Compilar el frontend (React + TypeScript + TailwindCSS)
```bash
cd frontend
npm install
npm run build
cd ..
```
*El comando `npm run build` genera la carpeta `frontend/dist`, la cual es servida automáticamente por el servidor backend FastAPI.*

---

## 4. Configuración

El sistema combina variables de entorno (`.env`) y configuración estructurada en `configs/app_config.yaml`.

Crea tu archivo `.env` a partir de la plantilla:
```bash
cp .env.example .env
```

Variables disponibles:
```env
ENV=development
DEBUG=true
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Cámara: 'webcam', 'usb', 'rtsp', 'synthetic'
CAMERA_SOURCE_TYPE=webcam
CAMERA_WEBCAM_INDEX=0
CAMERA_RTSP_URL=

# Modelos
MODEL_CONFIDENCE=0.25
MODEL_IOU=0.45
MODEL_DEVICE=auto

# Alertas
ALERT_EMPTY_THRESHOLD=0.80
ALERT_CONSECUTIVE_SECONDS=3.0
ALERT_COOLDOWN_SECONDS=30.0
ALERT_WEBHOOK_URL=
```

---

## 5. Ejecución Local

### Método Rápido (Recomendado):
```bash
python run.py
```

### O mediante Uvicorn CLI:
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Abre en tu navegador:
- **Aplicación Web:** [http://localhost:8000](http://localhost:8000)
- **Documentación OpenAPI interactiva:** [http://localhost:8000/docs](http://localhost:8000/docs)

### Opcional: Ejecutar Frontend en modo desarrollo (HMR / Vite):
```bash
cd frontend
npm run dev
```
Disponible en: [http://localhost:5173](http://localhost:5173) (las llamadas a `/api` y `/ws` se redirigen transparentemente al puerto 8000).

---

## 6. Ejecución con Docker / Docker Compose

Para desplegar en contenedores con aceleración GPU:

```bash
docker compose up --build -d
```
El contenedor expondrá el servicio en el puerto `8000` con persistencia en `./models`, `./data`, `./alerts` y `./configs`.

---

## 7. Configuración de Cámara

El sistema soporta cuatro modalidades en `CameraService`:

1. **Webcam Integrada / USB (Índice):** Configura `CAMERA_SOURCE_TYPE=webcam` y `CAMERA_WEBCAM_INDEX=0` (o 1, 2 para cámaras USB secundarias).
2. **Cámara USB Externa:** Selecciona `usb` e indica el índice.
3. **Cámara IP (RTSP):** Configura la URL RTSP completa (ej: `rtsp://usuario:clave@192.168.1.100:554/h264`). **Seguridad:** Las credenciales nunca se envían al frontend.
4. **Simulador Sintético de Estantería (`synthetic`):** Generador de góndola con productos y ganchos vacíos alternantes. Permite desarrollar, probar alertas y evaluar el sistema incluso en servidores sin cámara física conectada.

*Reconexión Automática:* Si la cámara se desconecta físicamente, el servicio entra en modo `CONNECTING` y reintenta la conexión periódicamente cada 3 segundos sin congelar la aplicación.

---

## 8. Colocación de `best.pt` y Metadatos

El modelo principal de producción se encuentra en:
```text
models/production/best.pt
models/production/metadata.json
```

Metadatos inspeccionados del modelo original:
- **Clases:** `0`: `missing`, `1`: `product`.
- **Dataset de origen:** Roboflow "Empty Spaces in a Supermarket Hanger" versión 3.
- **Resolución nativa:** 640x640.

**Regla crítica:** Nunca sobrescribas manualmente `models/production/best.pt`. Utiliza siempre el flujo de candidatos y Hot-Swap provisto por el sistema.

---

## 9. Uso del Dashboard

El Dashboard ofrece visibilidad completa en tiempo real:
- **Tarjetas KPI:** Conteo de productos, conteo de faltantes, total de espacios, tasa de ocupación (%) y tasa de vacío (%).
- **Visor de Cámara en Vivo:** Stream MJPEG optimizado con bounding boxes renderizados en backend (Verde para `product`, Rojo/Coral para `missing`) y HUD de telemetría.
- **Panel de Inferencia:** FPS de inferencia en tiempo real y desglose de tiempos: *Preprocess*, *Inferencia PyTorch* y *Postprocess (NMS)*.
- **Hardware Monitor:** Monitoreo continuo de uso de CPU, núcleos lógicos, memoria RAM en GB y tarjeta NVIDIA GPU (RTX 3060) con VRAM asignada, reservada y total mediante `torch.cuda`.

---

## 10. Sistema de Alertas

Regla de disparo de alerta:
$$\text{empty\_rate} = \frac{\text{missing}}{\text{products} + \text{missing}} \ge 0.80$$

Características clave:
1. **Filtro temporal contra falsos positivos:** La condición debe persistir durante al menos `consecutive_seconds` (por defecto 3.0 segundos). No se dispara por un único fotograma.
2. **Protección contra división por cero:** Si $\text{total\_spaces} = 0$, no se calcula tasa ni se genera alerta.
3. **Cooldown de seguridad:** Tras disparar una alerta, entra en un periodo de enfriamiento de `cooldown_seconds` (por defecto 30.0 segundos) para evitar inundación de avisos.
4. **Persistencia de Snapshots:** Al activarse, guarda automáticamente una imagen de alta resolución en `alerts/images/alert_{id}_{timestamp}.jpg`.
5. **Registro JSONL:** El evento queda registrado en `alerts/logs/alerts.jsonl` con métricas, conteos y ruta del snapshot.
6. **Modal en Frontend:** Visualizador con zoom para inspeccionar los snapshots registrados en cualquier momento.

---

## 11. Active Learning & Human-in-the-Loop (HITL)

El sistema evita explícitamente convertir predicciones no supervisadas en ground truth:

1. **Auto-Recolección:** Se guardan fotogramas automáticamente en `data/collected/` cuando:
   - La confianza de alguna detección es menor a `low_confidence_threshold` (0.40).
   - La tasa de faltantes es inusualmente alta (> 0.70).
   - El operador presiona el botón **"Capturar Muestra"** en la interfaz.
2. **Revisión Humana:** En la pestaña **Active Learning**, el supervisor puede:
   - Inspeccionar cada imagen capturada y sus bounding boxes propuestos.
   - Alternar la clase de cualquier caja con un solo clic (`product` ↔ `missing`).
   - Descartar muestras ruidosas (`rejected`).
   - **Aprobar muestra (`approved`):** Genera automáticamente el archivo de etiquetas normalizado en formato YOLO (`.txt`), listo para el entrenamiento.

---

## 12. Reentrenamiento Desacoplado (Training Worker)

El reentrenamiento se ejecuta como un **proceso en segundo plano independiente**, asegurando que la cámara y la inferencia continúen funcionando sin caídas de FPS.

1. **Requisitos:** Requiere al menos 5 muestras aprobadas en `data/approved/`.
2. **Estructuración:** El worker genera un workspace estructurado con split 80% train / 20% val y su correspondiente `data.yaml`.
3. **Fine-Tuning:** Ejecuta ajuste fino de YOLOv8 a partir del modelo de producción activo, permitiendo configurar:
   - `epochs` (ej: 50)
   - `batch_size` (ej: 16)
   - `imgsz` (ej: 640)
   - `lr0` (ej: 0.01)
4. **Candidato:** Guarda los pesos resultantes en `models/candidates/vXXX/best.pt`.

---

## 13. Evaluación de Modelos y Hot-Swap

Antes de que un candidato pueda usarse en producción:

1. **Evaluación:** El evaluador calcula métricas automáticas sobre el conjunto de validación:
   - $mAP_{50}$
   - $mAP_{50-95}$
   - $Precision$
   - $Recall$
2. **Criterio de Aprobación:** Compara el resultado frente al umbral configurado ($mAP_{50} \ge 0.80$).
3. **Hot-Swap:** Al presionar **"Promover a Producción"**:
   - Archiva la versión actual en `models/archive/vXXX/`.
   - Copia el candidato a `models/production/best.pt`.
   - Actualiza `metadata.json`.
   - Recarga atómicamente la instancia YOLO en memoria sin reiniciar el servidor ni detener la captura de la cámara.

---

## 14. Rollback Instantáneo

Si una versión recién activada en producción no presenta el comportamiento esperado en tienda:
- En la pestaña **Modelos**, busca en la lista de **Versiones Archivadas**.
- Haz clic en **"Restaurar (Rollback)"**.
- El `ModelManager` respaldará la versión descartada y restaurará la versión histórica seleccionada en milisegundos sin tiempo de inactividad.

---

## 15. Tests Automatizados

La suite de pruebas con `pytest` valida exhaustivamente las reglas de negocio y los servicios críticos:

```bash
python -m pytest backend/tests -v
```

Cobertura de pruebas:
- `test_inventory_zero_detections`: Protección contra división por cero cuando no hay detecciones.
- `test_inventory_mixed_detections`: Verificación de tasas exactas de ocupación y vacíos.
- `test_inventory_80_percent_empty`: Activación matemática del umbral de faltantes del 80%.
- `test_inventory_roi_filtering`: Filtrado geométrico de cajas dentro y fuera de la Región de Interés.
- `test_alert_not_triggered_on_single_frame`: Garantía de que un único frame no dispara la alerta.
- `test_alert_triggered_after_consecutive_seconds`: Disparo correcto tras cumplirse la ventana temporal.
- `test_alert_cooldown_prevents_spam`: Verificación del bloqueo de nuevas alertas durante el cooldown.
- `test_alert_ignores_zero_spaces`: Prevención de falsas alertas cuando la estantería no tiene espacios.
- `test_model_manager_classes_and_info`: Inspección de clases `product` y `missing` en `best.pt`.
- `test_model_manager_threshold_update`: Modificación en caliente de confidence e IoU.
- `test_model_manager_list_versions`: Descubrimiento de producción, candidatos y archivo.
- `test_dataset_capture_and_transition`: Ciclo de vida de muestras y generación de etiquetas YOLO `.txt`.

---

## 16. Troubleshooting y Solución de Problemas

1. **¿Qué sucede si no tengo una cámara física conectada?**
   - En la página **Cámara** o en `.env`, selecciona la fuente `synthetic`. La aplicación activará automáticamente el simulador de estantería para que puedas probar todas las funciones, alertas y capturas sin hardware físico.
2. **Error de CUDA o memoria de GPU:**
   - La aplicación detecta automáticamente la disponibilidad de CUDA. Si la VRAM no es suficiente o no hay drivers NVIDIA instalados, el `ModelManager` conmuta de forma transparente a ejecución en `cpu`.
3. **La alerta no se dispara al superar el 80%:**
   - Verifica que la condición persista durante los 3 segundos configurados de forma continua y que no se encuentre en periodo de cooldown (observa el contador de cooldown en la tarjeta del Dashboard o Alertas).
4. **El reentrenamiento no inicia:**
   - Asegúrate de haber aprobado al menos 5 imágenes en la pestaña **Active Learning** (`data/approved/`).
