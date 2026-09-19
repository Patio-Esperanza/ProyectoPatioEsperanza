from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.cliente import Cliente
from app.models.enums import TipoCliente
from app.models.usuario import Usuario


@pytest.fixture
def enviados(monkeypatch):
    capturados = []

    def _fake(destinatario, asunto, contenido_html):
        capturados.append((destinatario, asunto, contenido_html))

    monkeypatch.setattr("app.api.routes.clientes.enviar_correo", _fake)
    return capturados


async def _crear_cliente_activo(db_session, rfc: str) -> Cliente:
    cliente = Cliente(
        razon_social="Importadora Demo", rfc=rfc, tipo=TipoCliente.IMPORTADOR_EXPORTADOR, activo=True
    )
    db_session.add(cliente)
    await db_session.commit()
    await db_session.refresh(cliente)
    return cliente


@pytest.mark.anyio
async def test_registro_con_rfc_valido_crea_usuario_inactivo(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA1")

    response = await client.post(
        "/api/clientes/registro",
        json={"nombre": "Juan", "email": "juan@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA1"},
    )

    assert response.status_code == 201
    assert len(enviados) == 1
    assert enviados[0][0] == "juan@empresa.mx"

    result = await db_session.execute(select(Usuario).where(Usuario.email == "juan@empresa.mx"))
    usuario = result.scalar_one()
    assert usuario.activo is False
    assert usuario.cliente_id is not None
    assert usuario.codigo_verificacion is not None


@pytest.mark.anyio
async def test_registro_con_rfc_invalido_tambien_crea_usuario_inactivo(client, db_session, enviados):
    response = await client.post(
        "/api/clientes/registro",
        json={"nombre": "Juan", "email": "juan2@empresa.mx", "password": "clave1234", "rfc": "ZZZ999999ZZ9"},
    )

    assert response.status_code == 201
    assert len(enviados) == 1

    result = await db_session.execute(select(Usuario).where(Usuario.email == "juan2@empresa.mx"))
    usuario = result.scalar_one()
    assert usuario.activo is False
    assert usuario.cliente_id is None


@pytest.mark.anyio
async def test_verificar_con_codigo_correcto_y_rfc_valido_activa(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA2")
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Ana", "email": "ana@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA2"},
    )
    result = await db_session.execute(select(Usuario).where(Usuario.email == "ana@empresa.mx"))
    usuario = result.scalar_one()
    codigo = usuario.codigo_verificacion

    response = await client.post(
        "/api/clientes/verificar", json={"email": "ana@empresa.mx", "codigo": codigo}
    )

    assert response.status_code == 200
    assert response.json()["detail"] == "Cuenta activada"
    await db_session.refresh(usuario)
    assert usuario.activo is True
    assert usuario.codigo_verificacion is None


@pytest.mark.anyio
async def test_verificar_con_codigo_correcto_y_rfc_invalido_no_activa(client, db_session, enviados):
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Beto", "email": "beto@empresa.mx", "password": "clave1234", "rfc": "ZZZ999999ZZ8"},
    )
    result = await db_session.execute(select(Usuario).where(Usuario.email == "beto@empresa.mx"))
    usuario = result.scalar_one()
    codigo = usuario.codigo_verificacion

    response = await client.post(
        "/api/clientes/verificar", json={"email": "beto@empresa.mx", "codigo": codigo}
    )

    assert response.status_code == 200
    assert "no está registrada" in response.json()["detail"]
    await db_session.refresh(usuario)
    assert usuario.activo is False


@pytest.mark.anyio
async def test_verificar_con_codigo_incorrecto_falla(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA3")
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Cami", "email": "cami@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA3"},
    )

    response = await client.post(
        "/api/clientes/verificar", json={"email": "cami@empresa.mx", "codigo": "000000"}
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_verificar_con_codigo_expirado_falla(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA4")
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Dani", "email": "dani@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA4"},
    )
    result = await db_session.execute(select(Usuario).where(Usuario.email == "dani@empresa.mx"))
    usuario = result.scalar_one()
    codigo = usuario.codigo_verificacion
    usuario.codigo_verificacion_expira = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    response = await client.post(
        "/api/clientes/verificar", json={"email": "dani@empresa.mx", "codigo": codigo}
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_login_falla_mientras_no_esta_verificado(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA5")
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Eli", "email": "eli@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA5"},
    )

    response = await client.post(
        "/api/auth/login", data={"username": "eli@empresa.mx", "password": "clave1234"}
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_reregistro_de_email_inactivo_sobreescribe_codigo(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA6")
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Fer", "email": "fer@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA6"},
    )
    result = await db_session.execute(select(Usuario).where(Usuario.email == "fer@empresa.mx"))
    primer_codigo = result.scalar_one().codigo_verificacion

    response = await client.post(
        "/api/clientes/registro",
        json={"nombre": "Fer", "email": "fer@empresa.mx", "password": "clave5678", "rfc": "AAA010101AA6"},
    )

    assert response.status_code == 201
    assert len(enviados) == 2
    result = await db_session.execute(select(Usuario).where(Usuario.email == "fer@empresa.mx"))
    usuario = result.scalar_one()
    assert usuario.codigo_verificacion != primer_codigo


@pytest.mark.anyio
async def test_registro_con_email_ya_activo_devuelve_409(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA7")
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Gus", "email": "gus@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA7"},
    )
    result = await db_session.execute(select(Usuario).where(Usuario.email == "gus@empresa.mx"))
    usuario = result.scalar_one()
    codigo = usuario.codigo_verificacion
    await client.post("/api/clientes/verificar", json={"email": "gus@empresa.mx", "codigo": codigo})

    response = await client.post(
        "/api/clientes/registro",
        json={"nombre": "Gus", "email": "gus@empresa.mx", "password": "otraClave1", "rfc": "AAA010101AA7"},
    )

    assert response.status_code == 409
