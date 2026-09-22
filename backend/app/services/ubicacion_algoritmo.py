import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contenedor import Contenedor
from app.models.ubicacion import Carril, Tira, Tramo, Ubicacion

PESO_DISTANCIA = 0.40
PESO_TIPO = 0.25
PESO_PESO = 0.15
PESO_BLOQUEO = 0.15
PESO_DESTINO = 0.05
MAX_DISTANCIA_PATIO = 20


@dataclass(frozen=True)
class Coordenadas:
    carril_orden: int
    tramo_orden: int
    tira_orden: int
    nivel: int


@dataclass(frozen=True)
class CandidatoUbicacion:
    ubicacion_id: uuid.UUID
    codigo: str
    costo: float
    tira_id: uuid.UUID
    nivel: int


def distancia_manhattan(a: Coordenadas, b: Coordenadas) -> int:
    return (
        abs(a.carril_orden - b.carril_orden)
        + abs(a.tramo_orden - b.tramo_orden)
        + abs(a.tira_orden - b.tira_orden)
        + abs(a.nivel - b.nivel)
    )


async def _coordenadas_de_ubicacion(db: AsyncSession, ubicacion: Ubicacion) -> Coordenadas:
    result = await db.execute(
        select(Tira.orden, Tramo.orden, Carril.orden)
        .join(Tramo, Tira.tramo_id == Tramo.id)
        .join(Carril, Tramo.carril_id == Carril.id)
        .where(Tira.id == ubicacion.tira_id)
    )
    tira_orden, tramo_orden, carril_orden = result.one()
    return Coordenadas(carril_orden, tramo_orden, tira_orden, ubicacion.nivel)


async def _contenedor_en_nivel_inferior(
    db: AsyncSession, tira_id: uuid.UUID, nivel: int
) -> Contenedor | None:
    if nivel <= 1:
        return None
    result = await db.execute(
        select(Contenedor)
        .join(Ubicacion, Contenedor.ubicacion_id == Ubicacion.id)
        .where(Ubicacion.tira_id == tira_id, Ubicacion.nivel == nivel - 1)
    )
    return result.scalar_one_or_none()


async def _tipo_teorico_carril(db: AsyncSession, tira_id: uuid.UUID):
    result = await db.execute(
        select(Carril.tipo_teorico)
        .join(Tramo, Tramo.carril_id == Carril.id)
        .join(Tira, Tira.tramo_id == Tramo.id)
        .where(Tira.id == tira_id)
    )
    return result.scalar_one_or_none()


async def calcular_costo(
    db: AsyncSession, ubicacion: Ubicacion, contenedor: Contenedor, punto_referencia: Coordenadas
) -> float:
    coords = await _coordenadas_de_ubicacion(db, ubicacion)
    d = distancia_manhattan(coords, punto_referencia)

    tipo_teorico = await _tipo_teorico_carril(db, ubicacion.tira_id)
    pen_tipo = 0.0 if tipo_teorico is None or tipo_teorico == contenedor.tipo else 0.3

    if ubicacion.nivel == 1:
        pen_peso = 0.0
    else:
        contenedor_abajo = await _contenedor_en_nivel_inferior(db, ubicacion.tira_id, ubicacion.nivel)
        if contenedor_abajo is None or contenedor.peso_kg > contenedor_abajo.peso_kg:
            pen_peso = 1.0
        else:
            pen_peso = 0.0

    pen_bloqueo = round((5 - ubicacion.nivel) / 4 * 0.6, 4)

    if contenedor.fecha_estimada_salida is None:
        pen_destino = 0.0
    else:
        horas_restantes = (
            contenedor.fecha_estimada_salida - datetime.now(timezone.utc)
        ).total_seconds() / 3600
        normalizado = min(d / MAX_DISTANCIA_PATIO, 1.0)
        factor = 0.8 if horas_restantes <= 48 else 0.2
        pen_destino = normalizado * factor

    return (
        PESO_DISTANCIA * d
        + PESO_TIPO * pen_tipo
        + PESO_PESO * pen_peso
        + PESO_BLOQUEO * pen_bloqueo
        + PESO_DESTINO * pen_destino
    )


async def sugerir_ubicacion(
    db: AsyncSession,
    *,
    patio_id: uuid.UUID,
    contenedor: Contenedor,
    punto_referencia_ubicacion_id: uuid.UUID,
) -> CandidatoUbicacion:
    ref_result = await db.execute(select(Ubicacion).where(Ubicacion.id == punto_referencia_ubicacion_id))
    ref_ubicacion = ref_result.scalar_one()
    punto_referencia = await _coordenadas_de_ubicacion(db, ref_ubicacion)

    libres_result = await db.execute(
        select(Ubicacion)
        .join(Tira, Ubicacion.tira_id == Tira.id)
        .join(Tramo, Tira.tramo_id == Tramo.id)
        .join(Carril, Tramo.carril_id == Carril.id)
        .outerjoin(Contenedor, Contenedor.ubicacion_id == Ubicacion.id)
        .where(Carril.patio_id == patio_id, Ubicacion.activo.is_(True), Contenedor.id.is_(None))
    )
    candidatos_libres = libres_result.scalars().all()

    evaluados: list[CandidatoUbicacion] = []
    for ubicacion in candidatos_libres:
        if ubicacion.nivel > 1:
            abajo = await _contenedor_en_nivel_inferior(db, ubicacion.tira_id, ubicacion.nivel)
            if abajo is None:
                continue
        costo = await calcular_costo(db, ubicacion, contenedor, punto_referencia)
        evaluados.append(
            CandidatoUbicacion(
                ubicacion.id, ubicacion.codigo, costo, ubicacion.tira_id, ubicacion.nivel
            )
        )

    if not evaluados:
        raise ValueError("No hay ubicaciones disponibles que cumplan las restricciones")

    evaluados.sort(key=lambda c: c.costo)
    return evaluados[0]
