import hmac
import hashlib
import logging
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.socio import CredencialSocio, EventoSocio
from app.models.contenedor import Contenedor

logger = logging.getLogger(__name__)


def generar_firma_hmac(payload_bytes: bytes, secreto: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    mac = hmac.new(secreto.encode("utf-8"), payload_bytes, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


async def registrar_evento_socio(
    db: AsyncSession,
    contenedor: Contenedor,
    tipo_evento: str,
) -> None:
    """Register an outbound webhook event for partner-created containers."""
    if not contenedor.credencial_socio_id:
        return

    payload = {
        "evento": tipo_evento,
        "contenedor_id": str(contenedor.id),
        "numero_contenedor": contenedor.numero_contenedor,
        "estado": contenedor.estado.value,
        "referencia_externa": contenedor.referencia_externa,
        "patio_id": str(contenedor.patio_id),
        "fecha": datetime.now(timezone.utc).isoformat(),
    }

    evento = EventoSocio(
        credencial_socio_id=contenedor.credencial_socio_id,
        contenedor_id=contenedor.id,
        tipo=tipo_evento,
        payload=payload,
        estado="pendiente",
        intentos=0,
        siguiente_intento_en=datetime.now(timezone.utc),
    )
    db.add(evento)


async def ejecutar_dispatch_webhooks_socio(db: AsyncSession) -> None:
    """Dispatch pending webhook events to partner endpoints."""
    now_utc = datetime.now(timezone.utc)
    stmt = (
        select(EventoSocio, CredencialSocio)
        .join(CredencialSocio, EventoSocio.credencial_socio_id == CredencialSocio.id)
        .where(
            EventoSocio.estado == "pendiente",
            EventoSocio.siguiente_intento_en <= now_utc,
            CredencialSocio.activo.is_(True),
            CredencialSocio.webhook_url.is_not(None),
        )
        .limit(50)
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        for evento, credencial in rows:
            import json
            payload_bytes = json.dumps(evento.payload, ensure_ascii=False, default=str).encode("utf-8")
            firma = generar_firma_hmac(payload_bytes, credencial.webhook_secreto or "")

            headers = {
                "Content-Type": "application/json",
                "X-Esperanza-Firma": firma,
                "X-Esperanza-Evento-Id": str(evento.id),
                "User-Agent": "PatioEsperanza-WebhookDispatcher/1.0",
            }

            try:
                response = await client.post(
                    credencial.webhook_url,
                    content=payload_bytes,
                    headers=headers,
                )
                if 200 <= response.status_code < 300:
                    evento.estado = "enviado"
                    evento.ultimo_error = None
                    logger.info("Webhook %s enviado exitosamente a socio %s (%s)", evento.id, credencial.nombre, credencial.webhook_url)
                else:
                    raise httpx.HTTPStatusError(
                        f"Status code {response.status_code}",
                        request=response.request,
                        response=response,
                    )
            except Exception as exc:
                evento.intentos += 1
                evento.ultimo_error = str(exc)
                if evento.intentos >= 5:
                    evento.estado = "fallido"
                    logger.error("Webhook %s falló definitivamente tras %d intentos: %s", evento.id, evento.intentos, exc)
                else:
                    # Exponential backoff: 2^intentos minutes
                    backoff_minutes = 2 ** evento.intentos
                    evento.siguiente_intento_en = now_utc + timedelta(minutes=backoff_minutes)
                    logger.warning("Webhook %s falló (intento %d), reintentando en %d minutos: %s", evento.id, evento.intentos, backoff_minutes, exc)

            await db.commit()
