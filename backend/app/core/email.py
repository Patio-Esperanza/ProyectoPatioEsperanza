from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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
