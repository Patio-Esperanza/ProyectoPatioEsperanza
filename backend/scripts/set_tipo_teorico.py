"""Fija tipo_teorico (lleno/vacio) en carriles ya existentes, por rango.

Ejemplo: carriles A01-A07 llenos, A08-A11 vacios, en el patio 02:
    python -m scripts.set_tipo_teorico --patio-codigo 02 \
        --lleno 1-7 --vacio 8-11
"""
import argparse
import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.enums import TipoContenedor
from app.models.ubicacion import Carril, Patio


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fija tipo_teorico en carriles existentes")
    parser.add_argument("--patio-codigo", required=True)
    parser.add_argument("--lleno", help="Rango de carriles, ej. 1-7 o 1,2,3")
    parser.add_argument("--vacio", help="Rango de carriles, ej. 8-11 o 8,9,10,11")
    args = parser.parse_args()

    if not args.lleno and not args.vacio:
        parser.error("indica al menos --lleno o --vacio")

    return args


def _parse_rango(spec: str) -> list[int]:
    numeros: list[int] = []
    for parte in spec.split(","):
        parte = parte.strip()
        if "-" in parte:
            inicio, fin = parte.split("-", 1)
            numeros.extend(range(int(inicio), int(fin) + 1))
        else:
            numeros.append(int(parte))
    return numeros


async def main() -> int:
    args = _parse_args()

    cambios: list[tuple[TipoContenedor, list[int]]] = []
    if args.lleno:
        cambios.append((TipoContenedor.LLENO, _parse_rango(args.lleno)))
    if args.vacio:
        cambios.append((TipoContenedor.VACIO, _parse_rango(args.vacio)))

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        patio_result = await db.execute(select(Patio).where(Patio.codigo == args.patio_codigo))
        patio = patio_result.scalar_one_or_none()
        if patio is None:
            print(f"No existe un patio con codigo {args.patio_codigo}.")
            return 1

        actualizados = 0
        no_encontrados: list[str] = []

        for tipo, numeros in cambios:
            for n in numeros:
                codigo = f"A{n:02d}"
                existente = await db.execute(
                    select(Carril).where(Carril.patio_id == patio.id, Carril.codigo == codigo)
                )
                carril = existente.scalar_one_or_none()
                if carril is None:
                    no_encontrados.append(codigo)
                    continue
                carril.tipo_teorico = tipo
                actualizados += 1

        await db.commit()
        print(f"Carriles actualizados: {actualizados}.")
        if no_encontrados:
            print(f"Codigos no encontrados: {', '.join(no_encontrados)}.")

    await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
