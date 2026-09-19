import uuid

import pytest

from app.core.security import create_access_token
from app.models.contenedor import Contenedor
from app.models.enums import RolUsuario
from app.models.usuario import Usuario


_USUARIO_ID = "00000000-0000-0000-0000-000000000001"


def _token(rol: RolUsuario) -> str:
    return create_access_token(_USUARIO_ID, rol.value, [], 60)


async def _crear_usuario_autenticado(db_session) -> None:
    db_session.add(
        Usuario(
            id=uuid.UUID(_USUARIO_ID),
            tipo=RolUsuario.ADMIN,
            email="admin@patio.mx",
            password_hash="hash",
            activo=True,
        )
    )
    await db_session.commit()


@pytest.mark.anyio
async def test_operador_crea_contenedor(client, db_session):
    await _crear_usuario_autenticado(db_session)
    admin_token = _token(RolUsuario.ADMIN)
    patio_resp = await client.post(
        "/api/patios", json={"nombre": "Patio Norte", "codigo": "PN"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    patio_id = patio_resp.json()["id"]

    op_token = _token(RolUsuario.OPERADOR)
    response = await client.post(
        "/api/contenedores",
        json={
            "numero_contenedor": "CSQU3054383",
            "tipo": "lleno",
            "tamano": "40",
            "patio_id": patio_id,
            "peso_kg": 18000,
        },
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["numero_contenedor"] == "CSQU3054383"
    assert body["estado"] == "solicitud_ingreso"


@pytest.mark.anyio
async def test_numero_contenedor_invalido_rechazado(client, db_session):
    await _crear_usuario_autenticado(db_session)
    admin_token = _token(RolUsuario.ADMIN)
    patio_resp = await client.post(
        "/api/patios", json={"nombre": "Patio Norte", "codigo": "PN2"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    patio_id = patio_resp.json()["id"]

    op_token = _token(RolUsuario.OPERADOR)
    response = await client.post(
        "/api/contenedores",
        json={
            "numero_contenedor": "CSQU3054380",
            "tipo": "lleno",
            "tamano": "40",
            "patio_id": patio_id,
            "peso_kg": 18000,
        },
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_cliente_no_puede_crear_contenedor(client, db_session):
    await _crear_usuario_autenticado(db_session)
    admin_token = _token(RolUsuario.ADMIN)
    patio_resp = await client.post(
        "/api/patios", json={"nombre": "Patio Norte", "codigo": "PN3"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    patio_id = patio_resp.json()["id"]

    cliente_token = _token(RolUsuario.CLIENTE)
    response = await client.post(
        "/api/contenedores",
        json={
            "numero_contenedor": "CSQU3054383",
            "tipo": "lleno",
            "tamano": "40",
            "patio_id": patio_id,
            "peso_kg": 18000,
        },
        headers={"Authorization": f"Bearer {cliente_token}"},
    )
    assert response.status_code == 403


async def _crear_patio(db_session, nombre: str, codigo: str):
    from app.models.ubicacion import Patio

    patio = Patio(nombre=nombre, codigo=codigo, activo=True)
    db_session.add(patio)
    await db_session.commit()
    await db_session.refresh(patio)
    return patio


async def _crear_cliente(db_session, rfc: str):
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    cliente = Cliente(
        razon_social="Importadora Demo", rfc=rfc, tipo=TipoCliente.IMPORTADOR_EXPORTADOR, activo=True
    )
    db_session.add(cliente)
    await db_session.commit()
    await db_session.refresh(cliente)
    return cliente


@pytest.fixture
def enviados_pin(monkeypatch):
    capturados = []

    def _fake(destinatario, asunto, contenido_html):
        capturados.append((destinatario, asunto, contenido_html))

    monkeypatch.setattr("app.api.routes.contenedores.enviar_correo", _fake)
    return capturados


@pytest.mark.anyio
async def test_cliente_solicita_contenedor_con_patio_autoasignado(client, db_session, enviados_pin):
    patio = await _crear_patio(db_session, "Patio Norte", "PN4")
    cliente = await _crear_cliente(db_session, "AAA010101AA1")
    db_session.add(
        Usuario(
            id=uuid.UUID(_USUARIO_ID),
            tipo=RolUsuario.CLIENTE,
            email="cliente@empresa.mx",
            password_hash="hash",
            cliente_id=cliente.id,
            activo=True,
        )
    )
    await db_session.commit()
    token = create_access_token(_USUARIO_ID, "cliente", [], 60, cliente_id=str(cliente.id))

    response = await client.post(
        "/api/contenedores/solicitar",
        json={
            "numero_contenedor": "CSQU3054383",
            "tipo": "lleno",
            "tamano": "40",
            "peso_kg": 18000,
            "fecha_estimada_retiro": "2026-10-01",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["estado"] == "solicitud_ingreso"
    assert body["patio_id"] == str(patio.id)
    assert body["fecha_estimada_retiro"].startswith("2026-10-01")


@pytest.mark.anyio
async def test_operador_no_puede_solicitar_contenedor(client, db_session):
    await _crear_usuario_autenticado(db_session)
    token = _token(RolUsuario.OPERADOR)

    response = await client.post(
        "/api/contenedores/solicitar",
        json={"numero_contenedor": "CSQU3054383", "tipo": "lleno", "tamano": "40", "peso_kg": 18000},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_solicitar_genera_pin_y_envia_correo(client, db_session, enviados_pin):
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    patio = await _crear_patio(db_session, "Patio Norte", "PN5")
    cliente = Cliente(
        razon_social="Importadora PIN", rfc="BBB020202BB2", tipo=TipoCliente.IMPORTADOR_EXPORTADOR, activo=True
    )
    db_session.add(cliente)
    await db_session.commit()
    await db_session.refresh(cliente)
    db_session.add(
        Usuario(
            id=uuid.UUID(_USUARIO_ID),
            tipo=RolUsuario.CLIENTE,
            email="pin-cliente@empresa.mx",
            password_hash="hash",
            cliente_id=cliente.id,
            activo=True,
        )
    )
    await db_session.commit()
    token = create_access_token(_USUARIO_ID, "cliente", [], 60, cliente_id=str(cliente.id))

    response = await client.post(
        "/api/contenedores/solicitar",
        json={
            "numero_contenedor": "CSQU3054383",
            "tipo": "lleno",
            "tamano": "40",
            "peso_kg": 18000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert "pin_confirmacion" not in response.json()
    assert len(enviados_pin) == 1
    destinatario, asunto, contenido = enviados_pin[0]
    assert destinatario == "pin-cliente@empresa.mx"
    assert "PIN" in asunto

    from sqlalchemy import select as sa_select

    result = await db_session.execute(
        sa_select(Contenedor).where(Contenedor.numero_contenedor == "CSQU3054383")
    )
    contenedor = result.scalar_one()
    assert contenedor.pin_confirmacion is not None
    assert len(contenedor.pin_confirmacion) == 4
    assert contenedor.pin_confirmacion.isdigit()
    assert contenedor.pin_confirmacion in contenido


async def _crear_solicitud_con_pin(client, db_session, usuario_id: str, cliente_rfc: str, numero: str):
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    patio = await _crear_patio(db_session, f"Patio {numero}", numero[:6])
    cliente = Cliente(
        razon_social="Importadora Test", rfc=cliente_rfc, tipo=TipoCliente.IMPORTADOR_EXPORTADOR, activo=True
    )
    db_session.add(cliente)
    await db_session.commit()
    await db_session.refresh(cliente)
    db_session.add(
        Usuario(
            id=uuid.UUID(usuario_id),
            tipo=RolUsuario.CLIENTE,
            email=f"{usuario_id}@empresa.mx",
            password_hash="hash",
            cliente_id=cliente.id,
            activo=True,
        )
    )
    await db_session.commit()
    token = create_access_token(usuario_id, "cliente", [], 60, cliente_id=str(cliente.id))

    response = await client.post(
        "/api/contenedores/solicitar",
        json={"numero_contenedor": numero, "tipo": "lleno", "tamano": "40", "peso_kg": 18000},
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()["id"], cliente


@pytest.mark.anyio
async def test_admin_ve_pin(client, db_session, enviados_pin):
    await _crear_usuario_autenticado(db_session)
    admin_token = _token(RolUsuario.ADMIN)
    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000002", "CCC030303CC3", "CSQU3053849"
    )

    response = await client.get(
        f"/api/contenedores/{contenedor_id}/pin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert len(response.json()["pin_confirmacion"]) == 4


@pytest.mark.anyio
async def test_cliente_dueno_ve_pin(client, db_session, enviados_pin):
    contenedor_id, cliente = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000003", "DDD040404DD4", "CSQU3053854"
    )
    token = create_access_token(
        "00000000-0000-0000-0000-000000000003", "cliente", [], 60, cliente_id=str(cliente.id)
    )

    response = await client.get(
        f"/api/contenedores/{contenedor_id}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(response.json()["pin_confirmacion"]) == 4


@pytest.mark.anyio
async def test_cliente_de_otra_empresa_no_ve_pin(client, db_session, enviados_pin):
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000004", "EEE050505EE5", "CSQU3053860"
    )

    otro_cliente = Cliente(
        razon_social="Otra Empresa", rfc="FFF060606FF6", tipo=TipoCliente.TRANSPORTISTA, activo=True
    )
    db_session.add(otro_cliente)
    await db_session.commit()
    await db_session.refresh(otro_cliente)
    otro_token = create_access_token(
        "00000000-0000-0000-0000-000000000005", "cliente", [], 60, cliente_id=str(otro_cliente.id)
    )
    db_session.add(
        Usuario(
            id=uuid.UUID("00000000-0000-0000-0000-000000000005"),
            tipo=RolUsuario.CLIENTE,
            email="otro@empresa.mx",
            password_hash="hash",
            cliente_id=otro_cliente.id,
            activo=True,
        )
    )
    await db_session.commit()

    response = await client.get(
        f"/api/contenedores/{contenedor_id}/pin",
        headers={"Authorization": f"Bearer {otro_token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_operador_no_ve_pin(client, db_session, enviados_pin):
    await _crear_usuario_autenticado(db_session)
    op_token = _token(RolUsuario.OPERADOR)
    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000006", "GGG070707GG7", "CSQU3053875"
    )

    response = await client.get(
        f"/api/contenedores/{contenedor_id}/pin",
        headers={"Authorization": f"Bearer {op_token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_pin_de_contenedor_inexistente_404(client, db_session):
    await _crear_usuario_autenticado(db_session)
    admin_token = _token(RolUsuario.ADMIN)

    response = await client.get(
        "/api/contenedores/00000000-0000-0000-0000-0000000000ff/pin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_operador_verifica_pin_correcto(client, db_session, enviados_pin):
    from sqlalchemy import select as sa_select

    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000007", "HHH080808HH8", "CSQU3053880"
    )
    result = await db_session.execute(sa_select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one()
    pin_real = contenedor.pin_confirmacion

    await _crear_usuario_autenticado(db_session)
    op_token = _token(RolUsuario.OPERADOR)

    response = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3053880", "pin": pin_real},
        headers={"Authorization": f"Bearer {op_token}"},
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "en_porteria"

    await db_session.refresh(contenedor)
    assert contenedor.pin_verificado_en is not None
    assert str(contenedor.pin_verificado_por) == "00000000-0000-0000-0000-000000000001"


@pytest.mark.anyio
async def test_verificar_pin_incorrecto_422(client, db_session, enviados_pin):
    await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000008", "III090909II9", "CSQU3053896"
    )
    await _crear_usuario_autenticado(db_session)
    op_token = _token(RolUsuario.OPERADOR)

    response = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3053896", "pin": "0000"},
        headers={"Authorization": f"Bearer {op_token}"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "PIN incorrecto"


@pytest.mark.anyio
async def test_verificar_pin_numero_inexistente_404(client, db_session):
    await _crear_usuario_autenticado(db_session)
    op_token = _token(RolUsuario.OPERADOR)

    response = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3053999", "pin": "1234"},
        headers={"Authorization": f"Bearer {op_token}"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_verificar_pin_estado_no_pendiente_409(client, db_session, enviados_pin):
    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-00000000000a", "JJJ101010JJ1", "CSQU3053900"
    )
    from sqlalchemy import select as sa_select

    result = await db_session.execute(sa_select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one()
    pin_real = contenedor.pin_confirmacion

    await _crear_usuario_autenticado(db_session)
    op_token = _token(RolUsuario.OPERADOR)

    primera = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3053900", "pin": pin_real},
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert primera.status_code == 200

    segunda = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3053900", "pin": pin_real},
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert segunda.status_code == 409


@pytest.mark.anyio
async def test_cliente_no_puede_verificar_pin(client, db_session, enviados_pin):
    contenedor_id, cliente = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-00000000000b", "KKK111111KK1", "CSQU3053915"
    )
    token = create_access_token(
        "00000000-0000-0000-0000-00000000000b", "cliente", [], 60, cliente_id=str(cliente.id)
    )

    response = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3053915", "pin": "1234"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_listar_contenedores_cliente_solo_ve_los_suyos(client, db_session, enviados_pin):
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    _, cliente_a = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-00000000000c", "LLL121212LL1", "CSQU3060010"
    )
    otro_cliente = Cliente(
        razon_social="Otra Importadora", rfc="MMM131313MM1", tipo=TipoCliente.TRANSPORTISTA, activo=True
    )
    db_session.add(otro_cliente)
    await db_session.commit()
    await db_session.refresh(otro_cliente)
    db_session.add(
        Usuario(
            id=uuid.UUID("00000000-0000-0000-0000-00000000000d"),
            tipo=RolUsuario.CLIENTE,
            email="otro-listado@empresa.mx",
            password_hash="hash",
            cliente_id=otro_cliente.id,
            activo=True,
        )
    )
    await db_session.commit()
    otro_token = create_access_token(
        "00000000-0000-0000-0000-00000000000d", "cliente", [], 60, cliente_id=str(otro_cliente.id)
    )
    await client.post(
        "/api/contenedores/solicitar",
        json={"numero_contenedor": "CSQU3060025", "tipo": "lleno", "tamano": "40", "peso_kg": 18000},
        headers={"Authorization": f"Bearer {otro_token}"},
    )

    token_a = create_access_token(
        "00000000-0000-0000-0000-00000000000c", "cliente", [], 60, cliente_id=str(cliente_a.id)
    )
    response = await client.get("/api/contenedores", headers={"Authorization": f"Bearer {token_a}"})

    assert response.status_code == 200
    numeros = [c["numero_contenedor"] for c in response.json()]
    assert numeros == ["CSQU3060010"]


@pytest.mark.anyio
async def test_listar_contenedores_staff_filtra_por_estado_ordenado_por_fecha(client, db_session, enviados_pin):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select as sa_select

    contenedor_id_1, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-00000000000e", "NNN141414NN1", "CSQU3060030"
    )
    contenedor_id_2, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-00000000000f", "OOO151515OO1", "TCLU3060465"
    )

    result1 = await db_session.execute(sa_select(Contenedor).where(Contenedor.id == contenedor_id_1))
    c1 = result1.scalar_one()
    c1.estado = "solicitud_salida"
    c1.fecha_deseada_salida = datetime.now(timezone.utc) + timedelta(days=5)

    result2 = await db_session.execute(sa_select(Contenedor).where(Contenedor.id == contenedor_id_2))
    c2 = result2.scalar_one()
    c2.estado = "solicitud_salida"
    c2.fecha_deseada_salida = datetime.now(timezone.utc) + timedelta(days=1)
    await db_session.commit()

    await _crear_usuario_autenticado(db_session)
    admin_token = _token(RolUsuario.ADMIN)

    response = await client.get(
        "/api/contenedores?estado=solicitud_salida",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    ids = [c["id"] for c in response.json()]
    assert ids == [str(contenedor_id_2), str(contenedor_id_1)]
