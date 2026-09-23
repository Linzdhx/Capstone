# Dockerfile para CVW Inventory Monitor
FROM python:3.12-slim

# Evitar prompts interactivos
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

# Copiar código del proyecto y artefactos
COPY backend/ ./backend/
COPY configs/ ./configs/
COPY models/ ./models/
COPY frontend/dist/ ./frontend/dist/
COPY .env.example .env

# Crear directorios para persistencia de datos y logs
RUN mkdir -p data/collected data/pending_review data/approved data/validation alerts/images alerts/logs

# Exponer puerto FastAPI + Frontend integrado
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Comando de ejecución con Uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
