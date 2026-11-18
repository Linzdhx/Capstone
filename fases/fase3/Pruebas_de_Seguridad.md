# Pruebas de Seguridad — Computer Vision Walmart (CVW)

**Fase:** 3 · **Fecha de ejecución:** 18-11-2026 · **Rama analizada:** `main` (commit `e957b1f`)
**Responsable de la ejecución:** David Salvatierra

## 1. Alcance

| Área | Herramienta | Qué revisa |
|---|---|---|
| Código backend (Python) | `bandit 1.9.4` | Patrones inseguros en `backend/` (3.890 líneas, sin tests) |
| Dependencias Python | `pip-audit 2.10.1` | Vulnerabilidades conocidas en `requirements.txt` |
| Dependencias frontend | `npm audit` | Vulnerabilidades conocidas en `frontend/package-lock.json` |
| Secretos en el repo | `detect-secrets 1.5.0` + historial git | Claves, tokens o `.env` versionados |
| API en ejecución | `pytest` + `TestClient` (`backend/tests/test_security.py`) | Path traversal, subida de archivos no imagen, `.env` fuera de git |
| Configuración | Revisión manual | CORS, autenticación, bind de red |

Las salidas completas están en `fases/fase3/Evidencias/Seguridad/`.

## 2. Resultados

| # | Prueba | Resultado | Severidad |
|---|---|---|---|
| S-01 | bandit: severidad alta | 0 hallazgos | — |
| S-02 | bandit B104: servidor escucha en `0.0.0.0` (`backend/app/core/config.py:12`) | Esperado para Docker; en local conviene `127.0.0.1` | Media |
| S-03 | bandit B110: 10 bloques `try/except: pass` | Errores silenciados; dificulta auditar fallas | Baja |
| S-04 | pip-audit sobre `requirements.txt` | 0 vulnerabilidades conocidas | — |
| S-05 | npm audit: `vite 8.3.0` (directa) y `source-map-js` (indirecta) | 2 vulnerabilidades altas, con corrección disponible | Alta (solo desarrollo) |
| S-06 | detect-secrets | 2 alertas, ambas falsos positivos: ejemplo `rtsp://usuario:clave@...` en `README.md:263` y en el placeholder de `CameraPage.tsx:628` | — |
| S-07 | `.env` en git (archivo actual e historial) | No versionado; `.gitignore` lo excluye | — |
| S-08 | Path traversal con `..%2F` en `/api/stock/historica/image/` y `/api/dataset/images/` | Bloqueado (404) | — |
| S-09 | Subida de archivo no imagen a `/api/stock/upload` | Se descarta, sin error 500 ni falla registrada | — |
| S-10 | CORS | `allow_origins=["*"]` con `allow_credentials=True`: acepta cualquier origen | Media |
| S-11 | Autenticación de la API | No existe; cualquier equipo en la red puede usar los endpoints, incluido `POST /api/camera/add` | Alta (si se expone fuera de la red local) |
| S-12 | Path traversal con barra invertida (`..%5C`) en Windows | Posible, no verificado en Windows (ver 3.1) | Alta (a verificar) |

**Pruebas automáticas:** `backend/tests` pasa 20 de 20, incluidas las 7 nuevas de `test_security.py`.

## 3. Observaciones

### 3.1 Path traversal en Windows (S-12)
`_find_image_path()` (`incident_service.py`) y `get_dataset_image()` (`api/dataset.py`) arman la ruta con `carpeta / filename` sin validar el nombre. En Linux la prueba S-08 pasa porque `/` no entra en el parámetro. En Windows, `\` sí es separador de rutas, así que una petición como `GET /api/stock/historica/image/..%5C.env.example` podría devolver archivos fuera de `historica/`.

**Cómo verificarlo** (con la API corriendo en Windows):
```powershell
curl.exe http://localhost:8000/api/stock/historica/image/..%5C.env.example
```
Si responde 200 con el contenido del archivo, el riesgo está confirmado.

**Corrección propuesta:**
```python
from pathlib import Path

def _safe_join(folder: Path, filename: str) -> Path | None:
    if Path(filename).name != filename or "\\" in filename:
        return None
    cand = (folder / filename).resolve()
    return cand if cand.is_relative_to(folder.resolve()) else None
```

### 3.2 Dependencias del frontend (S-05)
Afectan al servidor de desarrollo de Vite, no al build de producción. Se corrigen con `npm audit fix` dentro de `frontend/` y luego volviendo a probar `npm run build`.

### 3.3 Límites de este análisis
- `requirements.txt` usa rangos (`>=`), así que pip-audit revisó las versiones más nuevas que resuelve hoy. Para auditar las versiones instaladas en cada equipo hay que correr `pip-audit` dentro del entorno virtual del proyecto.
- No se hicieron pruebas de carga, fuzzing ni pentesting.

## 4. Cómo repetir las pruebas
```bash
pip install bandit pip-audit detect-secrets
bandit -r backend -x backend/tests
pip-audit -r requirements.txt
detect-secrets scan --all-files
cd frontend && npm audit && cd ..
python -m pytest backend/tests/test_security.py -v
```

## 5. Acciones recomendadas

| Prioridad | Acción | Hallazgo |
|---|---|---|
| 1 | Validar nombres de archivo con `_safe_join` en los endpoints de imágenes | S-12 |
| 2 | Limitar CORS a la URL del frontend | S-10 |
| 3 | `npm audit fix` en `frontend/` | S-05 |
| 4 | API key simple para endpoints que modifican estado (cámaras, alertas) | S-11 |
| 5 | Registrar el error en vez de `pass` en los `except` | S-03 |
