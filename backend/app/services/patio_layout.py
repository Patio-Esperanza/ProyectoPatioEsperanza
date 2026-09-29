from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion


async def sembrar_layout_uniforme(
    db: AsyncSession,
    patio: Patio,
    carriles: int,
    tramos: int,
    tiras: int,
    niveles: int,
) -> tuple[int, int, int]:
    """Crea carriles/tramos/tiras/ubicaciones con codigos A01/T01/R01/N1.

    Salta por completo un carril cuyo codigo ya exista (no le agrega tramos
    nuevos). No hace commit: quien llama decide cuando.
    """
    carriles_creados = 0
    carriles_saltados = 0
    ubicaciones_creadas = 0

    for c in range(carriles):
        carril_codigo = f"A{c + 1:02d}"
        existente = await db.execute(
            select(Carril).where(Carril.patio_id == patio.id, Carril.codigo == carril_codigo)
        )
        if existente.scalar_one_or_none() is not None:
            carriles_saltados += 1
            continue

        carril = Carril(patio_id=patio.id, codigo=carril_codigo, orden=c)
        db.add(carril)
        await db.flush()
        carriles_creados += 1

        for t in range(tramos):
            tramo = Tramo(carril_id=carril.id, codigo=f"T{t + 1:02d}", orden=t)
            db.add(tramo)
            await db.flush()

            for r in range(tiras):
                tira = Tira(tramo_id=tramo.id, codigo=f"R{r + 1:02d}", orden=r)
                db.add(tira)
                await db.flush()

                for n in range(1, niveles + 1):
                    db.add(
                        Ubicacion(
                            tira_id=tira.id,
                            nivel=n,
                            codigo=f"{carril.codigo}-{tramo.codigo}-{tira.codigo}-N{n}",
                            activo=True,
                        )
                    )
                    ubicaciones_creadas += 1

    return carriles_creados, carriles_saltados, ubicaciones_creadas
