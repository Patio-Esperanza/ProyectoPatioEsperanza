import asyncio
import datetime
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings, zona_horaria_app


async def ejecutar_corte_diario(
    db: AsyncSession, fecha: str | datetime.date | datetime.datetime | None = None
) -> None:
    if fecha is None:
        tz = zona_horaria_app()
        fecha_obj = datetime.datetime.now(tz).date()
    elif isinstance(fecha, str):
        fecha_obj = datetime.date.fromisoformat(fecha)
    elif isinstance(fecha, datetime.datetime):
        fecha_obj = fecha.date()
    else:
        fecha_obj = fecha

    query = text(
        """
        INSERT INTO inventario_diario (fecha, patio_id, contenedor_id, cliente_id, ubicacion_id, estado, dias_estancia)
        SELECT
            :fecha_val AS fecha,
            c.patio_id,
            c.id AS contenedor_id,
            c.cliente_id,
            c.ubicacion_id,
            c.estado::text,
            GREATEST(1, (:fecha_val - (c.ingresado_en AT TIME ZONE COALESCE(p.timezone, 'America/Mexico_City'))::date) + 1) AS dias_estancia
        FROM contenedores c
        JOIN patios p ON c.patio_id = p.id
        WHERE c.ingresado_en IS NOT NULL
          AND (c.ingresado_en AT TIME ZONE COALESCE(p.timezone, 'America/Mexico_City'))::date <= :fecha_val
          AND (
              c.fecha_salida IS NULL
              OR (c.fecha_salida AT TIME ZONE COALESCE(p.timezone, 'America/Mexico_City'))::date >= :fecha_val
          )
        ON CONFLICT (fecha, patio_id, contenedor_id)
        DO UPDATE SET
            cliente_id = EXCLUDED.cliente_id,
            ubicacion_id = EXCLUDED.ubicacion_id,
            estado = EXCLUDED.estado,
            dias_estancia = EXCLUDED.dias_estancia;
        """
    )
    await db.execute(query, {"fecha_val": fecha_obj})
    await db.commit()


async def main() -> None:
    fecha_arg = sys.argv[1] if len(sys.argv) > 1 else None
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        await ejecutar_corte_diario(db, fecha_arg)
        print(f"Corte diario ejecutado exitosamente para la fecha: {fecha_arg or 'hoy'}")
    await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
