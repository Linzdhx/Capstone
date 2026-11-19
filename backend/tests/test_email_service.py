from types import SimpleNamespace

import pytest

from backend.app.core.config import settings
from backend.app.services.email_service import EmailAlertService


def test_email_alert_service_sends_using_configured_smtp(monkeypatch):
    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("smtp.test", 587, 10)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def starttls(self):
            pass

        def login(self, username, password):
            assert (username, password) == ("user", "secret")

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr("backend.app.services.email_service.smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr(
        "backend.app.services.email_service.settings",
        SimpleNamespace(
            alerts=SimpleNamespace(
                email_enabled=True,
                email_smtp_host="smtp.test",
                email_smtp_port=587,
                email_smtp_username="user",
                email_smtp_password="secret",
                email_from="alerts@test",
                email_recipients=["ops@test"],
                email_use_tls=True,
                email_use_ssl=False,
            )
        ),
    )

    assert EmailAlertService().send_alert("Critical", "Gondola crítica") is True
    assert sent_messages[0]["Subject"] == "Critical"
    assert sent_messages[0]["To"] == "ops@test"
    assert sent_messages[0].get_content().strip() == "Gondola crítica"


def test_email_alert_service_rejects_incomplete_configuration(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.email_service.settings",
        SimpleNamespace(
            alerts=SimpleNamespace(
                email_enabled=True,
                email_smtp_host="",
                email_smtp_username="",
                email_recipients=[],
            )
        ),
    )

    with pytest.raises(RuntimeError, match="Configuración de correo incompleta"):
        EmailAlertService().send_alert("Critical", "Gondola crítica")
