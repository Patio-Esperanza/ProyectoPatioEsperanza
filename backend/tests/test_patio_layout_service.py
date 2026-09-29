import pytest
from sqlalchemy import select

from app.models.ubicacion import Carril, Patio, Ubicacion
from app.services.patio_layout import sembrar_layout_uniforme


async def _crear_patio(db_session, codigo: str) -> Patio:
    patio = Patio(nombre=f"Patio {codigo}", codigo=codigo)
    db_session.add(patio)
    await db_session.flush()
    return patio


@pytest.mark.anyio
async def test_sembrar_layout_uniforme_crea_la_jerarquia_completa(db_session):
    patio = await _crear_patio(db_session, "SL1")

    carriles_creados, carriles_saltados, ubicaciones_creadas = await sembrar_layout_uniforme(
        db_session, patio, carriles=2, tramos=1, tiras=1, niveles=3
    )
    await db_session.commit()

    assert carriles_creados == 2
    assert carriles_saltados == 0
    assert ubicaciones_creadas == 6

    codigos = await db_session.execute(select(Ubicacion.codigo))
    assert sorted(row[0] for row in codigos.all()) == [
        "A01-T01-R01-N1",
        "A01-T01-R01-N2",
        "A01-T01-R01-N3",
        "A02-T01-R01-N1",
        "A02-T01-R01-N2",
        "A02-T01-R01-N3",
    ]


@pytest.mark.anyio
async def test_sembrar_layout_uniforme_es_idempotente_por_carril(db_session):
    patio = await _crear_patio(db_session, "SL2")
    await sembrar_layout_uniforme(db_session, patio, carriles=2, tramos=1, tiras=1, niveles=2)
    await db_session.commit()

    carriles_creados, carriles_saltados, ubicaciones_creadas = await sembrar_layout_uniforme(
        db_session, patio, carriles=2, tramos=1, tiras=1, niveles=2
    )
    await db_session.commit()

    assert carriles_creados == 0
    assert carriles_saltados == 2
    assert ubicaciones_creadas == 0


@pytest.mark.anyio
async def test_sembrar_layout_uniforme_agrega_solo_los_carriles_nuevos(db_session):
    patio = await _crear_patio(db_session, "SL3")
    await sembrar_layout_uniforme(db_session, patio, carriles=1, tramos=1, tiras=1, niveles=2)
    await db_session.commit()

    carriles_creados, carriles_saltados, ubicaciones_creadas = await sembrar_layout_uniforme(
        db_session, patio, carriles=3, tramos=1, tiras=1, niveles=2
    )
    await db_session.commit()

    assert carriles_creados == 2
    assert carriles_saltados == 1
    assert ubicaciones_creadas == 4

    total_carriles = await db_session.execute(select(Carril).where(Carril.patio_id == patio.id))
    assert len(total_carriles.scalars().all()) == 3
