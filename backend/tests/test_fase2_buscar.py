import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.core.ubicaciones import etiqueta_ubicacion
from app.models.enums import RolUsuario
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
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
async def test_global_search_requires_minimum_characters(client: AsyncClient, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    response = await client.get(
        "/api/buscar?q=MSC",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_global_search_works_with_four_characters(client: AsyncClient, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)

    from app.models.contenedor import Contenedor
    from app.models.enums import EstadoContenedor, TamanoContenedor, TipoContenedor

    patio = Patio(
        nombre="Patio Test",
        codigo="PT",
        timezone="America/Mexico_City",
    )
    db_session.add(patio)
    await db_session.flush()

    carril = Carril(patio_id=patio.id, codigo="A01", orden=1)
    db_session.add(carril)
    await db_session.flush()

    tramo = Tramo(carril_id=carril.id, codigo="T01", orden=1)
    db_session.add(tramo)
    await db_session.flush()

    tira = Tira(tramo_id=tramo.id, codigo="R01", orden=1)
    db_session.add(tira)
    await db_session.flush()

    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo="A01-T01-R01-N1")
    db_session.add(ubicacion)
    await db_session.flush()

    contenedor = Contenedor(
        numero_contenedor="MSCU1234567",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.VEINTE,
        patio_id=patio.id,
        estado=EstadoContenedor.UBICADO,
        peso_kg=20000,
        ubicacion_id=ubicacion.id,
    )
    db_session.add(contenedor)
    await db_session.commit()

    response = await client.get(
        f"/api/buscar?q=MSCU&patio_id={patio.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["numero_contenedor"] == "MSCU1234567"
    assert "ubicacion_etiqueta" in data[0]


def test_etiqueta_ubicacion_corta():
    ubicacion = Ubicacion(
        id="00000000-0000-0000-0000-000000000001",
        tira_id="00000000-0000-0000-0000-000000000002",
        nivel=1,
        codigo="A01-T01-R01-N1",
    )
    etiqueta = etiqueta_ubicacion(ubicacion)
    assert etiqueta.corta == "A01-T01-R01-N1"
    assert etiqueta.larga == "Carril A01 · Tramo T01 · Tira R01 · Nivel 1"


def test_etiqueta_ubicacion_con_nivel_mayor():
    ubicacion = Ubicacion(
        id="00000000-0000-0000-0000-000000000001",
        tira_id="00000000-0000-0000-0000-000000000002",
        nivel=3,
        codigo="A05-T10-R02-N3",
    )
    etiqueta = etiqueta_ubicacion(ubicacion)
    assert etiqueta.corta == "A05-T10-R02-N3"
    assert etiqueta.larga == "Carril A05 · Tramo T10 · Tira R02 · Nivel 3"
