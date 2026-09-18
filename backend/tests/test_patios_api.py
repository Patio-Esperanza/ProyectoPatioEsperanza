import uuid

import pytest

from app.core.security import create_access_token
from app.models.enums import RolUsuario
from app.models.usuario import Usuario

_USUARIO_ID = "00000000-0000-0000-0000-000000000001"


def _token(rol: RolUsuario, patios: list[str] | None = None) -> str:
    return create_access_token(_USUARIO_ID, rol.value, patios or [], 60)


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
async def test_admin_crea_patio(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    response = await client.post(
        "/api/patios",
        json={"nombre": "Patio Norte", "codigo": "PN"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["codigo"] == "PN"


@pytest.mark.anyio
async def test_operador_no_puede_crear_patio(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.OPERADOR)
    token = _token(RolUsuario.OPERADOR)
    response = await client.post(
        "/api/patios",
        json={"nombre": "Patio Norte", "codigo": "PN2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_listar_patios(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    await client.post(
        "/api/patios", json={"nombre": "Patio Sur", "codigo": "PS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = await client.get("/api/patios", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert any(p["codigo"] == "PS" for p in response.json())
