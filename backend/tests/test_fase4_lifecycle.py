import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models.servicio import ServicioCatalogo, ServicioContenedor, EstadoServicio
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, TipoContenedor, TamanoContenedor
from app.models.ubicacion import Patio, Carril, Tramo, Tira, Ubicacion
from app.models.usuario import Usuario, UsuarioPatio
from app.core.security import create_access_token, hash_password
from app.models.enums import RolUsuario
import uuid


@pytest.fixture
async def setup_test_data(db_session):
    """Set up patio, ubicacion, usuario despachador, and a contenedor ready for dispatch"""
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

    contenedor = Contenedor(
        numero_contenedor="MSCU7654321",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.VEINTE,
        patio_id=patio.id,
        estado=EstadoContenedor.EN_PORTERIA_SALIDA,
        peso_kg=12000,
        sellos="SELLO123",
        pin_salida_hash=hash_password("1234"),
        pin_salida_intentos=0,
        ubicacion_id=ubicacion.id,
    )
    db_session.add(contenedor)
    await db_session.commit()
    await db_session.refresh(contenedor)

    return {
        "token": token,
        "patio_id": patio.id,
        "contenedor_id": contenedor.id,
        "ubicacion_id": ubicacion.id,
        "usuario_id": usuario.id,
    }


@pytest.mark.asyncio
async def test_service_blocks_container_dispatch(client: AsyncClient, setup_test_data, db_session):
    """
    Test that a container with a pending service order that blocks exit
    cannot be dispatched. Should return 409.
    """
    # Create a service catalog entry that blocks exit (TRA - Traspaleo)
    result = await db_session.execute(
        select(ServicioCatalogo).where(ServicioCatalogo.codigo == "TRA")
    )
    servicio_catalogo = result.scalar_one_or_none()
    assert servicio_catalogo is not None
    assert servicio_catalogo.bloquea_salida is True

    # Create a pending service order for the container (state: programado)
    servicio = ServicioContenedor(
        contenedor_id=setup_test_data["contenedor_id"],
        servicio_catalogo_id=servicio_catalogo.id,
        solicitado_por=setup_test_data["usuario_id"],
        estado=EstadoServicio.PROGRAMADO,
    )
    db_session.add(servicio)
    await db_session.commit()

    # Try to dispatch the container - should be blocked
    response = await client.post(
        f"/api/contenedores/{setup_test_data['contenedor_id']}/despachar",
        json={"pin_salida": "1234"},
        headers={"Authorization": f"Bearer {setup_test_data['token']}"}
    )
    assert response.status_code == 409
    body = response.json()
    assert "servicio" in body["detail"].lower() or "traspaleo" in body["detail"].lower()


@pytest.mark.asyncio
async def test_service_terminated_allows_dispatch(client: AsyncClient, setup_test_data, db_session):
    """
    Test that a container with a TERMINATED service order can be dispatched.
    """
    # Create a service catalog entry that blocks exit (TRA - Traspaleo)
    result = await db_session.execute(
        select(ServicioCatalogo).where(ServicioCatalogo.codigo == "TRA")
    )
    servicio_catalogo = result.scalar_one_or_none()
    assert servicio_catalogo is not None
    assert servicio_catalogo.bloquea_salida is True

    # Create a TERMINATED service order for the container
    servicio = ServicioContenedor(
        contenedor_id=setup_test_data["contenedor_id"],
        servicio_catalogo_id=servicio_catalogo.id,
        solicitado_por=setup_test_data["usuario_id"],
        estado=EstadoServicio.TERMINADO,
    )
    db_session.add(servicio)
    await db_session.commit()

    # Try to dispatch the container - should succeed now
    response = await client.post(
        f"/api/contenedores/{setup_test_data['contenedor_id']}/despachar",
        json={"pin_salida": "1234"},
        headers={"Authorization": f"Bearer {setup_test_data['token']}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["contenedor"]["estado"] == "despachado"


@pytest.mark.asyncio
async def test_all_blocking_services_block_dispatch(client: AsyncClient, setup_test_data, db_session):
    """
    Test that all four blocking services (TRA, REA, DES, EMP) block dispatch when pending.
    """
    for codigo in ["TRA", "REA", "DES", "EMP"]:
        # Get service catalog
        result = await db_session.execute(
            select(ServicioCatalogo).where(ServicioCatalogo.codigo == codigo)
        )
        servicio_catalogo = result.scalar_one_or_none()
        assert servicio_catalogo is not None
        assert servicio_catalogo.bloquea_salida is True

        # Create a new container for each test (<= 11 chars), ubicacion_id=None
        contenedor = Contenedor(
            numero_contenedor=f"MSCU{codigo}12",
            tipo=TipoContenedor.LLENO,
            tamano=TamanoContenedor.VEINTE,
            patio_id=setup_test_data["patio_id"],
            estado=EstadoContenedor.EN_PORTERIA_SALIDA,
            peso_kg=12000,
            sellos=f"SELLO{codigo}",
            pin_salida_hash=hash_password("1234"),
            pin_salida_intentos=0,
            ubicacion_id=None,
        )
        db_session.add(contenedor)
        await db_session.commit()
        await db_session.refresh(contenedor)

        # Create pending service order
        servicio = ServicioContenedor(
            contenedor_id=contenedor.id,
            servicio_catalogo_id=servicio_catalogo.id,
            solicitado_por=setup_test_data["usuario_id"],
            estado=EstadoServicio.PROGRAMADO,
        )
        db_session.add(servicio)
        await db_session.commit()

        # Try to dispatch - should be blocked
        response = await client.post(
            f"/api/contenedores/{contenedor.id}/despachar",
            json={"pin_salida": "1234"},
            headers={"Authorization": f"Bearer {setup_test_data['token']}"}
        )
        assert response.status_code == 409, f"Service {codigo} should block dispatch"
