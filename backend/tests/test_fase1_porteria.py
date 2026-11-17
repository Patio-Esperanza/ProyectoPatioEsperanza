import pytest
import uuid
from httpx import AsyncClient
from app.core.security import create_access_token, hash_password
from app.models.enums import RolUsuario, EstadoContenedor, TipoContenedor, TamanoContenedor
from app.models.usuario import Usuario, UsuarioPatio
from app.models.ubicacion import Patio, Carril, Tramo, Tira, Ubicacion
from app.models.contenedor import Contenedor


@pytest.fixture
async def setup_guardia(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN")
    db_session.add(patio)
    await db_session.flush()

    carril = Carril(patio_id=patio.id, codigo="C1", orden=0)
    db_session.add(carril)
    await db_session.flush()

    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()

    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()

    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo="C1-T1-S1-N1")
    db_session.add(ubicacion)
    await db_session.flush()

    usuario = Usuario(
        tipo=RolUsuario.GUARDIA,
        email="guardia@patio.mx",
        password_hash=hash_password("clave123"),
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()
    db_session.add(UsuarioPatio(usuario_id=usuario.id, patio_id=patio.id))
    await db_session.commit()

    token = create_access_token(str(usuario.id), RolUsuario.GUARDIA.value, [str(patio.id)], 60)
    return token, patio.id


@pytest.mark.anyio
async def test_porteria_ingreso_requires_photos(client: AsyncClient, setup_guardia):
    token, patio_id = setup_guardia
    response = await client.post(
        "/api/porteria/ingresos",
        json={"pin": "123456", "placas": "ABC-123", "operador": "Juan", "sellos": "S1", "evidencias": []},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_porteria_buscar(client: AsyncClient, setup_guardia, db_session):
    token, patio_id = setup_guardia
    contenedor = Contenedor(
        numero_contenedor="CSQU3054383",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.CUARENTA,
        patio_id=patio_id,
        estado=EstadoContenedor.SOLICITUD_INGRESO,
        peso_kg=18000,
        pin_confirmacion="1234",
    )
    db_session.add(contenedor)
    await db_session.commit()

    response = await client.get(
        "/api/porteria/buscar?q=1234",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["numero_contenedor"] == "CSQU3054383"


@pytest.mark.anyio
async def test_porteria_ingreso_exitosa(client: AsyncClient, setup_guardia, db_session):
    token, patio_id = setup_guardia
    contenedor = Contenedor(
        numero_contenedor="MSCU1234567",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.VEINTE,
        patio_id=patio_id,
        estado=EstadoContenedor.SOLICITUD_INGRESO,
        peso_kg=12000,
        sellos="SELLO123",
        pin_confirmacion="5678",
    )
    db_session.add(contenedor)
    await db_session.commit()

    response = await client.post(
        "/api/porteria/ingresos",
        json={
            "pin": "5678",
            "placas": "XYZ-999",
            "operador": "Pedro",
            "sellos": "SELLO123",
            "evidencias": ["https://spaces.url/foto1.jpg"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["contenedor"]["estado"] == "ingresado"
    assert "sugerencias" in body
    assert len(body["sugerencias"]) >= 1


@pytest.mark.anyio
async def test_guardia_sin_patio_prohibido(client: AsyncClient, db_session):
    patio = Patio(nombre="Patio Sur", codigo="PS")
    db_session.add(patio)
    await db_session.flush()

    usuario = Usuario(
        tipo=RolUsuario.GUARDIA,
        email="guardiasinpatio@patio.mx",
        password_hash=hash_password("clave123"),
        activo=True,
    )
    db_session.add(usuario)
    await db_session.commit()

    token = create_access_token(str(usuario.id), RolUsuario.GUARDIA.value, [], 60)
    response = await client.get(
        "/api/porteria/buscar?q=1234",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
