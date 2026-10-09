import pytest

from app.core.security import create_access_token, decode_access_token, hash_password
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


@pytest.mark.anyio
async def test_endpoint_protegido_sin_token_devuelve_401(client):
    response = await client.get("/api/patios")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_login_de_cliente_incluye_cliente_id_en_token(client, db_session):
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    cliente = Cliente(
        razon_social="Importadora Demo",
        rfc="AAA010101AA9",
        tipo=TipoCliente.IMPORTADOR_EXPORTADOR,
        activo=True,
    )
    db_session.add(cliente)
    await db_session.flush()

    usuario = Usuario(
        tipo=RolUsuario.CLIENTE,
        email="cliente@empresa.mx",
        password_hash=hash_password("clave123"),
        cliente_id=cliente.id,
        activo=True,
    )
    db_session.add(usuario)
    await db_session.commit()

    response = await client.post(
        "/api/auth/login", data={"username": "cliente@empresa.mx", "password": "clave123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    payload = decode_access_token(token)
    assert payload["cliente_id"] == str(cliente.id)


async def _crear_usuario(db_session, email: str, *, activo: bool = True, patios: int = 1):
    """Usuario operador con `patios` patios asignados. Devuelve (usuario, lista de patios)."""
    creados = []
    for indice in range(patios):
        patio = Patio(nombre=f"Patio {email} {indice}", codigo=f"{email[:2]}{indice}".upper())
        db_session.add(patio)
        creados.append(patio)
    await db_session.flush()

    usuario = Usuario(
        tipo=RolUsuario.OPERADOR,
        email=email,
        password_hash=hash_password("clave123"),
        activo=activo,
    )
    db_session.add(usuario)
    await db_session.flush()
    for patio in creados:
        db_session.add(UsuarioPatio(usuario_id=usuario.id, patio_id=patio.id))
    await db_session.commit()
    return usuario, creados


def _token_de(usuario, patios, *, expires_minutes: int = 240) -> str:
    return create_access_token(
        str(usuario.id),
        usuario.tipo.value,
        [str(p.id) for p in patios],
        expires_minutes,
    )


@pytest.mark.anyio
async def test_refresh_devuelve_token_nuevo(client, db_session):
    usuario, patios = await _crear_usuario(db_session, "refresh.ok@patio.mx")
    token = _token_de(usuario, patios)

    response = await client.post(
        "/api/auth/refresh", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    nuevo = decode_access_token(response.json()["access_token"])
    assert nuevo["sub"] == str(usuario.id)
    assert nuevo["rol"] == usuario.tipo.value
    assert nuevo["patios"] == [str(patios[0].id)]


@pytest.mark.anyio
async def test_refresh_acepta_token_recien_caducado(client, db_session):
    """Dentro de la ventana de gracia: el usuario volvió a la pestaña y aún puede continuar."""
    usuario, patios = await _crear_usuario(db_session, "refresh.gracia@patio.mx")
    token = _token_de(usuario, patios, expires_minutes=-2)

    response = await client.post(
        "/api/auth/refresh", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


@pytest.mark.anyio
async def test_refresh_rechaza_token_caducado_hace_mucho(client, db_session):
    """Sin ventana acotada el token sería eterno: a las 2 horas ya no se renueva."""
    usuario, patios = await _crear_usuario(db_session, "refresh.viejo@patio.mx")
    token = _token_de(usuario, patios, expires_minutes=-120)

    response = await client.post(
        "/api/auth/refresh", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_rechaza_usuario_desactivado(client, db_session):
    """Desactivar a alguien tiene que cortarle la sesión, no dejarlo renovar para siempre."""
    usuario, patios = await _crear_usuario(
        db_session, "refresh.inactivo@patio.mx", activo=False
    )
    token = _token_de(usuario, patios)

    response = await client.post(
        "/api/auth/refresh", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_relee_patios_de_la_base(client, db_session):
    """Los patios del token alimentan RLS: si cambia la asignación, el token nuevo la refleja."""
    usuario, patios = await _crear_usuario(db_session, "refresh.patios@patio.mx", patios=2)
    token = _token_de(usuario, patios)

    quitado = patios[1]
    await db_session.execute(
        UsuarioPatio.__table__.delete().where(
            UsuarioPatio.usuario_id == usuario.id, UsuarioPatio.patio_id == quitado.id
        )
    )
    await db_session.commit()

    response = await client.post(
        "/api/auth/refresh", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    nuevo = decode_access_token(response.json()["access_token"])
    assert nuevo["patios"] == [str(patios[0].id)]
    assert str(quitado.id) not in nuevo["patios"]


@pytest.mark.anyio
async def test_refresh_relee_el_rol_de_la_base(client, db_session):
    """Un rol degradado en la base no puede sobrevivir en el token renovado."""
    usuario, patios = await _crear_usuario(db_session, "refresh.rol@patio.mx")
    token = create_access_token(
        str(usuario.id), RolUsuario.ADMIN.value, [str(p.id) for p in patios], 240
    )

    response = await client.post(
        "/api/auth/refresh", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    nuevo = decode_access_token(response.json()["access_token"])
    assert nuevo["rol"] == RolUsuario.OPERADOR.value


@pytest.mark.anyio
async def test_refresh_rechaza_firma_invalida(client, db_session):
    usuario, patios = await _crear_usuario(db_session, "refresh.firma@patio.mx")
    token = _token_de(usuario, patios)

    response = await client.post(
        "/api/auth/refresh", headers={"Authorization": f"Bearer {token}alterado"}
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_rechaza_usuario_inexistente(client, db_session):
    import uuid

    token = create_access_token(str(uuid.uuid4()), RolUsuario.OPERADOR.value, [], 240)

    response = await client.post(
        "/api/auth/refresh", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_sin_header_devuelve_401(client):
    response = await client.post("/api/auth/refresh")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_con_esquema_equivocado_devuelve_401(client, db_session):
    usuario, patios = await _crear_usuario(db_session, "refresh.esquema@patio.mx")
    token = _token_de(usuario, patios)

    response = await client.post(
        "/api/auth/refresh", headers={"Authorization": f"Basic {token}"}
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_de_cliente_conserva_cliente_id(client, db_session):
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    cliente = Cliente(
        razon_social="Refresh Demo",
        rfc="BBB020202BB8",
        tipo=TipoCliente.IMPORTADOR_EXPORTADOR,
        activo=True,
    )
    db_session.add(cliente)
    await db_session.flush()

    usuario = Usuario(
        tipo=RolUsuario.CLIENTE,
        email="refresh.cliente@empresa.mx",
        password_hash=hash_password("clave123"),
        cliente_id=cliente.id,
        activo=True,
    )
    db_session.add(usuario)
    await db_session.commit()

    token = create_access_token(
        str(usuario.id), usuario.tipo.value, [], 240, cliente_id=str(cliente.id)
    )

    response = await client.post(
        "/api/auth/refresh", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    nuevo = decode_access_token(response.json()["access_token"])
    assert nuevo["cliente_id"] == str(cliente.id)
