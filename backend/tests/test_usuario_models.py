import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.cliente import Cliente
from app.models.enums import RolUsuario, TipoCliente
from app.models.ubicacion import Patio
from app.models.usuario import Usuario, UsuarioPatio


@pytest.mark.anyio
async def test_crea_usuario_interno_con_patio_asignado(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN")
    db_session.add(patio)
    await db_session.flush()

    usuario = Usuario(
        tipo=RolUsuario.OPERADOR,
        email="operador@patio.mx",
        password_hash="hash",
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()

    db_session.add(UsuarioPatio(usuario_id=usuario.id, patio_id=patio.id))
    await db_session.flush()

    result = await db_session.execute(select(Usuario).where(Usuario.id == usuario.id))
    assert result.scalar_one().tipo == RolUsuario.OPERADOR


@pytest.mark.anyio
async def test_crea_usuario_cliente_ligado_a_cliente(db_session):
    cliente = Cliente(
        razon_social="Agencia Aduanal Ejemplo SA de CV",
        rfc="AAE010101AA1",
        tipo=TipoCliente.AGENCIA_ADUANAL,
    )
    db_session.add(cliente)
    await db_session.flush()

    usuario = Usuario(
        tipo=RolUsuario.CLIENTE,
        cliente_id=cliente.id,
        email="contacto@agencia.mx",
        password_hash="hash",
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()
    assert usuario.cliente_id == cliente.id


@pytest.mark.anyio
async def test_email_duplicado_falla(db_session):
    db_session.add(
        Usuario(tipo=RolUsuario.ADMIN, email="dup@patio.mx", password_hash="h", activo=True)
    )
    await db_session.flush()
    db_session.add(
        Usuario(tipo=RolUsuario.ADMIN, email="dup@patio.mx", password_hash="h", activo=True)
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
