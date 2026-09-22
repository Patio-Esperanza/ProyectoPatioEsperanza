"""Carga el layout de un patio: carriles, tramos, tiras y ubicaciones.

Es idempotente: si ya existe un carril con el codigo que va a generar, lo salta.

Ejemplo:
    python -m scripts.seed_patio_layout --patio-codigo PN \
        --carriles 12 --tramos 10 --tiras 12 --niveles 5 --entrada A01-T01-R01-N1
"""
import argparse
import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Carga el layout de un patio")
    parser.add_argument("--patio-codigo", required=True)
    parser.add_argument("--carriles", type=int, required=True)
    parser.add_argument("--tramos", type=int, required=True)
    parser.add_argument("--tiras", type=int, required=True)
    parser.add_argument("--niveles", type=int, default=5, choices=range(1, 6))
    parser.add_argument(
        "--entrada",
        help="Codigo de la ubicacion que sirve de punto de entrada, por ejemplo A01-T01-R01-N1",
    )
    return parser.parse_args()


async def main() -> int:
    args = _parse_args()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        patio_result = await db.execute(select(Patio).where(Patio.codigo == args.patio_codigo))
        patio = patio_result.scalar_one_or_none()
        if patio is None:
            print(f"No existe un patio con codigo {args.patio_codigo}.")
            return 1

        creados = 0
        saltados = 0

        for c in range(args.carriles):
            carril_codigo = f"A{c + 1:02d}"
            existente = await db.execute(
                select(Carril).where(
                    Carril.patio_id == patio.id, Carril.codigo == carril_codigo
                )
            )
            if existente.scalar_one_or_none() is not None:
                saltados += 1
                continue

            carril = Carril(patio_id=patio.id, codigo=carril_codigo, orden=c)
            db.add(carril)
            await db.flush()

            for t in range(args.tramos):
                tramo = Tramo(carril_id=carril.id, codigo=f"T{t + 1:02d}", orden=t)
                db.add(tramo)
                await db.flush()

                for r in range(args.tiras):
                    tira = Tira(tramo_id=tramo.id, codigo=f"R{r + 1:02d}", orden=r)
                    db.add(tira)
                    await db.flush()

                    for n in range(1, args.niveles + 1):
                        db.add(
                            Ubicacion(
                                tira_id=tira.id,
                                nivel=n,
                                codigo=f"{carril.codigo}-{tramo.codigo}-{tira.codigo}-N{n}",
                                activo=True,
                            )
                        )
                        creados += 1

        await db.commit()
        print(f"Ubicaciones creadas: {creados}. Carriles saltados por ya existir: {saltados}.")

        if args.entrada:
            entrada_result = await db.execute(
                select(Ubicacion).where(Ubicacion.codigo == args.entrada)
            )
            entrada = entrada_result.scalar_one_or_none()
            if entrada is None:
                print(f"No existe la ubicacion {args.entrada}. El punto de entrada no se fijo.")
                await engine.dispose()
                return 1
            patio.ubicacion_entrada_id = entrada.id
            await db.commit()
            print(f"Punto de entrada del patio fijado en {args.entrada}.")

    await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
