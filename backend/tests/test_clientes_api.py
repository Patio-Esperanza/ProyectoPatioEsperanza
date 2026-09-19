import uuid

import pytest

from app.core.security import create_access_token
from app.models.enums import RolUsuario
from app.models.usuario import Usuario

_USUARIO_ID = "00000000-0000-0000-0000-000000000001"


def _token(rol: RolUsuario) -> str:
    return create_access_token(_USUARIO_ID, rol.value, [], 60)


async def _crear_usuario_autenticado(db_session, rol: RolUsuario) -> None:
    db_session.add(
        Usuario(
            id=uuid.UUID(_USUARIO_ID),
            tipo=rol,
            email=f"{rol.value}@patio.mx",
            password_hash="hash",
            activo=True,
        )
    )
    await db_session.commit()


@pytest.mark.anyio
async def test_admin_crea_cliente(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)

    response = await client.post(
        "/api/clientes",
        json={"razon_social": "Importadora Demo", "rfc": "AAA010101AA1", "tipo": "importador_exportador"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["rfc"] == "AAA010101AA1"
    assert body["activo"] is True


@pytest.mark.anyio
async def test_operador_no_puede_crear_cliente(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.OPERADOR)
    token = _token(RolUsuario.OPERADOR)

    response = await client.post(
        "/api/clientes",
        json={"razon_social": "Importadora Demo", "rfc": "AAA010101AA2", "tipo": "importador_exportador"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_listar_clientes(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    await client.post(
        "/api/clientes",
        json={"razon_social": "Transportes Demo", "rfc": "AAA010101AA3", "tipo": "transportista"},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.get("/api/clientes", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert any(c["rfc"] == "AAA010101AA3" for c in response.json())
