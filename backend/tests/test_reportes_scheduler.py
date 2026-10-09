import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import zona_horaria_app
from app.models.reporte_programado import ReporteProgramado
from app.schemas.reportes import FrecuenciaReporte, ReporteTipo
from app.services import reportes_scheduler
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


def _programado(**overrides) -> ReporteProgramado:
    campos = {
        "id": uuid.uuid4(),
        "nombre": "Reporte",
        "tipo_reporte": ReporteTipo.CONTAINERS_IN_YARD.value,
        "frecuencia": FrecuenciaReporte.DIARIO.value,
        "hora": 8,
        "minuto": 30,
        "destinatarios": ["test@test.com"],
        "asunto": "Test",
        "activo": True,
    }
    campos.update(overrides)
    return ReporteProgramado(**campos)


def test_trigger_usa_la_zona_de_la_app_y_no_la_del_host():
    """La hora guardada se interpreta en México, no en UTC.

    Sin `timezone=` el trigger tomaba la zona del host, que en el contenedor es
    UTC: una fila con hora=8 disparaba a las 08:00 UTC, o 02:00 en México.
    """
    trigger = _calcular_trigger(_programado(hora=8, minuto=30))

    assert trigger.timezone == zona_horaria_app()

    # Siguiente disparo: 08:30 de México, que en UTC son las 14:30.
    desde = datetime.datetime(2026, 10, 9, 0, 0, tzinfo=datetime.timezone.utc)
    siguiente = trigger.get_next_fire_time(None, desde)
    assert siguiente.astimezone(zona_horaria_app()).hour == 8
    assert siguiente.astimezone(zona_horaria_app()).minute == 30
    assert siguiente.astimezone(datetime.timezone.utc).hour == 14


@pytest.mark.parametrize(
    "frecuencia, extra",
    [
        (FrecuenciaReporte.DIARIO.value, {}),
        (FrecuenciaReporte.SEMANAL.value, {"dia_semana": 1}),
        (FrecuenciaReporte.MENSUAL.value, {"dia_mes": 1}),
        ("frecuencia-desconocida", {}),
    ],
)
def test_todas_las_frecuencias_llevan_zona_horaria(frecuencia, extra):
    """Ninguna rama puede quedarse sin `timezone=`, incluido el fallback."""
    trigger = _calcular_trigger(_programado(frecuencia=frecuencia, **extra))

    assert trigger.timezone == zona_horaria_app()


def test_scheduler_arranca_con_la_zona_de_la_app():
    reportes_scheduler.scheduler = None
    try:
        reportes_scheduler.iniciar_scheduler()
        assert reportes_scheduler.scheduler.timezone == zona_horaria_app()
    finally:
        reportes_scheduler.apagar_scheduler()


@pytest.mark.asyncio
async def test_correo_y_archivo_llevan_la_hora_de_mexico(db_session: AsyncSession):
    """El texto "Generado" mostraba UTC: decía 08:30 para un correo de las 02:30."""
    prog_id = uuid.uuid4()
    prog = _programado(id=prog_id, nombre="Test Hora", destinatarios=["ops@empresa.com"])
    db_session.add(prog)
    await db_session.flush()

    # 2026-10-09 14:30 UTC son las 08:30 en México.
    instante = datetime.datetime(2026, 10, 9, 14, 30, 0, tzinfo=datetime.timezone.utc)

    class RelojFijo(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return instante.astimezone(tz) if tz else instante.replace(tzinfo=None)

    with patch("app.services.reportes_scheduler.enviar_correo_con_adjunto") as mock_email, patch(
        "app.services.reportes_scheduler.datetime.datetime", RelojFijo
    ):
        await ejecutar_envio_reporte_programado(prog_id, db_session)

    kwargs = mock_email.call_args.kwargs
    assert "Generado: 09/10/2026 08:30:00" in kwargs["contenido_html"]
    assert "20261009_083000" in kwargs["adjunto_nombre"]


@pytest.mark.asyncio
async def test_ultimo_envio_guarda_el_instante_correcto(db_session: AsyncSession):
    """`ultimo_envio` es timestamptz.

    Con un valor naive Postgres lo interpretaba en la zona de la sesión, así que
    el instante guardado no era el del envío.
    """
    prog_id = uuid.uuid4()
    prog = _programado(id=prog_id, nombre="Test Ultimo Envio")
    db_session.add(prog)
    await db_session.flush()

    instante = datetime.datetime(2026, 10, 9, 14, 30, 0, tzinfo=datetime.timezone.utc)

    class RelojFijo(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return instante.astimezone(tz) if tz else instante.replace(tzinfo=None)

    with patch("app.services.reportes_scheduler.enviar_correo_con_adjunto"), patch(
        "app.services.reportes_scheduler.datetime.datetime", RelojFijo
    ):
        await ejecutar_envio_reporte_programado(prog_id, db_session)

    await db_session.refresh(prog)
    assert prog.ultimo_envio.tzinfo is not None
    assert prog.ultimo_envio.astimezone(datetime.timezone.utc) == instante


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
