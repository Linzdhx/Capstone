"""Pruebas de seguridad de la API y repositorio (Fase 2 / Fase 3).

Cubren lo requerido por el Plan de Pruebas y la Guía de Seguridad:
- Escaneo de secretos en archivos versionados (patrones de credenciales, API keys, tokens, RTSP con usuario/clave, webhooks reales).
- Verificación de que .env no esté versionado y que .env.example no contenga credenciales reales.
- Detección/documentación de hallazgo en configuración CORS (allow_origins=["*"] con allow_credentials=True).
- Resiliencia de la API en endpoints de ingesta frente a archivos no imagen, archivos vacíos y archivos corruptos (sin 500 ni fuga de trazas).
- Recorrido de directorios (path traversal) en endpoints que reciben nombres de archivos o IDs.
"""
import io
import os
import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".ultralytics"))

from backend.app.main import app

client = TestClient(app)


# ---------- 1. Path Traversal ----------

@pytest.mark.parametrize(
    "url",
    [
        "/api/stock/historica/image/..%2F.env.example",
        "/api/stock/historica/image/..%2F..%2F.env.example",
        "/api/stock/historica/image/..%2F..%2Frequirements.txt",
        "/api/alerts/snapshots/..%2F..%2Frequirements.txt",
        "/api/alerts/snapshots/..%2F..%2Fetc%2Fpasswd",
        "/api/dataset/images/approved/..%2F..%2F.env.example",
        "/api/dataset/images/approved/..%2F..%2F..%2Frequirements.txt",
    ],
)
def test_path_traversal_bloqueado(url):
    """Un nombre de archivo con ../ no debe devolver archivos fuera de las carpetas permitidas."""
    r = client.get(url)
    assert r.status_code in (400, 403, 404)
    assert b"fastapi" not in r.content
    assert b"SERVER_HOST" not in r.content


# ---------- 2. Ingesta de archivos anómalos ----------

@pytest.mark.parametrize(
    "filename,content,mime",
    [
        ("malicioso.txt", b"no soy una imagen", "text/plain"),
        ("vacio.jpg", b"", "image/jpeg"),
        ("corrupto.jpg", b"\xff\xd8\xff\xe0" + b"\x00\x01\x02\x03" * 5, "image/jpeg"),
    ],
)
def test_subida_archivos_ingesta_controlada(filename, content, mime):
    """Archivos no imagen, vacíos o corruptos deben responder de forma controlada sin error 500 ni fuga de trazas."""
    r = client.post(
        "/api/stock/upload",
        files={"files": (filename, io.BytesIO(content), mime)},
    )
    # Debe responder con código controlado (< 500)
    assert r.status_code < 500, f"Error no controlado en {filename}: {r.status_code}"
    # No debe filtrar rutas internas ni trazas de excepción de Python
    assert b"Traceback (most recent call last)" not in r.content
    assert b"site-packages" not in r.content
    if r.status_code == 200:
        res = r.json()
        assert res.get("faults_detected", 0) == 0


# ---------- 3. Control de .env y variables sensibles ----------

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


def test_env_example_sin_secretos():
    """El archivo .env.example debe contener solo plantillas o valores vacíos, sin credenciales reales."""
    example_path = ROOT / ".env.example"
    assert example_path.exists(), ".env.example debe existir en la raíz"
    content = example_path.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip()
            if key == "CAMERA_RTSP_URL":
                assert not val or "@" not in val, "CAMERA_RTSP_URL en .env.example no debe contener credenciales"
            if key == "ALERT_WEBHOOK_URL":
                assert not val or "hooks.slack.com" not in val, "ALERT_WEBHOOK_URL no debe ser un webhook real"


# ---------- 4. Escaneo de secretos en archivos versionados ----------

PATRONES_SECRETOS = [
    (re.compile(r'(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}'), "AWS Access Key"),
    (re.compile(r'gh[pousr]_[A-Za-z0-9_]{36,}'), "GitHub Token"),
    (re.compile(r'sk-[a-zA-Z0-9]{32,}'), "OpenAI API Key"),
    (re.compile(r'-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP)? PRIVATE KEY'), "Clave privada"),
    # URL RTSP con usuario:contraseña real (no ejemplos tipo 'usuario:clave' o '***:***')
    (re.compile(r'rtsp://(?!(?:usuario:clave|\*\*\*:\*\*\*))[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+@'), "RTSP con credenciales reales"),
    # Webhooks reales de Slack / Discord
    (re.compile(r'https://hooks\.slack\.com/services/T[0-9A-Z]{8,}/B[0-9A-Z]{8,}/[0-9A-Za-z]{20,}'), "Webhook Slack real"),
    (re.compile(r'https://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]{30,}'), "Webhook Discord real"),
]

EXTENSIONES_BINARIAS = {".pt", ".png", ".jpg", ".jpeg", ".pdf", ".docx", ".pptx", ".mdj", ".pyc"}


def test_escaneo_secretos_en_repo():
    """Recorre todos los archivos versionados en git y verifica ausencia de secretos reales."""
    try:
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.splitlines()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("git no disponible")

    hallazgos = []
    for rel_path in tracked:
        file_path = ROOT / rel_path
        if file_path.suffix.lower() in EXTENSIONES_BINARIAS or not file_path.exists():
            continue
        try:
            texto = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for patron, nombre in PATRONES_SECRETOS:
            if patron.search(texto):
                hallazgos.append(f"{rel_path}: {nombre}")

    assert not hallazgos, f"Se encontraron patrones de secretos en el repo: {hallazgos}"


# ---------- 5. Hallazgo CORS ----------

def test_cors_configuracion_hallazgo():
    """
    Revisa la configuración CORS en backend/app/main.py.
    Documenta el hallazgo si usa allow_origins=['*'] con allow_credentials=True.
    """
    main_code = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    usa_wildcard_origin = 'allow_origins=["*"]' in main_code or "allow_origins=['*']" in main_code
    usa_credentials = "allow_credentials=True" in main_code
    
    # Hallazgo documentado: CORS con comodín y credenciales representa un riesgo de seguridad en producción
    if usa_wildcard_origin and usa_credentials:
        # El hallazgo está confirmado y documentado
        assert True
    else:
        assert False, "La configuración CORS ha cambiado."
