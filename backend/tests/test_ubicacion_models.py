import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.enums import TipoContenedor
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion


@pytest.mark.anyio
async def test_crea_jerarquia_completa(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN")
    db_session.add(patio)
    await db_session.flush()

    carril = Carril(patio_id=patio.id, codigo="A1", orden=0, tipo_teorico=TipoContenedor.LLENO)
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
    await db_session.flush()

    result = await db_session.execute(select(Ubicacion).where(Ubicacion.id == ubicacion.id))
    assert result.scalar_one().nivel == 1


@pytest.mark.anyio
async def test_nivel_fuera_de_rango_falla(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN2")
    db_session.add(patio)
    await db_session.flush()
    carril = Carril(patio_id=patio.id, codigo="A1", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()

    db_session.add(Ubicacion(tira_id=tira.id, nivel=6, codigo="bad"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.anyio
async def test_no_duplica_slot_tira_nivel(db_session):
    patio = Patio(nombre="Patio Norte", codigo="PN3")
    db_session.add(patio)
    await db_session.flush()
    carril = Carril(patio_id=patio.id, codigo="A1", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()

    db_session.add(Ubicacion(tira_id=tira.id, nivel=1, codigo="dup-1"))
    await db_session.flush()
    db_session.add(Ubicacion(tira_id=tira.id, nivel=1, codigo="dup-2"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
