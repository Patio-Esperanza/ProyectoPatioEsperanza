import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.socio_service import resolver_o_crear_cliente, validar_numero_contenedor
from app.models.enums import TipoCliente

@pytest.mark.anyio
async def test_resolver_o_crear_cliente_nuevo(db_session: AsyncSession):
    cliente = await resolver_o_crear_cliente(
        db_session,
        tipo=TipoCliente.IMPORTADOR_EXPORTADOR,
        rfc="IMM210702NL7",
        nombre="Importadora X S.A. de C.V."
    )
    await db_session.flush()
    assert cliente.id is not None
    assert cliente.alta_por_socio is True
    assert cliente.dias_libres == 0
    assert cliente.rfc == "IMM210702NL7"
    assert cliente.razon_social == "Importadora X S.A. de C.V."

@pytest.mark.anyio
async def test_resolver_o_crear_cliente_existente(db_session: AsyncSession):
    # Create first
    cliente1 = await resolver_o_crear_cliente(
        db_session,
        tipo=TipoCliente.AGENCIA_ADUANAL,
        rfc="AGN990101XX1",
        nombre="Agencia 1"
    )
    await db_session.flush()

    # Resolve again
    cliente2 = await resolver_o_crear_cliente(
        db_session,
        tipo=TipoCliente.AGENCIA_ADUANAL,
        rfc="AGN990101XX1",
        nombre="Agencia 1 Modificada"
    )
    await db_session.flush()
    assert cliente1.id == cliente2.id

def test_validar_numero_contenedor_valido():
    assert validar_numero_contenedor("MSCU1234567") is True
    assert validar_numero_contenedor("hlbu1234569") is True

def test_validar_numero_contenedor_invalido():
    assert validar_numero_contenedor("ABC1234567") is False
    assert validar_numero_contenedor("MSCU123") is False
    assert validar_numero_contenedor("12345678901") is False
