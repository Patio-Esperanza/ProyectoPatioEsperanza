import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import zona_horaria_app
from app.db import SessionLocal
from app.jobs.corte_diario import ejecutar_corte_diario

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
    scheduler.start()
    logger.info("Scheduler iniciado con job corte_diario a las 00:10")


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