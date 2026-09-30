import datetime
import logging
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import enviar_correo_con_adjunto
from app.db import SessionLocal
from app.models.reporte_programado import ReporteProgramado
from app.schemas.reportes import FrecuenciaReporte, ReporteTipo
from app.services.reportes_datos import TITULOS_POR_REPORTE, obtener_preview_reporte
from app.services.reportes_excel import generar_excel_reporte

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler | None = None


def _calcular_trigger(prog: ReporteProgramado) -> CronTrigger:
    """Build APScheduler CronTrigger from ReporteProgramado frequency config."""
    frecuencia = prog.frecuencia

    if frecuencia == FrecuenciaReporte.DIARIO.value:
        return CronTrigger(hour=prog.hora, minute=prog.minuto)

    if frecuencia == FrecuenciaReporte.SEMANAL.value:
        return CronTrigger(
            day_of_week=prog.dia_semana or 0,
            hour=prog.hora,
            minute=prog.minuto,
        )

    if frecuencia == FrecuenciaReporte.MENSUAL.value:
        return CronTrigger(
            day=prog.dia_mes or 1,
            hour=prog.hora,
            minute=prog.minuto,
        )

    return CronTrigger(hour=prog.hora, minute=prog.minuto)


def iniciar_scheduler() -> None:
    """Start global AsyncIOScheduler singleton."""
    global scheduler
    if scheduler is not None:
        return
    scheduler = AsyncIOScheduler()
    scheduler.start()
    logger.info("Scheduler iniciado")


def apagar_scheduler() -> None:
    """Shut down scheduler gracefully."""
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("Scheduler apagado")


async def sincronizar_tareas_desde_db(db: AsyncSession) -> None:
    """Load all active ReporteProgramado from DB and register cron jobs."""
    result = await db.execute(
        select(ReporteProgramado).where(ReporteProgramado.activo.is_(True))
    )
    programados = result.scalars().all()
    for prog in programados:
        programar_job_reporte(prog)
    logger.info("Sincronizados %d reportes programados", len(programados))


def programar_job_reporte(prog: ReporteProgramado) -> None:
    """Register or replace a cron job for one ReporteProgramado."""
    global scheduler
    if scheduler is None:
        return
    job_id = f"reporte_{prog.id}"
    # Remove existing job if any
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)

    trigger = _calcular_trigger(prog)
    scheduler.add_job(
        _ejecutar_job_wrapper,
        trigger=trigger,
        id=job_id,
        args=[prog.id],
        replace_existing=True,
    )
    logger.info("Job programado: %s (%s)", prog.nombre, job_id)


def remover_job_reporte(prog_id: uuid.UUID) -> None:
    """Remove a scheduled job by ReporteProgramado id."""
    global scheduler
    if scheduler is None:
        return
    job_id = f"reporte_{prog_id}"
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)
        logger.info("Job removido: %s", job_id)


async def _ejecutar_job_wrapper(reporte_programado_id: uuid.UUID) -> None:
    """Wrapper that creates its own DB session for scheduled execution."""
    async with SessionLocal() as db:
        try:
            await ejecutar_envio_reporte_programado(reporte_programado_id, db)
            await db.commit()
        except Exception:
            logger.exception("Error ejecutando reporte programado %s", reporte_programado_id)
            await db.rollback()


async def ejecutar_envio_reporte_programado(
    reporte_programado_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Generate Excel for a scheduled report and email it to recipients."""
    prog = await db.get(ReporteProgramado, reporte_programado_id)
    if prog is None:
        logger.error("ReporteProgramado %s not found", reporte_programado_id)
        return

    tipo = ReporteTipo(prog.tipo_reporte)
    titulo, subtitulo = TITULOS_POR_REPORTE.get(tipo, ("Reporte", ""))

    try:
        from app.schemas.reportes import FiltrosReporte

        filtros = FiltrosReporte(
            page=1,
            page_size=500,
            patio_id=prog.patio_id,
            cliente_id=prog.cliente_id,
        )
        patios_ids = [prog.patio_id] if prog.patio_id else None
        preview = await obtener_preview_reporte(db, tipo, filtros, patios_ids)

        buffer = generar_excel_reporte(
            tipo=tipo,
            datos=preview.filas,
            total_registros=preview.total_registros,
            subtitulo=subtitulo,
        )

        ahora = datetime.datetime.now()
        nombre_archivo = f"{titulo.replace(' ', '_')}_{ahora.strftime('%Y%m%d_%H%M%S')}.xlsx"

        contenido_html = (
            f"<p>Reporte automático: <strong>{titulo}</strong></p>"
            f"<p>{subtitulo}</p>"
            f"<p>Generado: {ahora.strftime('%d/%m/%Y %H:%M:%S')}</p>"
        )
        mensaje_custom = prog.mensaje or ""
        if mensaje_custom:
            contenido_html += f"<p>{mensaje_custom}</p>"

        enviar_correo_con_adjunto(
            destinatarios=prog.destinatarios,
            asunto=prog.asunto,
            contenido_html=contenido_html,
            adjunto_bytes=buffer.getvalue(),
            adjunto_nombre=nombre_archivo,
        )

        prog.ultimo_envio = ahora
        prog.ultimo_estado = "enviado"
        prog.ultimo_error = None
        await db.flush()

    except Exception as exc:
        logger.exception("Error generando/enviando reporte %s", reporte_programado_id)
        prog.ultimo_estado = "error"
        prog.ultimo_error = str(exc)[:500]
        await db.flush()
        raise
