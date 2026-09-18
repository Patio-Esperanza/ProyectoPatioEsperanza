import uuid

import pytest

from app.core.security import create_access_token
from app.models.enums import RolUsuario
from app.models.usuario import Usuario


_USUARIO_ID = "00000000-0000-0000-0000-000000000001"


def _token(rol: RolUsuario, patios: list[str] | None = None) -> str:
    return create_access_token(_USUARIO_ID, rol.value, patios or [], 60)


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


async def _crear_patio_carril_tramo_tira_ubicacion(client, admin_token, sufijo):
    patio = (
        await client.post(
            "/api/patios", json={"nombre": f"Patio {sufijo}", "codigo": f"P{sufijo}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()
    return patio


@pytest.mark.anyio
async def test_registrar_movimiento_ubica_contenedor(client, db_session):
    from app.models.ubicacion import Carril, Tira, Tramo, Ubicacion

    await _crear_usuario_autenticado(db_session)
    admin_token = _token(RolUsuario.ADMIN)
    patio = await _crear_patio_carril_tramo_tira_ubicacion(client, admin_token, "M1")

    carril = Carril(patio_id=patio["id"], codigo="A1", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()
    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo="A1-T1-S1-N1")
    db_session.add(ubicacion)
    await db_session.commit()

    op_token = _token(RolUsuario.OPERADOR, patios=[patio["id"]])
    contenedor_resp = await client.post(
        "/api/contenedores",
        json={
            "numero_contenedor": "CSQU3054383",
            "tipo": "lleno",
            "tamano": "40",
            "patio_id": patio["id"],
            "peso_kg": 18000,
        },
        headers={"Authorization": f"Bearer {op_token}"},
    )
    contenedor_id = contenedor_resp.json()["id"]

    response = await client.post(
        "/api/movimientos",
        json={
            "contenedor_id": contenedor_id,
            "ubicacion_destino_id": str(ubicacion.id),
            "tipo": "ingreso",
        },
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert response.status_code == 201

    verificar = await client.get(
        f"/api/contenedores/{contenedor_id}", headers={"Authorization": f"Bearer {op_token}"}
    )
    assert verificar.json()["estado"] == "ubicado"


@pytest.mark.anyio
async def test_no_permite_mover_a_slot_ocupado(client, db_session):
    from app.models.ubicacion import Carril, Tira, Tramo, Ubicacion

    await _crear_usuario_autenticado(db_session)
    admin_token = _token(RolUsuario.ADMIN)
    patio = await _crear_patio_carril_tramo_tira_ubicacion(client, admin_token, "M2")

    carril = Carril(patio_id=patio["id"], codigo="A1", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()
    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo="A1-T1-S1-N1")
    db_session.add(ubicacion)
    await db_session.commit()

    op_token = _token(RolUsuario.OPERADOR)

    async def _crear_y_mover(numero: str) -> int:
        contenedor_resp = await client.post(
            "/api/contenedores",
            json={
                "numero_contenedor": numero,
                "tipo": "lleno",
                "tamano": "40",
                "patio_id": patio["id"],
                "peso_kg": 18000,
            },
            headers={"Authorization": f"Bearer {op_token}"},
        )
        contenedor_id = contenedor_resp.json()["id"]
        mov = await client.post(
            "/api/movimientos",
            json={"contenedor_id": contenedor_id, "ubicacion_destino_id": str(ubicacion.id), "tipo": "ingreso"},
            headers={"Authorization": f"Bearer {op_token}"},
        )
        return mov.status_code

    primer_status = await _crear_y_mover("CSQU3054383")
    segundo_status = await _crear_y_mover("TRHU1866154")

    assert primer_status == 201
    assert segundo_status == 409
