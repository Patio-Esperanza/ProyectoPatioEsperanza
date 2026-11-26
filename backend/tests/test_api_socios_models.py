import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.socio import CredencialSocio, EventoSocio
from app.models.contenedor import Contenedor
from app.models.cliente import Cliente
from app.models.ubicacion import Patio
from app.models.enums import TipoContenedor, TamanoContenedor, EstadoContenedor, TipoCliente

@pytest.mark.anyio
async def test_credencial_socio_model(db_session: AsyncSession):
    patio = Patio(nombre="Patio Norte", codigo="PN1")
    db_session.add(patio)
    await db_session.flush()

    socio = CredencialSocio(
        nombre="Kasu",
        prefijo="kasu0001",
        secreto_hash="hash",
        patios_permitidos=[patio.id],
        activo=True
    )
    db_session.add(socio)
    await db_session.flush()
    assert socio.id is not None
    assert socio.prefijo == "kasu0001"

@pytest.mark.anyio
async def test_contenedor_socio_extensions(db_session: AsyncSession):
    patio = Patio(nombre="Patio Sur", codigo="PS1")
    db_session.add(patio)
    await db_session.flush()

    socio = CredencialSocio(
        nombre="Kasu",
        prefijo="kasu0002",
        secreto_hash="hash",
        patios_permitidos=[patio.id],
        activo=True
    )
    db_session.add(socio)
    await db_session.flush()

    cliente = Cliente(
        razon_social="Cliente Socio",
        rfc="CSO010101AA1",
        tipo=TipoCliente.IMPORTADOR_EXPORTADOR,
        alta_por_socio=True
    )
    db_session.add(cliente)
    await db_session.flush()

    contenedor = Contenedor(
        numero_contenedor="CSQU3054383",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        patio_id=patio.id,
        cliente_id=cliente.id,
        estado=EstadoContenedor.SOLICITUD_INGRESO,
        peso_kg=18000,
        origen="api_socio",
        credencial_socio_id=socio.id,
        idempotency_key="idemp-123",
        referencia_externa="ref-ext-1",
        datos_aduana={"pedimento": "1234567"},
        transporte_esperado={"linea_transportista": "Transportes K", "economico": "E100"},
        peso_por_confirmar=False
    )
    db_session.add(contenedor)
    await db_session.flush()
    assert contenedor.id is not None
    assert contenedor.origen == "api_socio"
    assert contenedor.credencial_socio_id == socio.id
    assert contenedor.idempotency_key == "idemp-123"
