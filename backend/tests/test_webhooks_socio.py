import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import AsyncMock, patch

from app.jobs.webhooks_socio import generar_firma_hmac, ejecutar_dispatch_webhooks_socio, registrar_evento_socio
from app.models.socio import CredencialSocio, EventoSocio
from app.models.contenedor import Contenedor
from app.models.ubicacion import Patio
from app.models.cliente import Cliente
from app.models.enums import EstadoContenedor, TipoContenedor, TamanoContenedor, TipoCliente


def test_generar_firma_hmac():
    firma = generar_firma_hmac(b"test-payload", "mi-secreto")
    assert firma.startswith("sha256=")
    assert len(firma) > 10


@pytest.mark.asyncio
async def test_registrar_y_dispatch_webhook(db_session: AsyncSession):
    patio = Patio(nombre="Patio Test", codigo="PT1")
    db_session.add(patio)
    await db_session.flush()

    socio = CredencialSocio(
        nombre="Kasu",
        prefijo="kasuweb1",
        secreto_hash="hash",
        patios_permitidos=[patio.id],
        webhook_url="https://example.com/webhook",
        webhook_secreto="secreto-test",
        activo=True
    )
    db_session.add(socio)
    await db_session.flush()

    cliente = Cliente(
        tipo=TipoCliente.IMPORTADOR_EXPORTADOR,
        rfc="IMM210702NL7",
        razon_social="Importadora X",
        alta_por_socio=True
    )
    db_session.add(cliente)
    await db_session.flush()

    contenedor = Contenedor(
        numero_contenedor="MSCU9999991",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        patio_id=patio.id,
        cliente_id=cliente.id,
        peso_kg=18000,
        estado=EstadoContenedor.SOLICITUD_INGRESO,
        credencial_socio_id=socio.id
    )
    db_session.add(contenedor)
    await db_session.flush()

    await registrar_evento_socio(
        db_session,
        contenedor=contenedor,
        tipo_evento="contenedor.ingresado"
    )
    await db_session.commit()

    # Verify event created in outbox
    result = await db_session.execute(select(EventoSocio))
    evento = result.scalar_one()
    assert evento.estado == "pendiente"
    assert evento.tipo == "contenedor.ingresado"

    # Mock httpx.AsyncClient.post
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        await ejecutar_dispatch_webhooks_socio(db_session)
        await db_session.commit()

    # Verify event marked as enviado
    await db_session.refresh(evento)
    assert evento.estado == "enviado"
    assert mock_post.called
