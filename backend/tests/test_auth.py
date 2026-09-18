import pytest

from app.core.security import hash_password
from app.models.enums import RolUsuario
from app.models.ubicacion import Patio
from app.models.usuario import Usuario, UsuarioPatio


@pytest.mark.anyio
async def test_login_correcto_devuelve_token(client, db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN")
    db_session.add(patio)
    await db_session.flush()

    usuario = Usuario(
        tipo=RolUsuario.OPERADOR,
        email="operador@patio.mx",
        password_hash=hash_password("clave123"),
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()
    db_session.add(UsuarioPatio(usuario_id=usuario.id, patio_id=patio.id))
    await db_session.commit()

    response = await client.post(
        "/api/auth/login", data={"username": "operador@patio.mx", "password": "clave123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body


@pytest.mark.anyio
async def test_login_password_incorrecto_falla(client, db_session):
    usuario = Usuario(
        tipo=RolUsuario.OPERADOR,
        email="operador2@patio.mx",
        password_hash=hash_password("clave123"),
        activo=True,
    )
    db_session.add(usuario)
    await db_session.commit()

    response = await client.post(
        "/api/auth/login", data={"username": "operador2@patio.mx", "password": "incorrecta"}
    )
    assert response.status_code == 401
