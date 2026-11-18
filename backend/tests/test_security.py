"""Pruebas de seguridad de la API (Fase 3).

Cubren lo que se puede verificar de forma automática sin infraestructura:
- Recorrido de directorios (path traversal) en los endpoints que sirven imágenes.
- Archivos no imagen en la subida de lotes: no deben botar el servidor ni generar fallas.
- El archivo .env con credenciales no debe quedar versionado.
"""
import io
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


@pytest.mark.parametrize(
    "url",
    [
        "/api/stock/historica/image/..%2F.env.example",
        "/api/stock/historica/image/..%2F..%2F.env.example",
        "/api/stock/historica/image/..%2F..%2Frequirements.txt",
        "/api/dataset/images/approved/..%2F..%2F.env.example",
        "/api/dataset/images/approved/..%2F..%2F..%2Frequirements.txt",
    ],
)
def test_path_traversal_bloqueado(url):
    """Un nombre de archivo con ../ no debe devolver archivos fuera de las carpetas de imágenes."""
    r = client.get(url)
    assert r.status_code in (400, 403, 404)
    assert b"fastapi" not in r.content
    assert b"SERVER_HOST" not in r.content


def test_subida_archivo_no_imagen_no_rompe_api():
    """Un archivo que no es imagen debe descartarse sin error 500 ni falla registrada."""
    r = client.post(
        "/api/stock/upload",
        files={"files": ("malicioso.txt", io.BytesIO(b"no soy una imagen"), "text/plain")},
    )
    assert r.status_code < 500
    if r.status_code == 200:
        assert r.json()["faults_detected"] == 0


def test_env_no_versionado():
    """El .env real (RTSP con usuario/clave, webhook) no debe estar en git."""
    try:
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.splitlines()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("git no disponible")
    assert ".env" not in tracked
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert any(line.strip() == ".env" for line in gitignore.splitlines())
