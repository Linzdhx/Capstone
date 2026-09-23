import pytest
from backend.app.ml.model_manager import ModelManager

def test_model_manager_classes_and_info():
    """Verifica que el ModelManager detecte correctamente las clases del modelo best.pt."""
    mgr = ModelManager()
    info = mgr.get_info()
    assert info.version == "v001"
    # Clases requeridas
    classes = [v.lower() for v in info.classes.values()]
    assert "missing" in classes
    assert "product" in classes

def test_model_manager_threshold_update():
    """Verifica actualización de umbrales confidence e IoU."""
    mgr = ModelManager()
    res = mgr.update_thresholds(confidence=0.45, iou=0.60)
    assert res["confidence"] == 0.45
    assert res["iou"] == 0.60
    assert mgr.confidence_threshold == 0.45
    assert mgr.iou_threshold == 0.60

def test_model_manager_list_versions():
    """Verifica el listado de versiones."""
    mgr = ModelManager()
    versions = mgr.list_versions()
    assert "production" in versions
    assert len(versions["production"]) > 0
    assert versions["production"][0].status == "production"
