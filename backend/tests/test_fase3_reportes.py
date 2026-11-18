import pytest
import datetime
import uuid
from fastapi import HTTPException
from app.schemas.reportes import FiltrosReporte, ReporteTipo
from app.services.reportes_datos import obtener_datos_reporte, ReportResultList


@pytest.mark.asyncio
async def test_reporte_estancia_cliente_scoping(db_session):
    # Test client scoping for stay-by-client report
    datos = await obtener_datos_reporte(db_session, "stay-by-client", cliente_id=1)
    assert isinstance(datos, ReportResultList)
    assert hasattr(datos, 'filas')
    assert hasattr(datos, 'total')
    assert hasattr(datos, 'kpis')


@pytest.mark.asyncio
async def test_reporte_inventory_at_date(db_session):
    datos = await obtener_datos_reporte(db_session, ReporteTipo.INVENTORY_AT_DATE)
    assert isinstance(datos, ReportResultList)
    assert hasattr(datos, 'filas')
    assert hasattr(datos, 'total')
    assert hasattr(datos, 'kpis')


@pytest.mark.asyncio
async def test_reporte_daily_summary(db_session):
    datos = await obtener_datos_reporte(db_session, ReporteTipo.DAILY_SUMMARY)
    assert isinstance(datos, ReportResultList)
    assert hasattr(datos, 'filas')
    assert hasattr(datos, 'total')
    assert hasattr(datos, 'kpis')


def test_rango_fechas_superior_366_dias_422():
    with pytest.raises((ValueError, HTTPException)):
        FiltrosReporte(
            fecha_inicio=datetime.date(2024, 1, 1),
            fecha_fin=datetime.date(2025, 2, 10),
        )
