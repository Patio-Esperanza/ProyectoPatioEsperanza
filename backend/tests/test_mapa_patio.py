import uuid

import pytest

from app.core.security import create_access_token
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, RolUsuario, TamanoContenedor, TipoContenedor
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
from app.models.usuario import Usuario
from app.services.mapa_patio import obtener_mapa

_USUARIO_ID = "00000000-0000-0000-0000-000000000051"


def _token(rol: RolUsuario, patios: list[str] | None = None) -> str:
    return create_access_token(_USUARIO_ID, rol.value, patios or [], 60)


async def _crear_usuario(db_session, rol: RolUsuario) -> None:
    db_session.add(
        Usuario(
            id=uuid.UUID(_USUARIO_ID),
            tipo=rol,
            email=f"mapa-{rol.value}@patio.mx",
            password_hash="hash",
            activo=True,
        )
    )
    await db_session.commit()


async def _crear_layout(db_session, sufijo: str) -> tuple[Patio, Tira, list[Ubicacion]]:
    """Un patio con un carril, un tramo, una tira y tres niveles.

    El nivel 3 queda inactivo, para poder distinguir niveles_totales de niveles_activos.
    """
    patio = Patio(nombre=f"Patio {sufijo}", codigo=f"MP{sufijo}")
    db_session.add(patio)
    await db_session.flush()

    carril = Carril(patio_id=patio.id, codigo="A1", orden=0, tipo_teorico=TipoContenedor.LLENO)
    db_session.add(carril)
    await db_session.flush()

    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()

    tira = Tira(tramo_id=tramo.id, codigo="R1", orden=0)
    db_session.add(tira)
    await db_session.flush()

    ubicaciones = [
        Ubicacion(tira_id=tira.id, nivel=1, codigo="A1-T1-R1-N1", activo=True),
        Ubicacion(tira_id=tira.id, nivel=2, codigo="A1-T1-R1-N2", activo=True),
        Ubicacion(tira_id=tira.id, nivel=3, codigo="A1-T1-R1-N3", activo=False),
    ]
    db_session.add_all(ubicaciones)
    await db_session.commit()
    return patio, tira, ubicaciones


@pytest.mark.anyio
async def test_obtener_mapa_cuenta_niveles_totales_activos_y_ocupados(db_session):
    patio, _tira, ubicaciones = await _crear_layout(db_session, "A")
    db_session.add(
        Contenedor(
            numero_contenedor="CAIU1112223",
            tipo=TipoContenedor.LLENO,
            tamano=TamanoContenedor.CUARENTA,
            patio_id=patio.id,
            ubicacion_id=ubicaciones[0].id,
            estado=EstadoContenedor.UBICADO,
            peso_kg=28000,
        )
    )
    await db_session.commit()

    mapa = await obtener_mapa(db_session, patio.id)

    assert len(mapa.carriles) == 1
    tira_out = mapa.carriles[0].tramos[0].tiras[0]
    assert tira_out.niveles_totales == 3
    assert tira_out.niveles_activos == 2
    assert tira_out.niveles_ocupados == 1
    assert mapa.resumen.ubicaciones_activas == 2
    assert mapa.resumen.ocupadas == 1


@pytest.mark.anyio
async def test_endpoint_mapa_devuelve_la_jerarquia(client, db_session):
    await _crear_usuario(db_session, RolUsuario.OPERADOR)
    patio, _tira, _ubicaciones = await _crear_layout(db_session, "B")
    token = _token(RolUsuario.OPERADOR, [str(patio.id)])

    response = await client.get(
        f"/api/patios/{patio.id}/mapa", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["carriles"][0]["codigo"] == "A1"
    assert cuerpo["carriles"][0]["tramos"][0]["tiras"][0]["niveles_totales"] == 3
    assert cuerpo["ubicacion_entrada_id"] is None


@pytest.mark.anyio
async def test_endpoint_mapa_rechaza_al_cliente(client, db_session):
    await _crear_usuario(db_session, RolUsuario.CLIENTE)
    patio, _tira, _ubicaciones = await _crear_layout(db_session, "C")
    token = _token(RolUsuario.CLIENTE, [str(patio.id)])

    response = await client.get(
        f"/api/patios/{patio.id}/mapa", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_endpoint_mapa_404_si_el_patio_no_existe(client, db_session):
    await _crear_usuario(db_session, RolUsuario.OPERADOR)
    token = _token(RolUsuario.OPERADOR)
    inexistente = uuid.uuid4()

    response = await client.get(
        f"/api/patios/{inexistente}/mapa", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_mapa_oculta_la_ocupacion_de_un_patio_no_asignado(client, db_session):
    """La RLS de 0006/0010 cubre contenedores, movimientos y auditoria, no la geometria.

    Un operador sin el patio asignado ve la estructura del patio, que no es dato
    confidencial, pero no ve que haya contenedores en el: la ocupacion sale en cero.
    """
    await _crear_usuario(db_session, RolUsuario.OPERADOR)
    patio, _tira, ubicaciones = await _crear_layout(db_session, "E")
    db_session.add(
        Contenedor(
            numero_contenedor="AJENO1234567"[:11],
            tipo=TipoContenedor.LLENO,
            tamano=TamanoContenedor.CUARENTA,
            patio_id=patio.id,
            ubicacion_id=ubicaciones[0].id,
            estado=EstadoContenedor.UBICADO,
            peso_kg=28000,
        )
    )
    await db_session.commit()

    # Control: con el patio asignado, el mismo montaje si reporta el contenedor. Sin esta
    # mitad el test pasaria aunque la ocupacion saliera siempre en cero.
    asignado = _token(RolUsuario.OPERADOR, [str(patio.id)])
    con_acceso = await client.get(
        f"/api/patios/{patio.id}/mapa", headers={"Authorization": f"Bearer {asignado}"}
    )
    assert con_acceso.status_code == 200
    assert con_acceso.json()["carriles"][0]["tramos"][0]["tiras"][0]["niveles_ocupados"] == 1

    sin_asignar = _token(RolUsuario.OPERADOR, [])
    response = await client.get(
        f"/api/patios/{patio.id}/mapa", headers={"Authorization": f"Bearer {sin_asignar}"}
    )

    assert response.status_code == 200
    tira_out = response.json()["carriles"][0]["tramos"][0]["tiras"][0]
    assert tira_out["niveles_totales"] == 3
    assert tira_out["niveles_ocupados"] == 0
