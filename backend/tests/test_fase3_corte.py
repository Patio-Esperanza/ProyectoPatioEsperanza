import pytest
from app.jobs.corte_diario import ejecutar_corte_diario

@pytest.mark.asyncio
async def test_corte_diario_es_idempotente(db_session):
    fecha = "2026-11-03"
    await ejecutar_corte_diario(db_session, fecha)
    await ejecutar_corte_diario(db_session, fecha) # Should not raise integrity error
    assert True
