# ==============================================================
# Etapa 1: Compilación de Frontend (React + Vite + TypeScript)
# ==============================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Copiar manifiestos de paquetes e instalar dependencias limpias
COPY frontend/package*.json ./
RUN npm ci

# Copiar código fuente del frontend y compilar bundle de producción
COPY frontend/ ./
RUN npm run build

# ==============================================================
# Etapa 2: Runtime Backend (FastAPI + YOLOv8 + Static Frontend)
# ==============================================================
FROM python:3.12-slim

# Evitar prompts interactivos y buffer en logs
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema necesarias para OpenCV y video
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código backend, configuraciones y modelos
COPY backend/ ./backend/
COPY configs/ ./configs/
COPY models/ ./models/
COPY .env.example .env

# Copiar el bundle del frontend compilado en la Etapa 1
COPY --from=frontend-builder /build/dist ./frontend/dist

# Crear directorios necesarios para persistencia de datos, alertas, incidencias e histórico
RUN mkdir -p data/collected data/pending_review data/approved data/validation data/incidents alerts/images alerts/logs historica

# Exponer puerto FastAPI + Frontend integrado
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Comando de ejecución con Uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
