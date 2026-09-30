import base64

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    Disposition,
    FileContent,
    FileName,
    FileType,
    Mail,
)

from app.config import settings


def enviar_correo(destinatario: str, asunto: str, contenido_html: str) -> None:
    mensaje = Mail(
        from_email=settings.sendgrid_from_email,
        to_emails=destinatario,
        subject=asunto,
        html_content=contenido_html,
    )
    cliente = SendGridAPIClient(settings.sendgrid_api_key)
    cliente.send(mensaje)


def enviar_correo_con_adjunto(
    destinatarios: list[str],
    asunto: str,
    contenido_html: str,
    adjunto_bytes: bytes,
    adjunto_nombre: str,
) -> None:
    """Envía un correo con un archivo adjunto a múltiples destinatarios."""
    mensaje = Mail(
        from_email=settings.sendgrid_from_email,
        to_emails=destinatarios,
        subject=asunto,
        html_content=contenido_html,
    )

    encoded = base64.b64encode(adjunto_bytes).decode("utf-8")
    attachment = Attachment(
        FileContent(encoded),
        FileName(adjunto_nombre),
        FileType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        Disposition("attachment"),
    )
    mensaje.attachment = attachment

    cliente = SendGridAPIClient(settings.sendgrid_api_key)
    cliente.send(mensaje)
