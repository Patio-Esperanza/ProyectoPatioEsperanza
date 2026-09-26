"""Carga el layout de un patio: carriles, tramos, tiras y ubicaciones.

Es idempotente: si ya existe un carril con el codigo que va a generar, lo salta.

Modo uniforme (mismo numero de tramos/tiras/niveles en todo el patio):
    python -m scripts.seed_patio_layout --patio-codigo PN \
        --carriles 12 --tramos 10 --tiras 12 --niveles 5 --entrada A01-T01-R01-N1

Modo config (carriles, tramos, tiras y niveles variables por tira, ver
scripts/patio_layout.example.json para el formato):
    python -m scripts.seed_patio_layout --patio-codigo PN \
        --config scripts/patio_layout.json --entrada A01-T01-R01-N1
"""
import argparse
import asyncio
import json
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.enums import TipoContenedor
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion

NIVEL_MIN = 1
NIVEL_MAX = 5


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Carga el layout de un patio")
    parser.add_argument("--patio-codigo", required=True)
    parser.add_argument("--config", help="Ruta a un JSON con carriles/tramos/tiras/niveles variables")
    parser.add_argument("--carriles", type=int, help="Modo uniforme: numero de carriles")
    parser.add_argument("--tramos", type=int, help="Modo uniforme: tramos por carril")
    parser.add_argument("--tiras", type=int, help="Modo uniforme: tiras por tramo")
    parser.add_argument("--niveles", type=int, default=5, choices=range(NIVEL_MIN, NIVEL_MAX + 1))
    parser.add_argument(
        "--entrada",
        help="Codigo de la ubicacion que sirve de punto de entrada, por ejemplo A01-T01-R01-N1",
    )
    args = parser.parse_args()

    if args.config:
        if args.carriles or args.tramos or args.tiras:
            parser.error("--config no se combina con --carriles/--tramos/--tiras")
    elif not (args.carriles and args.tramos and args.tiras):
        parser.error("faltan --carriles/--tramos/--tiras (o usa --config)")

    return args


def _cargar_config(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    carriles = data.get("carriles") if isinstance(data, dict) else data
    if not isinstance(carriles, list) or not carriles:
        raise ValueError("el config debe tener una lista 'carriles' no vacia")

    for carril in carriles:
        if not carril.get("codigo"):
            raise ValueError(f"carril sin codigo: {carril}")
        tipo = carril.get("tipo_teorico")
        if tipo is not None and tipo not in (t.value for t in TipoContenedor):
            raise ValueError(f"tipo_teorico invalido en carril {carril['codigo']}: {tipo}")
        tramos = carril.get("tramos")
        if not isinstance(tramos, list) or not tramos:
            raise ValueError(f"carril {carril['codigo']} sin tramos")
        for tramo in tramos:
            if not tramo.get("codigo"):
                raise ValueError(f"tramo sin codigo en carril {carril['codigo']}: {tramo}")
            tiras = tramo.get("tiras")
            if not isinstance(tiras, list) or not tiras:
                raise ValueError(f"tramo {tramo['codigo']} (carril {carril['codigo']}) sin tiras")
            for tira in tiras:
                if not tira.get("codigo"):
                    raise ValueError(f"tira sin codigo en tramo {tramo['codigo']}: {tira}")
                niveles = tira.get("niveles")
                if not isinstance(niveles, int) or not (NIVEL_MIN <= niveles <= NIVEL_MAX):
                    raise ValueError(
                        f"tira {tira['codigo']} (tramo {tramo['codigo']}): niveles debe ser "
                        f"un entero entre {NIVEL_MIN} y {NIVEL_MAX}, recibido {niveles!r}"
                    )

    return carriles


async def _sembrar_uniforme(db: AsyncSession, patio: Patio, args: argparse.Namespace) -> tuple[int, int]:
    creados = 0
    saltados = 0

    for c in range(args.carriles):
        carril_codigo = f"A{c + 1:02d}"
        existente = await db.execute(
            select(Carril).where(Carril.patio_id == patio.id, Carril.codigo == carril_codigo)
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

    return creados, saltados


async def _sembrar_config(db: AsyncSession, patio: Patio, carriles_config: list[dict]) -> tuple[int, int]:
    creados = 0
    saltados = 0

    for c, carril_data in enumerate(carriles_config):
        carril_codigo = carril_data["codigo"]
        existente = await db.execute(
            select(Carril).where(Carril.patio_id == patio.id, Carril.codigo == carril_codigo)
        )
        if existente.scalar_one_or_none() is not None:
            saltados += 1
            continue

        tipo_teorico = carril_data.get("tipo_teorico")
        carril = Carril(
            patio_id=patio.id,
            codigo=carril_codigo,
            orden=c,
            tipo_teorico=TipoContenedor(tipo_teorico) if tipo_teorico else None,
        )
        db.add(carril)
        await db.flush()

        for t, tramo_data in enumerate(carril_data["tramos"]):
            tramo = Tramo(carril_id=carril.id, codigo=tramo_data["codigo"], orden=t)
            db.add(tramo)
            await db.flush()

            for r, tira_data in enumerate(tramo_data["tiras"]):
                tira = Tira(tramo_id=tramo.id, codigo=tira_data["codigo"], orden=r)
                db.add(tira)
                await db.flush()

                for n in range(1, tira_data["niveles"] + 1):
                    db.add(
                        Ubicacion(
                            tira_id=tira.id,
                            nivel=n,
                            codigo=f"{carril.codigo}-{tramo.codigo}-{tira.codigo}-N{n}",
                            activo=True,
                        )
                    )
                    creados += 1

    return creados, saltados


async def main() -> int:
    args = _parse_args()

    carriles_config = None
    if args.config:
        try:
            carriles_config = _cargar_config(args.config)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"Config invalido: {exc}")
            return 1

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        patio_result = await db.execute(select(Patio).where(Patio.codigo == args.patio_codigo))
        patio = patio_result.scalar_one_or_none()
        if patio is None:
            print(f"No existe un patio con codigo {args.patio_codigo}.")
            return 1

        if carriles_config is not None:
            creados, saltados = await _sembrar_config(db, patio, carriles_config)
        else:
            creados, saltados = await _sembrar_uniforme(db, patio, args)

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
