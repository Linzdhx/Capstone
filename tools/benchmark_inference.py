#!/usr/bin/env python
"""Script de benchmark de rendimiento para inferencia YOLOv8s y API (RNF-01).

Mide la latencia de inferencia con el modelo de producción activo sobre al menos
20 imágenes de prueba del repositorio y calcula mediana (p50), p95 y máximo en ms.
Mide además la latencia punta a punta del endpoint de ingesta de la API.
"""
import os
import sys
import time
from pathlib import Path
import numpy as np
import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".ultralytics"))

try:
    import torch
    from ultralytics import YOLO
except ImportError as e:
    print(f"Error: Dependencias no disponibles ({e})")
    sys.exit(1)


def run_benchmark():
    model_path = ROOT / "models" / "production" / "best.pt"
    if not model_path.exists():
        print(f"Error: Modelo no encontrado en {model_path}")
        sys.exit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    device_name = torch.cuda.get_device_name(0) if device == "cuda" else "CPU"

    # Seleccionar al menos 20 imágenes de prueba
    images = list((ROOT / "historica").glob("*.jpg"))
    if len(images) < 20:
        images += list((ROOT / "data").rglob("*.jpg"))
    images = images[:20]

    if len(images) < 20:
        print(f"Advertencia: Solo se encontraron {len(images)} imágenes de prueba.")
        if not images:
            sys.exit(1)

    print("==================================================================")
    print("  BENCHMARK DE RENDIMIENTO — CVW INVENTORY MONITOR (RNF-01)")
    print("==================================================================")
    print(f"Modelo: {model_path.relative_to(ROOT)} (YOLOv8s)")
    print(f"Dispositivo de cómputo: {device.upper()} ({device_name})")
    print(f"Muestras de prueba analizadas: {len(images)} imágenes")
    print("------------------------------------------------------------------")

    model = YOLO(str(model_path))

    # Calentamiento (Warmup)
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    _ = model(dummy, device=device, verbose=False)

    latencies_ms = []
    for p in images:
        frame = cv2.imread(str(p))
        if frame is None:
            continue
        t0 = time.perf_counter()
        _ = model(frame, device=device, verbose=False)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    if not latencies_ms:
        print("Error: No se pudieron procesar las imágenes de prueba.")
        sys.exit(1)

    latencies_sorted = sorted(latencies_ms)
    p50 = float(np.percentile(latencies_sorted, 50))
    p95 = float(np.percentile(latencies_sorted, 95))
    pmax = float(max(latencies_sorted))
    pmin = float(min(latencies_sorted))
    pmean = float(np.mean(latencies_sorted))

    print(f"Latencia Mínima:   {pmin:8.2f} ms")
    print(f"Latencia Mediana:  {p50:8.2f} ms")
    print(f"Latencia Media:    {pmean:8.2f} ms")
    print(f"Latencia p95:      {p95:8.2f} ms")
    print(f"Latencia Máxima:   {pmax:8.2f} ms")
    print("------------------------------------------------------------------")

    # Medición de endpoint API punta a punta
    api_latencies_ms = []
    try:
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)
        test_img = images[0]
        with open(test_img, "rb") as f:
            img_bytes = f.read()

        # Warmup API
        client.post("/api/stock/upload", files={"files": (test_img.name, img_bytes, "image/jpeg")})

        for _ in range(5):
            t0 = time.perf_counter()
            r = client.post("/api/stock/upload", files={"files": (test_img.name, img_bytes, "image/jpeg")})
            t1 = time.perf_counter()
            if r.status_code == 200:
                api_latencies_ms.append((t1 - t0) * 1000.0)

        api_mean = float(np.mean(api_latencies_ms))
        print(f"Latencia API Endpoint (POST /api/stock/upload) promedio: {api_mean:8.2f} ms")
    except Exception as ex:
        print(f"Nota: No se pudo medir latencia API directa: {ex}")

    print("------------------------------------------------------------------")
    cumple_rnf01 = pmax < 5000.0
    print(f"Criterio RNF-01 (Inferencia < 5000 ms): {'CUMPLE (APROBADO)' if cumple_rnf01 else 'FALLA'}")
    print("==================================================================")

    return {
        "device": device,
        "device_name": device_name,
        "count": len(images),
        "p50": p50,
        "p95": p95,
        "max": pmax,
        "mean": pmean,
        "api_mean": np.mean(api_latencies_ms) if api_latencies_ms else None,
        "cumple_rnf01": cumple_rnf01,
    }


if __name__ == "__main__":
    run_benchmark()

