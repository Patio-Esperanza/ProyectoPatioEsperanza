import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contenedor import Contenedor
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
from app.schemas.mapa import (
    CarrilMapaOut,
    ContenedorEnNivelOut,
    DetalleTiraOut,
    MapaPatioOut,
    NivelTiraOut,
    ResumenMapaOut,
    TiraMapaOut,
    TramoMapaOut,
)


async def obtener_mapa(db: AsyncSession, patio_id: uuid.UUID) -> MapaPatioOut:
    """Ocupacion del patio agregada por tira.

    Una sola consulta. El mapa nunca carga las ubicaciones una por una: en un patio
    mediano son unas 7,200 filas contra unas 1,440 tiras.
    """
    patio_result = await db.execute(select(Patio).where(Patio.id == patio_id))
    patio = patio_result.scalar_one()

    filas = await db.execute(
        select(
            Carril.id.label("carril_id"),
            Carril.codigo.label("carril_codigo"),
            Carril.orden.label("carril_orden"),
            Carril.tipo_teorico.label("carril_tipo"),
            Tramo.id.label("tramo_id"),
            Tramo.codigo.label("tramo_codigo"),
            Tramo.orden.label("tramo_orden"),
            Tira.id.label("tira_id"),
            Tira.codigo.label("tira_codigo"),
            Tira.orden.label("tira_orden"),
            func.count(Ubicacion.id).label("niveles_totales"),
            func.count(Ubicacion.id)
            .filter(Ubicacion.activo.is_(True))
            .label("niveles_activos"),
            func.count(Contenedor.id).label("niveles_ocupados"),
        )
        .select_from(Carril)
        .join(Tramo, Tramo.carril_id == Carril.id)
        .join(Tira, Tira.tramo_id == Tramo.id)
        .outerjoin(Ubicacion, Ubicacion.tira_id == Tira.id)
        .outerjoin(Contenedor, Contenedor.ubicacion_id == Ubicacion.id)
        .where(Carril.patio_id == patio_id)
        .group_by(
            Carril.id,
            Carril.codigo,
            Carril.orden,
            Carril.tipo_teorico,
            Tramo.id,
            Tramo.codigo,
            Tramo.orden,
            Tira.id,
            Tira.codigo,
            Tira.orden,
        )
        .order_by(Carril.orden, Tramo.orden, Tira.orden)
    )

    carriles: list[CarrilMapaOut] = []
    ubicaciones_activas = 0
    ocupadas = 0

    for fila in filas:
        if not carriles or carriles[-1].id != fila.carril_id:
            carriles.append(
                CarrilMapaOut(
                    id=fila.carril_id,
                    codigo=fila.carril_codigo,
                    orden=fila.carril_orden,
                    tipo_teorico=fila.carril_tipo,
                    tramos=[],
                )
            )
        carril = carriles[-1]

        if not carril.tramos or carril.tramos[-1].id != fila.tramo_id:
            carril.tramos.append(
                TramoMapaOut(
                    id=fila.tramo_id,
                    codigo=fila.tramo_codigo,
                    orden=fila.tramo_orden,
                    tiras=[],
                )
            )
        tramo = carril.tramos[-1]

        tramo.tiras.append(
            TiraMapaOut(
                id=fila.tira_id,
                codigo=fila.tira_codigo,
                orden=fila.tira_orden,
                niveles_totales=fila.niveles_totales,
                niveles_activos=fila.niveles_activos,
                niveles_ocupados=fila.niveles_ocupados,
            )
        )
        ubicaciones_activas += fila.niveles_activos
        ocupadas += fila.niveles_ocupados

    return MapaPatioOut(
        patio_id=patio.id,
        ubicacion_entrada_id=patio.ubicacion_entrada_id,
        resumen=ResumenMapaOut(ubicaciones_activas=ubicaciones_activas, ocupadas=ocupadas),
        carriles=carriles,
    )


async def obtener_detalle_tira(db: AsyncSession, tira_id: uuid.UUID) -> DetalleTiraOut | None:
    """Los niveles de una tira con el contenedor de cada uno.

    El codigo que devuelve es el compuesto carril-tramo-tira, porque ese es el que el
    operador ve en el patio; el `codigo` de la tabla `tiras` solo distingue dentro del tramo.
    """
    encabezado = await db.execute(
        select(Carril.codigo, Tramo.codigo, Tira.codigo)
        .select_from(Tira)
        .join(Tramo, Tira.tramo_id == Tramo.id)
        .join(Carril, Tramo.carril_id == Carril.id)
        .where(Tira.id == tira_id)
    )
    fila_encabezado = encabezado.one_or_none()
    if fila_encabezado is None:
        return None
    carril_codigo, tramo_codigo, tira_codigo = fila_encabezado

    filas = await db.execute(
        select(Ubicacion, Contenedor)
        .outerjoin(Contenedor, Contenedor.ubicacion_id == Ubicacion.id)
        .where(Ubicacion.tira_id == tira_id)
        .order_by(Ubicacion.nivel)
    )

    niveles: list[NivelTiraOut] = []
    for ubicacion, contenedor in filas:
        niveles.append(
            NivelTiraOut(
                nivel=ubicacion.nivel,
                ubicacion_id=ubicacion.id,
                codigo=ubicacion.codigo,
                activo=ubicacion.activo,
                capacidad_peso_kg=ubicacion.capacidad_peso_kg,
                contenedor=(
                    None
                    if contenedor is None
                    else ContenedorEnNivelOut(
                        id=contenedor.id,
                        numero_contenedor=contenedor.numero_contenedor,
                        tipo=contenedor.tipo,
                        tamano=contenedor.tamano,
                        peso_kg=contenedor.peso_kg,
                        estado=contenedor.estado,
                    )
                ),
            )
        )

    return DetalleTiraOut(
        tira_id=tira_id,
        codigo=f"{carril_codigo}-{tramo_codigo}-{tira_codigo}",
        niveles=niveles,
    )
