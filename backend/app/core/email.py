import base64

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    ContentId,
    Disposition,
    FileContent,
    FileName,
    FileType,
    Mail,
)

from app.config import settings


def enviar_correo(
    destinatario: str,
    asunto: str,
    contenido_html: str,
    imagenes_inline: list[tuple[str, bytes, str]] | None = None,
) -> None:
    """Envía un correo HTML a un destinatario.

    `imagenes_inline` es una lista de tuplas `(content_id, png_bytes, nombre)`.
    El HTML las referencia como `cid:<content_id>`.
    """
    mensaje = Mail(
        from_email=settings.sendgrid_from_email,
        to_emails=destinatario,
        subject=asunto,
        html_content=contenido_html,
    )

    for cid, img_bytes, nombre in imagenes_inline or []:
        encoded = base64.b64encode(img_bytes).decode("utf-8")
        att = Attachment(
            FileContent(encoded),
            FileName(nombre),
            FileType("image/png"),
            Disposition("inline"),
            ContentId(cid),
        )
        mensaje.attachment = att

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
