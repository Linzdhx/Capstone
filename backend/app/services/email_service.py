"""Entrega de alertas por correo mediante SMTP."""
from email.message import EmailMessage
import smtplib
from typing import Iterable, List, Optional

from backend.app.core.config import settings
from backend.app.core.logging import logger


class EmailAlertService:
    """Servicio único para enviar alertas de la API por correo."""

    def send_alert(
        self,
        subject: str,
        body: str,
        recipients: Optional[Iterable[str]] = None,
    ) -> bool:
        config = settings.alerts
        destination: List[str] = list(recipients or getattr(config, "email_recipients", []))
        sender = getattr(config, "email_from", "") or getattr(config, "email_smtp_username", "")

        if not getattr(config, "email_enabled", False):
            logger.info("Alerta por correo omitida: ALERT_EMAIL_ENABLED está desactivado.")
            return False
        if not getattr(config, "email_smtp_host", "") or not sender or not destination:
            raise RuntimeError(
                "Configuración de correo incompleta: se requieren host SMTP, remitente y destinatarios."
            )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = ", ".join(destination)
        message.set_content(body)

        try:
            smtp_ssl = getattr(config, "email_use_ssl", False)
            smtp_class = smtplib.SMTP_SSL if smtp_ssl else smtplib.SMTP
            with smtp_class(config.email_smtp_host, config.email_smtp_port, timeout=10) as smtp:
                if getattr(config, "email_use_tls", True) and not smtp_ssl:
                    smtp.starttls()
                if config.email_smtp_username:
                    smtp.login(config.email_smtp_username, config.email_smtp_password)
                smtp.send_message(message)
            logger.info("Alerta por correo enviada a %s.", ", ".join(destination))
            return True
        except (OSError, smtplib.SMTPException) as exc:
            logger.error("No se pudo enviar alerta por correo: %s", exc)
            raise RuntimeError(f"No se pudo enviar alerta por correo: {exc}") from exc


email_alert_service = EmailAlertService()
