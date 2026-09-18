import uuid

import pytest

from app.core.security import create_access_token
from app.models.enums import RolUsuario
from app.models.ubicacion import Patio
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


async def _crear_patio(db_session, nombre: str, codigo: str) -> uuid.UUID:
    patio = Patio(nombre=nombre, codigo=codigo)
    db_session.add(patio)
    await db_session.commit()
    await db_session.refresh(patio)
    return patio.id


@pytest.mark.anyio
async def test_admin_crea_usuario_con_patios(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    patio_id = await _crear_patio(db_session, "Patio Norte", "PN")
    token = _token(RolUsuario.ADMIN)

    response = await client.post(
        "/api/usuarios",
        json={
            "nombre": "Juan Operador",
            "email": "juan@patio.mx",
            "password": "clave1234",
            "tipo": "operador",
            "patio_ids": [str(patio_id)],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "juan@patio.mx"
    assert body["tipo"] == "operador"
    assert [p["codigo"] for p in body["patios"]] == ["PN"]


@pytest.mark.anyio
async def test_operador_no_puede_crear_usuario(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.OPERADOR)
    token = _token(RolUsuario.OPERADOR)

    response = await client.post(
        "/api/usuarios",
        json={
            "nombre": "Otro",
            "email": "otro@patio.mx",
            "password": "clave1234",
            "tipo": "operador",
            "patio_ids": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_email_duplicado_devuelve_409(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    patio_id = await _crear_patio(db_session, "Patio Norte", "PN")
    token = _token(RolUsuario.ADMIN)
    payload = {
        "nombre": "Juan",
        "email": "duplicado@patio.mx",
        "password": "clave1234",
        "tipo": "operador",
        "patio_ids": [str(patio_id)],
    }

    primera = await client.post(
        "/api/usuarios", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert primera.status_code == 201

    segunda = await client.post(
        "/api/usuarios", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert segunda.status_code == 409


@pytest.mark.anyio
async def test_rol_no_admin_sin_patios_devuelve_422(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)

    response = await client.post(
        "/api/usuarios",
        json={
            "nombre": "Sin Patio",
            "email": "sinpatio@patio.mx",
            "password": "clave1234",
            "tipo": "supervisor",
            "patio_ids": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_admin_puede_crearse_sin_patios(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)

    response = await client.post(
        "/api/usuarios",
        json={
            "nombre": "Otro Admin",
            "email": "otroadmin@patio.mx",
            "password": "clave1234",
            "tipo": "admin",
            "patio_ids": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["patios"] == []


@pytest.mark.anyio
async def test_listar_usuarios_incluye_patios(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    patio_id = await _crear_patio(db_session, "Patio Sur", "PS")
    token = _token(RolUsuario.ADMIN)
    await client.post(
        "/api/usuarios",
        json={
            "nombre": "Ana",
            "email": "ana@patio.mx",
            "password": "clave1234",
            "tipo": "supervisor",
            "patio_ids": [str(patio_id)],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.get("/api/usuarios", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    ana = next(u for u in response.json() if u["email"] == "ana@patio.mx")
    assert [p["codigo"] for p in ana["patios"]] == ["PS"]
