import pytest
from sqlalchemy import select
from app.models.servicio import ServicioCatalogo

@pytest.mark.asyncio
async def test_servicios_catalogo_seed_exists(db_session):
    # Verify TRA (Traspaleo), REA, DES, EMP exist
    result = await db_session.execute(select(ServicioCatalogo).where(ServicioCatalogo.codigo == "TRA"))
    servicio = result.scalar_one_or_none()
    assert servicio is not None
    assert servicio.bloquea_salida is True
    assert servicio.requiere_evidencia is True
    assert servicio.requiere_unidad_relacionada is True

    result_rea = await db_session.execute(select(ServicioCatalogo).where(ServicioCatalogo.codigo == "REA"))
    assert result_rea.scalar_one_or_none() is not None

    result_des = await db_session.execute(select(ServicioCatalogo).where(ServicioCatalogo.codigo == "DES"))
    assert result_des.scalar_one_or_none() is not None

    result_emp = await db_session.execute(select(ServicioCatalogo).where(ServicioCatalogo.codigo == "EMP"))
    assert result_emp.scalar_one_or_none() is not None
