import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import zona_horaria_app
from app.db import SessionLocal
from app.jobs.corte_diario import ejecutar_corte_diario
from app.jobs.webhooks_socio import ejecutar_dispatch_webhooks_socio

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler | None = None


def iniciar_scheduler() -> None:
    """Start global AsyncIOScheduler singleton."""
    global scheduler
    if scheduler is not None:
        return
    scheduler = AsyncIOScheduler(timezone=zona_horaria_app())
    # Add daily snapshot job at 00:10 local time
    scheduler.add_job(
        _ejecutar_corte_diario_wrapper,
        trigger=CronTrigger(hour=0, minute=10, timezone=zona_horaria_app()),
        id="corte_diario",
        replace_existing=True,
    )
    # Add webhook dispatch job every minute
    scheduler.add_job(
        _ejecutar_dispatch_webhooks_socio_wrapper,
        trigger=CronTrigger(second=0, timezone=zona_horaria_app()),
        id="dispatch_webhooks_socio",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler iniciado con job corte_diario y dispatch_webhooks_socio")


def apagar_scheduler() -> None:
    """Shut down scheduler gracefully."""
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("Scheduler apagado")


async def _ejecutar_corte_diario_wrapper() -> None:
    """Wrapper that creates its own DB session for scheduled execution."""
    async with SessionLocal() as db:
        try:
            await ejecutar_corte_diario(db, None)
            await db.commit()
            logger.info("Corte diario ejecutado exitosamente")
        except Exception:
            logger.exception("Error ejecutando corte diario")
            await db.rollback()
            raise


async def _ejecutar_dispatch_webhooks_socio_wrapper() -> None:
    """Wrapper that creates its own DB session for webhook dispatch execution."""
    async with SessionLocal() as db:
        try:
            await ejecutar_dispatch_webhooks_socio(db)
            await db.commit()
        except Exception:
            logger.exception("Error ejecutando dispatch webhooks socio")
            await db.rollback()
            raise
