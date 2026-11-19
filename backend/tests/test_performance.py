"""Pruebas de rendimiento y latencia de inferencia y API (RNF-01).

Valida que el modelo de producción activo (YOLOv8s, models/production/best.pt)
cumpla con el tiempo máximo de inferencia por imagen (< 5 segundos, RNF-01)
sobre al menos 20 imágenes reales de prueba del repositorio.
"""
import os
import time
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".ultralytics"))


def _check_dependencies_and_weights():
    try:
        import cv2
        import torch
        from ultralytics import YOLO
    except ImportError as e:
        pytest.skip(f"Dependencias de visión/ML no disponibles: {e}")

    model_path = ROOT / "models" / "production" / "best.pt"
    if not model_path.exists():
        pytest.skip(f"Pesos de producción no encontrados en {model_path}")

    images = list((ROOT / "historica").glob("*.jpg"))
    if len(images) < 20:
        images += list((ROOT / "data").rglob("*.jpg"))
    images = images[:20]

    if len(images) < 20:
        pytest.skip(f"Se requieren al menos 20 imágenes de prueba, encontradas: {len(images)}")

    return model_path, images


@pytest.mark.performance
def test_yolov8s_inference_latency_rnf01():
    """Valida que la inferencia de YOLOv8s sobre 20 imágenes cumpla RNF-01 (< 5 s por imagen)."""
    import cv2
    import torch
    from ultralytics import YOLO

    model_path, images = _check_dependencies_and_weights()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = YOLO(str(model_path))

    # Calentamiento
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    _ = model(dummy, device=device, verbose=False)

    latencies_ms = []
    for img_path in images:
        frame = cv2.imread(str(img_path))
        assert frame is not None, f"No se pudo leer la imagen {img_path}"

        t0 = time.perf_counter()
        _ = model(frame, device=device, verbose=False)
        t1 = time.perf_counter()

        latency_ms = (t1 - t0) * 1000.0
        latencies_ms.append(latency_ms)

        # Aserción por imagen: RNF-01 exige < 5000 ms
        assert latency_ms < 5000.0, f"Latencia excedió 5 s en {img_path.name}: {latency_ms:.1f} ms"

    p50 = float(np.percentile(latencies_ms, 50))
    p95 = float(np.percentile(latencies_ms, 95))
    max_lat = max(latencies_ms)

    assert p50 > 0.0
    assert p95 > 0.0
    assert max_lat < 5000.0


@pytest.mark.performance
def test_api_end_to_end_upload_latency():
    """Valida que el endpoint de subida y análisis de imagen responda en tiempo adecuado."""
    from fastapi.testclient import TestClient
    from backend.app.main import app

    _, images = _check_dependencies_and_weights()
    client = TestClient(app)

    test_img = images[0]
    with open(test_img, "rb") as f:
        img_bytes = f.read()

    # Warmup
    client.post("/api/stock/upload", files={"files": (test_img.name, img_bytes, "image/jpeg")})

    latencies_ms = []
    for _ in range(5):
        t0 = time.perf_counter()
        response = client.post("/api/stock/upload", files={"files": (test_img.name, img_bytes, "image/jpeg")})
        t1 = time.perf_counter()
        assert response.status_code == 200
        latencies_ms.append((t1 - t0) * 1000.0)

    avg_latency = float(np.mean(latencies_ms))
    assert avg_latency < 5000.0, f"Latencia API punta a punta excedió 5 s: {avg_latency:.1f} ms"

