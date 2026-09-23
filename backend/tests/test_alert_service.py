import time
import pytest
from pathlib import Path
from backend.app.services.alert_service import AlertService
from backend.app.schemas.inventory import InventoryMetrics

def test_alert_not_triggered_on_single_frame(tmp_path: Path):
    """Verifica que una condición de 80% en un único frame no dispare la alerta de inmediato."""
    service = AlertService(
        empty_threshold=0.80,
        consecutive_seconds=3.0,
        cooldown_seconds=30.0,
        images_dir=tmp_path / "images",
        logs_file=tmp_path / "alerts.jsonl"
    )

    high_metrics = InventoryMetrics(
        products=1, missing=4, total_spaces=5, occupancy_rate=0.2, empty_rate=0.8
    )

    # Frame 1
    event = service.evaluate(high_metrics)
    assert event is None
    status = service.get_status(high_metrics.empty_rate)
    assert status.is_active is False

def test_alert_triggered_after_consecutive_seconds(tmp_path: Path):
    """Verifica que se dispare tras permanecer por encima del umbral por 3 segundos."""
    service = AlertService(
        empty_threshold=0.80,
        consecutive_seconds=1.0,  # Reducido para acelerar el test
        cooldown_seconds=10.0,
        images_dir=tmp_path / "images",
        logs_file=tmp_path / "alerts.jsonl"
    )

    high_metrics = InventoryMetrics(
        products=1, missing=4, total_spaces=5, occupancy_rate=0.2, empty_rate=0.8
    )

    # Iniciar condición
    service.evaluate(high_metrics)
    time.sleep(1.05)

    # Segundo chequeo tras cumplirse el tiempo consecutivo
    event = service.evaluate(high_metrics)
    assert event is not None
    assert event.empty_rate == 0.8
    assert "Alerta de estantería vacía" in event.message

def test_alert_cooldown_prevents_spam(tmp_path: Path):
    """Verifica que tras una alerta, el cooldown impida emitir otra antes del tiempo."""
    service = AlertService(
        empty_threshold=0.80,
        consecutive_seconds=0.1,
        cooldown_seconds=10.0,
        images_dir=tmp_path / "images",
        logs_file=tmp_path / "alerts.jsonl"
    )

    high_metrics = InventoryMetrics(
        products=0, missing=5, total_spaces=5, occupancy_rate=0.0, empty_rate=1.0
    )

    # 1. Disparar primera alerta
    service.evaluate(high_metrics)
    time.sleep(0.12)
    ev1 = service.evaluate(high_metrics)
    assert ev1 is not None

    # 2. Inmediatamente después, no debe emitir otra alerta por estar en cooldown
    ev2 = service.evaluate(high_metrics)
    assert ev2 is None
    status = service.get_status(1.0)
    assert status.cooldown_remaining_seconds > 0.0

def test_alert_ignores_zero_spaces(tmp_path: Path):
    """Verifica que con 0 espacios totales no se compute alerta ni error."""
    service = AlertService(
        images_dir=tmp_path / "images",
        logs_file=tmp_path / "alerts.jsonl"
    )
    empty_metrics = InventoryMetrics(
        products=0, missing=0, total_spaces=0, occupancy_rate=0.0, empty_rate=0.0
    )
    ev = service.evaluate(empty_metrics)
    assert ev is None
