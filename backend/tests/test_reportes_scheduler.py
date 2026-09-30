import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reporte_programado import ReporteProgramado
from app.schemas.reportes import FrecuenciaReporte, ReporteTipo
from app.services.reportes_scheduler import (
    _calcular_trigger,
    ejecutar_envio_reporte_programado,
)


def test_calcular_trigger_diario():
    prog = ReporteProgramado(
        id=uuid.uuid4(),
        nombre="Diario",
        tipo_reporte=ReporteTipo.CONTAINERS_IN_YARD.value,
        frecuencia=FrecuenciaReporte.DIARIO.value,
        hora=8,
        minuto=30,
        destinatarios=["test@test.com"],
        asunto="Test",
        activo=True,
    )
    trigger = _calcular_trigger(prog)
    assert trigger.fields[5].name == "hour"
    assert trigger.fields[6].name == "minute"


def test_calcular_trigger_semanal():
    prog = ReporteProgramado(
        id=uuid.uuid4(),
        nombre="Semanal",
        tipo_reporte=ReporteTipo.ENTRY_MOVEMENTS.value,
        frecuencia=FrecuenciaReporte.SEMANAL.value,
        hora=9,
        minuto=0,
        dia_semana=1,
        destinatarios=["test@test.com"],
        asunto="Test Semanal",
        activo=True,
    )
    trigger = _calcular_trigger(prog)
    assert trigger is not None


def test_calcular_trigger_mensual():
    prog = ReporteProgramado(
        id=uuid.uuid4(),
        nombre="Mensual",
        tipo_reporte=ReporteTipo.DEPARTURE_MOVEMENTS.value,
        frecuencia=FrecuenciaReporte.MENSUAL.value,
        hora=7,
        minuto=15,
        dia_mes=1,
        destinatarios=["test@test.com"],
        asunto="Test Mensual",
        activo=True,
    )
    trigger = _calcular_trigger(prog)
    assert trigger is not None


@pytest.mark.asyncio
async def test_ejecutar_envio_reporte_programado_envia_correo(db_session: AsyncSession):
    prog_id = uuid.uuid4()
    prog = ReporteProgramado(
        id=prog_id,
        nombre="Test Envío",
        tipo_reporte=ReporteTipo.CONTAINERS_IN_YARD.value,
        frecuencia=FrecuenciaReporte.DIARIO.value,
        hora=8,
        minuto=0,
        destinatarios=["ops@empresa.com"],
        asunto="Reporte Diario",
        activo=True,
    )
    db_session.add(prog)
    await db_session.flush()

    with patch("app.services.reportes_scheduler.enviar_correo_con_adjunto") as mock_email:
        await ejecutar_envio_reporte_programado(prog_id, db_session)
        mock_email.assert_called_once()
        call_args = mock_email.call_args
        assert call_args.kwargs["destinatarios"] == ["ops@empresa.com"]
        assert call_args.kwargs["asunto"] == "Reporte Diario"
        assert call_args.kwargs["adjunto_nombre"].endswith(".xlsx")

    # Verificar update en DB
    await db_session.refresh(prog)
    assert prog.ultimo_estado == "enviado"
    assert prog.ultimo_envio is not None
