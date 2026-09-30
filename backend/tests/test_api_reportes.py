import uuid
from unittest.mock import patch

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
async def test_preview_requiere_autenticacion(client):
    response = await client.get("/api/reportes/containers-in-yard/preview")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_cliente_no_puede_ver_reportes(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.CLIENTE)
    token = _token(RolUsuario.CLIENTE)

    response = await client.get(
        "/api/reportes/containers-in-yard/preview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_operador_ve_preview_containers_en_patio(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.OPERADOR)
    token = _token(RolUsuario.OPERADOR)

    response = await client.get(
        "/api/reportes/containers-in-yard/preview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tipo"] == "containers-in-yard"
    assert "columnas" in body
    assert "kpis" in body


@pytest.mark.anyio
async def test_exportar_excel(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.SUPERVISOR)
    token = _token(RolUsuario.SUPERVISOR)

    response = await client.get(
        "/api/reportes/containers-in-yard/exportar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment" in response.headers["content-disposition"]


@pytest.mark.anyio
async def test_crud_reporte_programado(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    headers = {"Authorization": f"Bearer {token}"}

    # Crear
    response = await client.post(
        "/api/reportes/programados",
        json={
            "nombre": "Reporte Diario Test",
            "tipo_reporte": "containers-in-yard",
            "frecuencia": "diario",
            "hora": 8,
            "minuto": 30,
            "destinatarios": ["ops@empresa.com"],
            "asunto": "Reporte Diario",
        },
        headers=headers,
    )
    assert response.status_code == 201
    creado = response.json()
    prog_id = creado["id"]
    assert creado["nombre"] == "Reporte Diario Test"

    # Listar
    response = await client.get("/api/reportes/programados", headers=headers)
    assert response.status_code == 200
    assert any(p["id"] == prog_id for p in response.json())

    # Detalle
    response = await client.get(f"/api/reportes/programados/{prog_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == prog_id

    # Actualizar
    response = await client.patch(
        f"/api/reportes/programados/{prog_id}",
        json={"activo": False},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["activo"] is False

    # Eliminar
    response = await client.delete(f"/api/reportes/programados/{prog_id}", headers=headers)
    assert response.status_code == 204

    response = await client.get(f"/api/reportes/programados/{prog_id}", headers=headers)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_ejecutar_manual_reporte_programado(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/reportes/programados",
        json={
            "nombre": "Reporte Manual Test",
            "tipo_reporte": "containers-in-yard",
            "frecuencia": "diario",
            "hora": 8,
            "minuto": 30,
            "destinatarios": ["ops@empresa.com"],
            "asunto": "Reporte Manual",
        },
        headers=headers,
    )
    prog_id = response.json()["id"]

    with patch("app.services.reportes_scheduler.enviar_correo_con_adjunto") as mock_email:
        response = await client.post(
            f"/api/reportes/programados/{prog_id}/ejecutar", headers=headers
        )
        assert response.status_code == 200
        mock_email.assert_called_once()
