import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import text
from app.core.security import create_access_token, hash_password
from app.models.enums import RolUsuario, EstadoContenedor, TipoContenedor, TamanoContenedor
from app.models.usuario import Usuario, UsuarioPatio
from app.models.ubicacion import Patio, Carril, Tramo, Tira, Ubicacion
from app.models.contenedor import Contenedor


@pytest.fixture
async def setup_guardia(db_session):
    patio = Patio(nombre="Patio Norte", codigo=f"PN-{uuid.uuid4().hex[:6]}")
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
        email=f"guardia-{uuid.uuid4().hex[:6]}@patio.mx",
        password_hash=hash_password("clave123"),
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()
    db_session.add(UsuarioPatio(usuario_id=usuario.id, patio_id=patio.id))
    await db_session.commit()

    token = create_access_token(str(usuario.id), RolUsuario.GUARDIA.value, [str(patio.id)], 60)
    return token, patio.id


@pytest.fixture
async def setup_despachador(db_session):
    patio = Patio(nombre="Patio Norte", codigo=f"PD-{uuid.uuid4().hex[:6]}")
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
        tipo=RolUsuario.DESPACHADOR,
        email=f"despachador-{uuid.uuid4().hex[:6]}@patio.mx",
        password_hash=hash_password("clave123"),
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()
    db_session.add(UsuarioPatio(usuario_id=usuario.id, patio_id=patio.id))
    await db_session.commit()

    token = create_access_token(str(usuario.id), RolUsuario.DESPACHADOR.value, [str(patio.id)], 60)
    return token, patio.id


@pytest.fixture
async def setup_operador_grua(db_session):
    patio = Patio(nombre="Patio Norte", codigo=f"PG-{uuid.uuid4().hex[:6]}")
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
        tipo=RolUsuario.OPERADOR_GRUA,
        email=f"grua-{uuid.uuid4().hex[:6]}@patio.mx",
        password_hash=hash_password("clave123"),
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()
    db_session.add(UsuarioPatio(usuario_id=usuario.id, patio_id=patio.id))
    await db_session.commit()

    token = create_access_token(str(usuario.id), RolUsuario.OPERADOR_GRUA.value, [str(patio.id)], 60)
    return token, patio.id


@pytest.mark.anyio
async def test_dispatch_rejects_non_gate_ready_container(client: AsyncClient, setup_despachador, db_session):
    token, patio_id = setup_despachador

    contenedor = Contenedor(
        numero_contenedor="MSCU1234567",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.VEINTE,
        patio_id=patio_id,
        estado=EstadoContenedor.UBICADO,
        peso_kg=12000,
        sellos="SELLO123",
    )
    db_session.add(contenedor)
    await db_session.commit()
    await db_session.refresh(contenedor)

    response = await client.post(
        f"/api/contenedores/{contenedor.id}/despachar",
        json={"pin_salida": "999999"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_dispatch_accepts_gate_ready_container(client: AsyncClient, setup_despachador, setup_guardia, db_session):
    token_despachador, patio_id = setup_despachador

    contenedor = Contenedor(
        numero_contenedor="MSCU7654321",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.VEINTE,
        patio_id=patio_id,
        estado=EstadoContenedor.EN_PORTERIA_SALIDA,
        peso_kg=12000,
        sellos="SELLO123",
        pin_salida_hash=hash_password("1234"),
        pin_salida_intentos=0,
    )
    db_session.add(contenedor)
    await db_session.commit()
    await db_session.refresh(contenedor)

    response = await client.post(
        f"/api/contenedores/{contenedor.id}/despachar",
        json={"pin_salida": "1234"},
        headers={"Authorization": f"Bearer {token_despachador}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["contenedor"]["estado"] == "despachado"
    assert body["contenedor"]["fecha_salida"] is not None


@pytest.mark.anyio
async def test_crane_operator_places_container(client: AsyncClient, setup_operador_grua, db_session):
    token, patio_id = setup_operador_grua

    contenedor = Contenedor(
        numero_contenedor="MSCU1111111",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.VEINTE,
        patio_id=patio_id,
        estado=EstadoContenedor.INGRESADO,
        peso_kg=12000,
    )
    db_session.add(contenedor)
    await db_session.commit()
    await db_session.refresh(contenedor)

    carril_result = await db_session.execute(
        text("SELECT id FROM carriles WHERE patio_id = :pid ORDER BY id LIMIT 1"), {"pid": str(patio_id)}
    )
    carril_id = carril_result.scalar_one()

    tramo_result = await db_session.execute(
        text("SELECT id FROM tramos WHERE carril_id = :cid ORDER BY id LIMIT 1"), {"cid": str(carril_id)}
    )
    tramo_id = tramo_result.scalar_one()

    tira_result = await db_session.execute(
        text("SELECT id FROM tiras WHERE tramo_id = :tid ORDER BY id LIMIT 1"), {"tid": str(tramo_id)}
    )
    tira_id = tira_result.scalar_one()

    ubicacion_result = await db_session.execute(
        text("SELECT id FROM ubicaciones WHERE tira_id = :tid AND nivel = 1 ORDER BY id LIMIT 1"), {"tid": str(tira_id)}
    )
    ubicacion_id = ubicacion_result.scalar_one()

    response = await client.post(
        f"/api/contenedores/{contenedor.id}/ubicar",
        json={"ubicacion_id": str(ubicacion_id)},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["contenedor"]["estado"] == "ubicado"
    assert body["contenedor"]["ubicacion_id"] == str(ubicacion_id)