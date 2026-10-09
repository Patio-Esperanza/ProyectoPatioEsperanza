import uuid

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.enums import RolUsuario
from app.models.ubicacion import Carril, Tira, Tramo, Ubicacion
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


@pytest.mark.anyio
async def test_admin_configura_layout_de_patio(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Layout", "codigo": "PL1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    patio_id = creado.json()["id"]

    response = await client.post(
        f"/api/patios/{patio_id}/layout",
        json={"carriles": 2, "tramos": 1, "tiras": 1, "niveles": 3},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {"carriles_creados": 2, "carriles_saltados": 0, "ubicaciones_creadas": 6}


@pytest.mark.anyio
async def test_configurar_layout_es_idempotente_por_carril(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Layout 2", "codigo": "PL2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    patio_id = creado.json()["id"]
    payload = {"carriles": 2, "tramos": 1, "tiras": 1, "niveles": 2}
    await client.post(
        f"/api/patios/{patio_id}/layout", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.post(
        f"/api/patios/{patio_id}/layout", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "carriles_creados": 0,
        "carriles_saltados": 2,
        "ubicaciones_creadas": 0,
    }


@pytest.mark.anyio
async def test_operador_no_puede_configurar_layout(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    admin_token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Layout 3", "codigo": "PL3"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    patio_id = creado.json()["id"]

    op_token = _token(RolUsuario.OPERADOR)
    response = await client.post(
        f"/api/patios/{patio_id}/layout",
        json={"carriles": 1, "tramos": 1, "tiras": 1, "niveles": 1},
        headers={"Authorization": f"Bearer {op_token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_configurar_layout_patio_inexistente_404(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)

    response = await client.post(
        "/api/patios/00000000-0000-0000-0000-0000000000ff/layout",
        json={"carriles": 1, "tramos": 1, "tiras": 1, "niveles": 1},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_configurar_layout_niveles_fuera_de_rango_422(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Layout 4", "codigo": "PL4"},
        headers={"Authorization": f"Bearer {token}"},
    )
    patio_id = creado.json()["id"]

    response = await client.post(
        f"/api/patios/{patio_id}/layout",
        json={"carriles": 1, "tramos": 1, "tiras": 1, "niveles": 6},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


async def _crear_patio_con_layout(client, token, codigo="ENT", carriles=1):
    headers = {"Authorization": f"Bearer {token}"}
    creado = await client.post(
        "/api/patios", json={"nombre": f"Patio {codigo}", "codigo": codigo}, headers=headers,
    )
    patio_id = creado.json()["id"]
    layout = await client.post(
        f"/api/patios/{patio_id}/layout",
        json={"carriles": carriles, "tramos": 1, "tiras": 1, "niveles": 1}, headers=headers,
    )
    assert layout.status_code == 200
    return patio_id


async def _ubicacion_del_patio(db_session, patio_id: str, codigo: str) -> Ubicacion:
    result = await db_session.execute(
        select(Ubicacion)
        .join(Tira, Tira.id == Ubicacion.tira_id)
        .join(Tramo, Tramo.id == Tira.tramo_id)
        .join(Carril, Carril.id == Tramo.carril_id)
        .where(Carril.patio_id == uuid.UUID(patio_id), Ubicacion.codigo == codigo)
    )
    return result.scalars().one()


@pytest.mark.anyio
async def test_admin_fija_entrada_por_codigo(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    patio_id = await _crear_patio_con_layout(client, token)
    ubicacion = await _ubicacion_del_patio(db_session, patio_id, "A01-T01-R01-N1")

    response = await client.patch(
        f"/api/patios/{patio_id}/entrada", json={"codigo": "A01-T01-R01-N1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["ubicacion_entrada_id"] == str(ubicacion.id)


@pytest.mark.anyio
async def test_fijar_entrada_acepta_el_nivel_con_cero(client, db_session):
    """El nivel se guarda sin cero (N1), pero el admin lo teclea con cero.

    `A01-T01-R01-N01` describe la misma ubicación que `A01-T01-R01-N1`, así que
    el endpoint normaliza el código en vez de responder 404.
    """
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    patio_id = await _crear_patio_con_layout(client, token, codigo="ENTD")
    ubicacion = await _ubicacion_del_patio(db_session, patio_id, "A01-T01-R01-N1")

    response = await client.patch(
        f"/api/patios/{patio_id}/entrada", json={"codigo": "A01-T01-R01-N01"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["ubicacion_entrada_id"] == str(ubicacion.id)


@pytest.mark.anyio
async def test_fijar_entrada_acepta_segmentos_sin_cero_y_minusculas(client, db_session):
    """Los segmentos de carril, tramo y tira sí llevan cero: A01, no A1.

    El admin puede teclear cualquiera de las dos formas, en minúsculas y con
    espacios alrededor.
    """
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    patio_id = await _crear_patio_con_layout(client, token, codigo="ENTE")
    ubicacion = await _ubicacion_del_patio(db_session, patio_id, "A01-T01-R01-N1")

    response = await client.patch(
        f"/api/patios/{patio_id}/entrada", json={"codigo": "  a1-t1-r1-n1  "},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["ubicacion_entrada_id"] == str(ubicacion.id)


@pytest.mark.anyio
async def test_fijar_entrada_sin_nivel_pide_el_formato_completo(client, db_session):
    """Sin nivel el código no identifica una ubicación.

    El endpoint no puede adivinar el nivel, así que responde 422 y dice el
    formato esperado en vez de un 404 que parece decir que el patio está vacío.
    """
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    patio_id = await _crear_patio_con_layout(client, token, codigo="ENTF")

    response = await client.patch(
        f"/api/patios/{patio_id}/entrada", json={"codigo": "A01-T01-R01"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert "A01-T01-R01-N1" in response.text


@pytest.mark.anyio
async def test_fijar_entrada_con_codigo_inexistente_404(client, db_session):
    """Código bien formado que no existe en el patio: 404, no 422."""
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    patio_id = await _crear_patio_con_layout(client, token, codigo="ENTX")

    response = await client.patch(
        f"/api/patios/{patio_id}/entrada", json={"codigo": "A99-T99-R99-N9"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_fijar_entrada_con_codigo_malformado_422(client, db_session):
    """Un código que no tiene la forma del layout no es un 404 de ubicación."""
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    patio_id = await _crear_patio_con_layout(client, token, codigo="ENTY")

    response = await client.patch(
        f"/api/patios/{patio_id}/entrada", json={"codigo": "Z99-T99-R99-N9"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert "A01-T01-R01-N1" in response.text


@pytest.mark.anyio
async def test_fijar_entrada_con_codigo_de_otro_patio_404(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    patio_destino = await _crear_patio_con_layout(client, token, codigo="ENTA", carriles=1)
    patio_ajeno = await _crear_patio_con_layout(client, token, codigo="ENTB", carriles=2)

    # A02 solo existe en patio_ajeno, no en patio_destino.
    await _ubicacion_del_patio(db_session, patio_ajeno, "A02-T01-R01-N1")

    response = await client.patch(
        f"/api/patios/{patio_destino}/entrada", json={"codigo": "A02-T01-R01-N1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_operador_no_puede_fijar_entrada_403(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    admin_token = _token(RolUsuario.ADMIN)
    patio_id = await _crear_patio_con_layout(client, admin_token, codigo="ENTC")

    response = await client.patch(
        f"/api/patios/{patio_id}/entrada", json={"codigo": "A01-T01-R01-N1"},
        headers={"Authorization": f"Bearer {_token(RolUsuario.OPERADOR)}"},
    )

    assert response.status_code == 403
