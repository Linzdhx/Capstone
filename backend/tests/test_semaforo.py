from backend.app.services.semaforo_service import clasificar, Semaforo
from backend.app.services.inventory_service import InventoryService
from backend.app.schemas.detection import DetectionItem


# ---------- Paso 1: lógica del semáforo ----------

def test_sin_datos():
    assert clasificar(0.0, 0) == Semaforo.SIN_DATOS

def test_rojo_limite():
    assert clasificar(0.20, 10) == Semaforo.ROJO
    assert clasificar(0.0, 10) == Semaforo.ROJO

def test_amarillo():
    assert clasificar(0.21, 100) == Semaforo.AMARILLO
    assert clasificar(0.40, 10) == Semaforo.AMARILLO

def test_verde():
    assert clasificar(0.41, 100) == Semaforo.VERDE
    assert clasificar(1.0, 10) == Semaforo.VERDE


# ---------- Paso 2: integración con el inventario ----------

def _det(clase):
    return DetectionItem(class_id=0, class_name=clase, confidence=0.9, box=[0, 0, 10, 10])

def test_inventario_devuelve_rojo():
    # 1 producto y 4 vacíos -> 20 % de stock -> rojo
    dets = [_det("product")] + [_det("missing")] * 4
    metrics = InventoryService().calculate_metrics(dets)
    assert metrics.semaforo == "rojo"

def test_inventario_devuelve_verde():
    # 3 productos y 1 vacío -> 75 % de stock -> verde
    dets = [_det("product")] * 3 + [_det("missing")]
    metrics = InventoryService().calculate_metrics(dets)
    assert metrics.semaforo == "verde"