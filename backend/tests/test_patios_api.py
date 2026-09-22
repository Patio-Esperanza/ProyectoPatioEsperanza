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


@pytest.mark.anyio
async def test_admin_actualiza_anticipacion_minima(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Este", "codigo": "PE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    patio_id = creado.json()["id"]
    assert creado.json()["anticipacion_minima_horas"] == 24

    response = await client.patch(
        f"/api/patios/{patio_id}",
        json={"anticipacion_minima_horas": 48},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["anticipacion_minima_horas"] == 48


@pytest.mark.anyio
async def test_operador_no_puede_actualizar_patio(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    admin_token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Oeste", "codigo": "PO"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    patio_id = creado.json()["id"]

    op_token = _token(RolUsuario.OPERADOR)
    response = await client.patch(
        f"/api/patios/{patio_id}",
        json={"anticipacion_minima_horas": 48},
        headers={"Authorization": f"Bearer {op_token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_actualizar_patio_valor_invalido(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Centro", "codigo": "PC"},
        headers={"Authorization": f"Bearer {token}"},
    )
    patio_id = creado.json()["id"]

    response = await client.patch(
        f"/api/patios/{patio_id}",
        json={"anticipacion_minima_horas": 0},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_actualizar_patio_inexistente_404(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)

    response = await client.patch(
        "/api/patios/00000000-0000-0000-0000-0000000000ff",
        json={"anticipacion_minima_horas": 48},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_patio_expone_punto_de_entrada_nulo(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    await client.post(
        "/api/patios",
        json={"nombre": "Patio Entrada", "codigo": "PE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = await client.get("/api/patios", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    patio = next(p for p in response.json() if p["codigo"] == "PE")
    assert patio["ubicacion_entrada_id"] is None
