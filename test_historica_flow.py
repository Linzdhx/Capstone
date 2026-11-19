import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
import requests

from backend.app.core.config import BASE_DIR

BASE_URL = "http://localhost:8000"


@contextlib.contextmanager
def server_context():
    """Context manager que aísla historica/ y levanta el servidor si no está activo."""
    hist_dir = BASE_DIR / "historica"
    hist_dir.mkdir(parents=True, exist_ok=True)

    # 1. Respaldar archivos existentes en historica/
    temp_backup = tempfile.mkdtemp(prefix="cvw_historica_backup_")
    existing_files = list(hist_dir.glob("*"))
    for f in existing_files:
        try:
            shutil.move(str(f), str(Path(temp_backup) / f.name))
        except Exception:
            pass

    # 2. Levantar servidor si no está ya en ejecución
    proc = None
    server_started = False
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=1.0)
        if r.status_code == 200:
            server_started = False
    except Exception:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(BASE_DIR)
        env["YOLO_CONFIG_DIR"] = str(BASE_DIR / ".ultralytics")
        env["CAMERA_SOURCE_TYPE"] = "synthetic"
        proc = subprocess.Popen(
            [sys.executable, "run.py"],
            cwd=str(BASE_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        server_started = True

        ready = False
        for _ in range(30):
            time.sleep(0.5)
            try:
                r = requests.get(f"{BASE_URL}/api/health", timeout=1.0)
                if r.status_code == 200:
                    ready = True
                    break
            except Exception:
                pass

        if not ready:
            if proc:
                proc.terminate()
            for f in Path(temp_backup).glob("*"):
                shutil.move(str(f), str(hist_dir / f.name))
            shutil.rmtree(temp_backup, ignore_errors=True)
            raise RuntimeError("El servidor no inició en http://localhost:8000 tras 15 segundos")

    try:
        yield BASE_URL, temp_backup
    finally:
        # Apagar servidor si fue iniciado en este contexto
        if proc and server_started:
            proc.terminate()
            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.kill()

        # Limpiar imágenes de prueba creadas
        for tf_name in ["gondola_lacteos.jpg", "gondola_panaderia.jpg"]:
            tf = hist_dir / tf_name
            if tf.exists():
                tf.unlink()

        # Restaurar archivos originales
        for f in Path(temp_backup).glob("*"):
            try:
                shutil.move(str(f), str(hist_dir / f.name))
            except Exception:
                pass
        shutil.rmtree(temp_backup, ignore_errors=True)


@pytest.fixture(scope="module")
def managed_server():
    with server_context() as (url, backup_dir):
        yield url, backup_dir


def run_tests(base_url: str = BASE_URL, backup_dir: str = None):
    print("==================================================")
    print("  EJECUTANDO PRUEBAS DEL NUEVO FLUJO /historica   ")
    print("==================================================")

    # 1. Verificar estado inactivo inicial
    r = requests.get(f"{base_url}/api/stock/dashboard")
    dash = r.json()
    print("1. Estado Inactivo Inicial:")
    print(f'   is_active = {dash.get("is_active")} | total_aisles = {dash.get("total_aisles")}')
    assert dash.get("is_active") is False, "El Dashboard debe iniciar inactivo si /historica está vacía"

    # 2. Carga de imagen sin fallas -> Descartada
    # Usar una muestra de góndola abastecida del repositorio
    clean_bytes = None
    if backup_dir:
        candidates = list(Path(backup_dir).glob("002_*.jpg")) or list(Path(backup_dir).glob("*.jpg"))
        if candidates:
            with open(candidates[0], "rb") as f:
                clean_bytes = f.read()

    if clean_bytes is None:
        clean_img = np.full((480, 640, 3), 180, dtype=np.uint8)
        _, clean_buf = cv2.imencode(".jpg", clean_img)
        clean_bytes = clean_buf.tobytes()

    files = [("files", ("estanteria_completa.jpg", clean_bytes, "image/jpeg"))]
    r = requests.post(f"{base_url}/api/stock/upload", files=files)
    up_res = r.json()
    print("2. Carga de imagen sin faltantes:")
    print(f'   Total analizadas: {up_res["total_analyzed"]}')
    print(f'   Fallas detectadas: {up_res["faults_detected"]}')
    print(f'   Descartadas: {up_res["discarded_clean"]}')
    print(f'   Dashboard activo: {up_res["dashboard_active"]}')
    assert up_res["faults_detected"] == 0
    assert up_res["discarded_clean"] == 1
    assert up_res["dashboard_active"] is False

    # 3. Carga y almacenamiento en /historica
    hist_dir = BASE_DIR / "historica"
    hist_dir.mkdir(parents=True, exist_ok=True)
    img1_path = hist_dir / "gondola_lacteos.jpg"
    img2_path = hist_dir / "gondola_panaderia.jpg"

    cv2.imwrite(str(img1_path), np.zeros((480, 640, 3), dtype=np.uint8))
    time.sleep(0.05)
    cv2.imwrite(str(img2_path), np.zeros((480, 640, 3), dtype=np.uint8))

    r = requests.get(f"{base_url}/api/stock/dashboard")
    dash = r.json()
    print("3. Activación por Faltantes en /historica:")
    print(f'   is_active = {dash.get("is_active")} | total_aisles = {dash.get("total_aisles")}')
    for a in dash.get("aisles", []):
        print(f'   -> {a["display_name"]} | Archivo: {a["filename"]} | Severidad: {a["severity_info"]["severity"]}')
    assert dash.get("is_active") is True
    assert dash.get("total_aisles") == 2
    assert dash["aisles"][0].get("aisle_name") == "Pasillo 1" or dash["aisles"][0]["display_name"] in ["Pasillo 1", "Alerta 1"]
    assert dash["aisles"][1].get("aisle_name") == "Pasillo 2" or dash["aisles"][1]["display_name"] in ["Pasillo 2", "Alerta 2"]

    # 4. Resolver Pasillo 1 -> Pasillo 2 pasa automáticamente a ser Pasillo 1
    file_to_resolve = dash["aisles"][0]["filename"]
    print(f"4. Resolviendo falla de Pasillo 1 ({file_to_resolve})...")
    r = requests.post(f"{base_url}/api/stock/historica/{file_to_resolve}/resolve")
    res_data = r.json()
    print(f'   Respuesta de resolución: {res_data.get("message")}')

    r = requests.get(f"{base_url}/api/stock/dashboard")
    dash_reordered = r.json()
    print("   Estado tras resolución:")
    print(f'   Pasillos restantes: {dash_reordered.get("total_aisles")}')
    for a in dash_reordered.get("aisles", []):
        print(f'   -> {a["display_name"]} | Archivo: {a["filename"]}')

    assert dash_reordered.get("total_aisles") == 1
    assert dash_reordered["aisles"][0].get("aisle_name") == "Pasillo 1" or dash_reordered["aisles"][0]["display_name"] in ["Pasillo 1", "Alerta 1"], "El antiguo Pasillo 2 DEBE ser ahora Pasillo 1"
    assert dash_reordered["aisles"][0]["filename"] == "gondola_panaderia.jpg"
    print("   -> ÉXITO: El antiguo Pasillo 2 pasó a ser automáticamente Pasillo 1!")

    # 5. Resolver el pasillo restante -> El Dashboard vuelve al estado inactivo
    last_file = dash_reordered["aisles"][0]["filename"]
    print(f"5. Resolviendo último pasillo ({last_file})...")
    requests.post(f"{base_url}/api/stock/historica/{last_file}/resolve")

    r = requests.get(f"{base_url}/api/stock/dashboard")
    dash_final = r.json()
    print("   Estado final con /historica vacía:")
    print(f'   is_active = {dash_final.get("is_active")} | total_aisles = {dash_final.get("total_aisles")}')
    assert dash_final.get("is_active") is False
    print("   -> ÉXITO: El Dashboard vuelve a quedar inactivo correctamente.")

    print("\n==================================================")
    print("   TODAS LAS PRUEBAS DEL NUEVO FLUJO PASARON 100% ")
    print("==================================================")


def test_historica_flow(managed_server):
    url, backup_dir = managed_server
    run_tests(base_url=url, backup_dir=backup_dir)


if __name__ == "__main__":
    with server_context() as (url, backup_dir):
        run_tests(base_url=url, backup_dir=backup_dir)
