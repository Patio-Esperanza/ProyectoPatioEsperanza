import datetime
import uuid
from app.schemas.reportes import (
    FiltrosReporte,
    FrecuenciaReporte,
    ReporteColumna,
    ReporteKpi,
    ReportePreviewOut,
    ReporteProgramadoCreate,
    ReporteProgramadoOut,
    ReporteTipo,
)

def test_schemas_reportes_serializacion():
    filtros = FiltrosReporte(
        fecha_inicio=datetime.date(2026, 9, 1),
        fecha_fin=datetime.date(2026, 9, 30),
        page=1,
        page_size=25,
    )
    assert filtros.page == 1
    assert filtros.page_size == 25

    col = ReporteColumna(key="contenedor", label="Contenedor", align="center")
    kpi = ReporteKpi(label="Total", value="54", tone="info")
    preview = ReportePreviewOut(
        tipo=ReporteTipo.CONTAINERS_IN_YARD,
        titulo="Contenedores en Patio",
        subtitulo="Snapshot de contenedores activos",
        total_registros=1,
        columnas=[col],
        filas=[{"contenedor": "CSNU7862291"}],
        kpis=[kpi],
        page=1,
        page_size=25,
        total_paginas=1,
    )
    data = preview.model_dump()
    assert data["tipo"] == "containers-in-yard"
    assert len(data["columnas"]) == 1

def test_schema_reporte_programado():
    prog = ReporteProgramadoCreate(
        nombre="Envío Diario Contenedores",
        tipo_reporte=ReporteTipo.CONTAINERS_IN_YARD,
        frecuencia=FrecuenciaReporte.DIARIO,
        hora=8,
        minuto=30,
        destinatarios=["operaciones@empresa.com"],
        asunto="Reporte Diario de Contenedores en Patio",
    )
    assert prog.hora == 8
    assert prog.minuto == 30
    assert len(prog.destinatarios) == 1
