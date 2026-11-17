import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, RolUsuario, TamanoContenedor, TipoContenedor
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
from app.models.usuario import Usuario, UsuarioPatio


@pytest.fixture
async def setup_entorno_estiba(db_session):
    patio = Patio(nombre="Patio Estiba", codigo=f"PE-{uuid.uuid4().hex[:6]}")
    db_session.add(patio)
    await db_session.flush()

    carril = Carril(patio_id=patio.id, codigo="C1", orden=0)
    db_session.add(carril)
    await db_session.flush()

    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()

    tira1 = Tira(tramo_id=tramo.id, codigo="S1", orden=0, max_niveles=2)
    tira2 = Tira(tramo_id=tramo.id, codigo="S2", orden=1, max_niveles=2)
    db_session.add_all([tira1, tira2])
    await db_session.flush()

    ub1 = Ubicacion(tira_id=tira1.id, nivel=1, codigo="C1-T1-S1-N1")
    ub2 = Ubicacion(tira_id=tira1.id, nivel=2, codigo="C1-T1-S1-N2")
    ub3 = Ubicacion(tira_id=tira1.id, nivel=3, codigo="C1-T1-S1-N3")
    ub_alt = Ubicacion(tira_id=tira2.id, nivel=1, codigo="C1-T1-S2-N1")
    db_session.add_all([ub1, ub2, ub3, ub_alt])
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
    return token, patio.id, {"ub1_id": ub1.id, "ub2_id": ub2.id, "ub3_id": ub3.id, "ub_alt_id": ub_alt.id}


@pytest.mark.anyio
async def test_ubicacion_floating_position_rejected(
    client: AsyncClient, setup_entorno_estiba, db_session
):
    token, patio_id, ubs = setup_entorno_estiba

    contenedor = Contenedor(
        numero_contenedor="MSCU1234567",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.VEINTE,
        patio_id=patio_id,
        estado=EstadoContenedor.INGRESADO,
        peso_kg=12000,
    )
    db_session.add(contenedor)
    await db_session.commit()
    await db_session.refresh(contenedor)

    # Nivel 2 con el nivel 1 vacío: posición flotante.
    response = await client.post(
        f"/api/contenedores/{contenedor.id}/reubicar",
        json={"ubicacion_destino_id": str(ubs["ub2_id"]), "motivo": "Reubicacion de prueba"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_ubicacion_max_niveles_rejected(
    client: AsyncClient, setup_entorno_estiba, db_session
):
    token, patio_id, ubs = setup_entorno_estiba

    contenedor = Contenedor(
        numero_contenedor="MSCU7654321",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.VEINTE,
        patio_id=patio_id,
        estado=EstadoContenedor.UBICADO,
        peso_kg=12000,
        ubicacion_id=ubs["ub1_id"],
    )
    db_session.add(contenedor)
    await db_session.commit()
    await db_session.refresh(contenedor)

    # Nivel 3 supera max_niveles=2.
    response = await client.post(
        f"/api/contenedores/{contenedor.id}/reubicar",
        json={"ubicacion_destino_id": str(ubs["ub3_id"]), "motivo": "Excede max niveles"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_reubicar_container_with_containers_on_top(
    client: AsyncClient, setup_entorno_estiba, db_session
):
    token, patio_id, ubs = setup_entorno_estiba

    c1 = Contenedor(
        numero_contenedor="MSCU1111111",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.VEINTE,
        patio_id=patio_id,
        estado=EstadoContenedor.UBICADO,
        peso_kg=12000,
        ubicacion_id=ubs["ub1_id"],
    )
    c2 = Contenedor(
        numero_contenedor="MSCU2222222",
        tipo=TipoContenedor.LLENO,
        tamano=TamanoContenedor.VEINTE,
        patio_id=patio_id,
        estado=EstadoContenedor.UBICADO,
        peso_kg=12000,
        ubicacion_id=ubs["ub2_id"],
    )
    db_session.add_all([c1, c2])
    await db_session.commit()

    # c1 tiene a c2 encima: no se puede sacar de abajo. Movemos a ub_alt_id.
    response = await client.post(
        f"/api/contenedores/{c1.id}/reubicar",
        json={"ubicacion_destino_id": str(ubs["ub_alt_id"]), "motivo": "Sacar de abajo"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
    assert "MSCU2222222" in str(response.json())
