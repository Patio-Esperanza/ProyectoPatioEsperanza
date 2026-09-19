import uuid

import pytest

from app.core.security import create_access_token
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


@pytest.mark.anyio
async def test_cliente_solicita_contenedor_con_patio_autoasignado(client, db_session):
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
