import datetime
import math
import uuid
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cliente import Cliente
from app.models.contenedor import Contenedor, Movimiento
from app.models.enums import (
    EstadoContenedor,
    TipoContenedor,
    TipoMovimiento,
)
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
from app.models.usuario import Usuario
from app.schemas.reportes import (
    FiltrosReporte,
    ReporteColumna,
    ReporteKpi,
    ReportePreviewOut,
    ReporteTipo,
)

COLUMNAS_POR_REPORTE: dict[ReporteTipo, list[ReporteColumna]] = {
    ReporteTipo.CONTAINERS_IN_YARD: [
        ReporteColumna(key="contenedor", label="Contenedor", align="center"),
        ReporteColumna(key="cliente", label="Cliente", align="left"),
        ReporteColumna(key="tipo", label="Tipo", align="center"),
        ReporteColumna(key="tamano", label="Tamaño", align="center"),
        ReporteColumna(key="estadia", label="Estadía (Días)", align="center"),
        ReporteColumna(key="fecha_entrada", label="Fecha de Entrada", align="center"),
        ReporteColumna(key="sellos", label="Sellos", align="center"),
        ReporteColumna(key="patio", label="Patio", align="left"),
        ReporteColumna(key="viaje", label="Viaje", align="center"),
    ],
    ReporteTipo.ENTRY_MOVEMENTS: [
        ReporteColumna(key="folio", label="Folio", align="center"),
        ReporteColumna(key="numero_viaje", label="Número de Viaje", align="center"),
        ReporteColumna(key="fecha_entrada", label="Fecha Entrada", align="center"),
        ReporteColumna(key="estado", label="Estado", align="center"),
        ReporteColumna(key="operador", label="Operador", align="left"),
        ReporteColumna(key="placas", label="Placas", align="center"),
        ReporteColumna(key="economico", label="Económico", align="center"),
        ReporteColumna(key="transportista", label="Transportista", align="left"),
        ReporteColumna(key="cliente", label="Cliente", align="left"),
        ReporteColumna(key="patio", label="Patio", align="left"),
        ReporteColumna(key="contenedor", label="Contenedor", align="center"),
        ReporteColumna(key="condicion", label="Condición", align="center"),
    ],
    ReporteTipo.DEPARTURE_MOVEMENTS: [
        ReporteColumna(key="folio", label="Folio", align="center"),
        ReporteColumna(key="numero_viaje", label="Número de Viaje", align="center"),
        ReporteColumna(key="fecha_entrada", label="Fecha Entrada", align="center"),
        ReporteColumna(key="fecha_salida", label="Fecha Salida", align="center"),
        ReporteColumna(key="estado", label="Estado", align="center"),
        ReporteColumna(key="operador", label="Operador", align="left"),
        ReporteColumna(key="placas", label="Placas", align="center"),
        ReporteColumna(key="economico", label="Económico", align="center"),
        ReporteColumna(key="transportista", label="Transportista", align="left"),
        ReporteColumna(key="cliente", label="Cliente", align="left"),
        ReporteColumna(key="patio", label="Patio", align="left"),
        ReporteColumna(key="contenedor", label="Contenedor", align="center"),
        ReporteColumna(key="condicion", label="Condición", align="center"),
    ],
    ReporteTipo.POSITIONS: [
        ReporteColumna(key="contenedor", label="No. CONTENEDOR", align="center"),
        ReporteColumna(key="posicion", label="POSICION", align="center"),
        ReporteColumna(key="carril", label="CARRIL", align="center"),
        ReporteColumna(key="tramo", label="TRAMO", align="center"),
        ReporteColumna(key="tira", label="TIRA", align="center"),
        ReporteColumna(key="altura", label="ALTURA", align="center"),
        ReporteColumna(key="fecha", label="FECHA", align="center"),
    ],
    ReporteTipo.SPECIAL_SERVICES: [
        ReporteColumna(key="servicio", label="Servicio", align="left"),
        ReporteColumna(key="cliente", label="Cliente", align="left"),
        ReporteColumna(key="patio", label="Patio", align="left"),
        ReporteColumna(key="contenedor", label="Contenedor", align="center"),
        ReporteColumna(key="fecha_servicio", label="Fecha de Servicio", align="center"),
        ReporteColumna(key="cantidad", label="Cantidad", align="right"),
        ReporteColumna(key="unidad", label="Unidad", align="center"),
    ],
}

TITULOS_POR_REPORTE: dict[ReporteTipo, tuple[str, str]] = {
    ReporteTipo.CONTAINERS_IN_YARD: (
        "Contenedores en Patio",
        "Inventario y permanencia de contenedores activos en patio",
    ),
    ReporteTipo.ENTRY_MOVEMENTS: (
        "Movimientos de Entrada",
        "Histórico de ingresos de contenedores registrados",
    ),
    ReporteTipo.DEPARTURE_MOVEMENTS: (
        "Movimientos de Salida",
        "Histórico de salidas y despachos de contenedores",
    ),
    ReporteTipo.POSITIONS: (
        "Reporte de Posiciones",
        "Mapeo de contenedores ubicados por carril, tramo, tira y nivel",
    ),
    ReporteTipo.SPECIAL_SERVICES: (
        "Servicios Especiales",
        "Registro de servicios extraordinarios aplicados a contenedores",
    ),
}


def _formatear_fecha(dt: datetime.datetime | None) -> str:
    if not dt:
        return ""
    return dt.strftime("%d/%m/%Y %H:%M:%S")


async def obtener_datos_contenedores_en_patio(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> tuple[list[dict[str, Any]], int, list[ReporteKpi]]:
    estados_activos = [
        EstadoContenedor.INGRESADO,
        EstadoContenedor.UBICADO,
        EstadoContenedor.EN_ESTADIA,
        EstadoContenedor.EN_SERVICIO_ESPECIAL,
    ]

    stmt = (
        select(Contenedor, Cliente, Patio)
        .outerjoin(Cliente, Contenedor.cliente_id == Cliente.id)
        .outerjoin(Patio, Contenedor.patio_id == Patio.id)
        .where(Contenedor.estado.in_(estados_activos))
    )

    if patios_ids:
        stmt = stmt.where(Contenedor.patio_id.in_(patios_ids))
    if filtros.patio_id:
        stmt = stmt.where(Contenedor.patio_id == filtros.patio_id)
    if filtros.cliente_id:
        stmt = stmt.where(Contenedor.cliente_id == filtros.cliente_id)
    if filtros.fecha_inicio:
        inicio_dt = datetime.datetime.combine(filtros.fecha_inicio, datetime.time.min, tzinfo=datetime.timezone.utc)
        stmt = stmt.where(Contenedor.created_at >= inicio_dt)
    if filtros.fecha_fin:
        fin_dt = datetime.datetime.combine(filtros.fecha_fin, datetime.time.max, tzinfo=datetime.timezone.utc)
        stmt = stmt.where(Contenedor.created_at <= fin_dt)
    if filtros.busqueda:
        term = f"%{filtros.busqueda.strip()}%"
        stmt = stmt.where(Contenedor.numero_contenedor.ilike(term))

    # Obtener total y todos para métricas
    res_all = await db.execute(stmt.order_by(Contenedor.created_at.desc()))
    items_all = res_all.all()
    total = len(items_all)

    ahora = datetime.datetime.now(datetime.timezone.utc)
    llenos = 0
    vacios = 0
    dias_totales = 0

    for c, cli, p in items_all:
        if c.tipo == TipoContenedor.LLENO:
            llenos += 1
        else:
            vacios += 1
        dias = max(0, (ahora - c.created_at).days) if c.created_at else 0
        dias_totales += dias

    estadia_promedio = (dias_totales / total) if total > 0 else 0.0

    # Paginación
    offset = (filtros.page - 1) * filtros.page_size
    items_pag = items_all[offset : offset + filtros.page_size]

    filas = []
    for c, cli, p in items_pag:
        dias = max(0, (ahora - c.created_at).days) if c.created_at else 0
        tipo_str = "Lleno" if c.tipo == TipoContenedor.LLENO else "Vacío"
        tamano_val = c.tamano.value if hasattr(c.tamano, "value") else str(c.tamano)
        filas.append(
            {
                "contenedor": c.numero_contenedor,
                "cliente": cli.razon_social if cli else "Sin cliente",
                "tipo": tipo_str,
                "tamano": f"CONTENEDOR ESTANDAR {tamano_val}\"",
                "estadia": dias,
                "fecha_entrada": _formatear_fecha(c.created_at),
                "sellos": "",
                "patio": p.nombre if p else "",
                "viaje": f"ENT{str(c.id)[:6].upper()}",
            }
        )

    kpis = [
        ReporteKpi(label="Total Contenedores", value=str(total), tone="info"),
        ReporteKpi(label="Llenos", value=str(llenos), subtext=f"{(llenos/total*100):.0f}% del total" if total else "0%", tone="success"),
        ReporteKpi(label="Vacíos", value=str(vacios), subtext=f"{(vacios/total*100):.0f}% del total" if total else "0%", tone="warning"),
        ReporteKpi(label="Estadía Promedio", value=f"{estadia_promedio:.1f} días", tone="info"),
    ]

    return filas, total, kpis


async def obtener_datos_movimientos_entrada(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> tuple[list[dict[str, Any]], int, list[ReporteKpi]]:
    stmt = (
        select(Movimiento, Contenedor, Cliente, Patio, Usuario)
        .join(Contenedor, Movimiento.contenedor_id == Contenedor.id)
        .outerjoin(Cliente, Contenedor.cliente_id == Cliente.id)
        .outerjoin(Patio, Movimiento.patio_id == Patio.id)
        .outerjoin(Usuario, Movimiento.operador_id == Usuario.id)
        .where(Movimiento.tipo == TipoMovimiento.INGRESO)
    )

    if patios_ids:
        stmt = stmt.where(Movimiento.patio_id.in_(patios_ids))
    if filtros.patio_id:
        stmt = stmt.where(Movimiento.patio_id == filtros.patio_id)
    if filtros.cliente_id:
        stmt = stmt.where(Contenedor.cliente_id == filtros.cliente_id)
    if filtros.fecha_inicio:
        inicio_dt = datetime.datetime.combine(filtros.fecha_inicio, datetime.time.min, tzinfo=datetime.timezone.utc)
        stmt = stmt.where(Movimiento.ts >= inicio_dt)
    if filtros.fecha_fin:
        fin_dt = datetime.datetime.combine(filtros.fecha_fin, datetime.time.max, tzinfo=datetime.timezone.utc)
        stmt = stmt.where(Movimiento.ts <= fin_dt)
    if filtros.busqueda:
        term = f"%{filtros.busqueda.strip()}%"
        stmt = stmt.where(Contenedor.numero_contenedor.ilike(term))

    res_all = await db.execute(stmt.order_by(Movimiento.ts.desc()))
    items_all = res_all.all()
    total = len(items_all)

    llenos = sum(1 for m, c, cli, p, u in items_all if c.tipo == TipoContenedor.LLENO)
    vacios = total - llenos

    offset = (filtros.page - 1) * filtros.page_size
    items_pag = items_all[offset : offset + filtros.page_size]

    filas = []
    for idx, (m, c, cli, p, u) in enumerate(items_pag, start=offset + 1):
        condicion_str = "Lleno" if c.tipo == TipoContenedor.LLENO else "Vacío"
        mes_ano = m.ts.strftime("%b%y").upper() if m.ts else "26"
        numero_viaje = f"ENT{str(m.id)[:6].upper()}-{mes_ano}"
        filas.append(
            {
                "folio": idx,
                "numero_viaje": numero_viaje,
                "fecha_entrada": _formatear_fecha(m.ts),
                "estado": "Completado",
                "operador": u.nombre if u else "Operador Sistema",
                "placas": "N/A",
                "economico": "N/A",
                "transportista": cli.razon_social if cli else "Transportista Especializado",
                "cliente": cli.razon_social if cli else "Sin cliente",
                "patio": p.nombre if p else "",
                "contenedor": c.numero_contenedor,
                "condicion": condicion_str,
            }
        )

    kpis = [
        ReporteKpi(label="Total Entradas", value=str(total), tone="info"),
        ReporteKpi(label="Llenos", value=str(llenos), tone="success"),
        ReporteKpi(label="Vacíos", value=str(vacios), tone="warning"),
    ]

    return filas, total, kpis


async def obtener_datos_movimientos_salida(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> tuple[list[dict[str, Any]], int, list[ReporteKpi]]:
    stmt = (
        select(Movimiento, Contenedor, Cliente, Patio, Usuario)
        .join(Contenedor, Movimiento.contenedor_id == Contenedor.id)
        .outerjoin(Cliente, Contenedor.cliente_id == Cliente.id)
        .outerjoin(Patio, Movimiento.patio_id == Patio.id)
        .outerjoin(Usuario, Movimiento.operador_id == Usuario.id)
        .where(Movimiento.tipo == TipoMovimiento.SALIDA)
    )

    if patios_ids:
        stmt = stmt.where(Movimiento.patio_id.in_(patios_ids))
    if filtros.patio_id:
        stmt = stmt.where(Movimiento.patio_id == filtros.patio_id)
    if filtros.cliente_id:
        stmt = stmt.where(Contenedor.cliente_id == filtros.cliente_id)
    if filtros.fecha_inicio:
        inicio_dt = datetime.datetime.combine(filtros.fecha_inicio, datetime.time.min, tzinfo=datetime.timezone.utc)
        stmt = stmt.where(Movimiento.ts >= inicio_dt)
    if filtros.fecha_fin:
        fin_dt = datetime.datetime.combine(filtros.fecha_fin, datetime.time.max, tzinfo=datetime.timezone.utc)
        stmt = stmt.where(Movimiento.ts <= fin_dt)
    if filtros.busqueda:
        term = f"%{filtros.busqueda.strip()}%"
        stmt = stmt.where(Contenedor.numero_contenedor.ilike(term))

    res_all = await db.execute(stmt.order_by(Movimiento.ts.desc()))
    items_all = res_all.all()
    total = len(items_all)

    llenos = sum(1 for m, c, cli, p, u in items_all if c.tipo == TipoContenedor.LLENO)
    vacios = total - llenos

    offset = (filtros.page - 1) * filtros.page_size
    items_pag = items_all[offset : offset + filtros.page_size]

    filas = []
    for idx, (m, c, cli, p, u) in enumerate(items_pag, start=offset + 1):
        condicion_str = "Lleno" if c.tipo == TipoContenedor.LLENO else "Vacío"
        mes_ano = m.ts.strftime("%b%y").upper() if m.ts else "26"
        numero_viaje = f"SAL{str(m.id)[:6].upper()}-{mes_ano}"
        filas.append(
            {
                "folio": idx,
                "numero_viaje": numero_viaje,
                "fecha_entrada": _formatear_fecha(c.created_at),
                "fecha_salida": _formatear_fecha(m.ts),
                "estado": "Completado",
                "operador": u.nombre if u else "Operador Sistema",
                "placas": "N/A",
                "economico": "N/A",
                "transportista": cli.razon_social if cli else "Transportista Especializado",
                "cliente": cli.razon_social if cli else "Sin cliente",
                "patio": p.nombre if p else "",
                "contenedor": c.numero_contenedor,
                "condicion": condicion_str,
            }
        )

    kpis = [
        ReporteKpi(label="Total Salidas", value=str(total), tone="info"),
        ReporteKpi(label="Llenos", value=str(llenos), tone="success"),
        ReporteKpi(label="Vacíos", value=str(vacios), tone="warning"),
    ]

    return filas, total, kpis


async def obtener_datos_posiciones(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> tuple[list[dict[str, Any]], int, list[ReporteKpi]]:
    estados_activos = [
        EstadoContenedor.INGRESADO,
        EstadoContenedor.UBICADO,
        EstadoContenedor.EN_ESTADIA,
        EstadoContenedor.EN_SERVICIO_ESPECIAL,
    ]

    stmt = (
        select(Contenedor, Ubicacion, Tira, Tramo, Carril, Patio)
        .join(Ubicacion, Contenedor.ubicacion_id == Ubicacion.id)
        .join(Tira, Ubicacion.tira_id == Tira.id)
        .join(Tramo, Tira.tramo_id == Tramo.id)
        .join(Carril, Tramo.carril_id == Carril.id)
        .join(Patio, Carril.patio_id == Patio.id)
        .where(Contenedor.ubicacion_id.isnot(None))
        .where(Contenedor.estado.in_(estados_activos))
    )

    if patios_ids:
        stmt = stmt.where(Contenedor.patio_id.in_(patios_ids))
    if filtros.patio_id:
        stmt = stmt.where(Contenedor.patio_id == filtros.patio_id)
    if filtros.cliente_id:
        stmt = stmt.where(Contenedor.cliente_id == filtros.cliente_id)
    if filtros.fecha_inicio:
        inicio_dt = datetime.datetime.combine(filtros.fecha_inicio, datetime.time.min, tzinfo=datetime.timezone.utc)
        stmt = stmt.where(Contenedor.created_at >= inicio_dt)
    if filtros.fecha_fin:
        fin_dt = datetime.datetime.combine(filtros.fecha_fin, datetime.time.max, tzinfo=datetime.timezone.utc)
        stmt = stmt.where(Contenedor.created_at <= fin_dt)
    if filtros.busqueda:
        term = f"%{filtros.busqueda.strip()}%"
        stmt = stmt.where(Contenedor.numero_contenedor.ilike(term))

    res_all = await db.execute(stmt.order_by(Carril.orden, Tramo.orden, Tira.orden, Ubicacion.nivel))
    items_all = res_all.all()
    total = len(items_all)

    nivel_1 = sum(1 for c, ub, ti, tr, ca, p in items_all if ub.nivel == 1)
    nivel_superior = total - nivel_1

    offset = (filtros.page - 1) * filtros.page_size
    items_pag = items_all[offset : offset + filtros.page_size]

    filas = []
    for c, ub, ti, tr, ca, p in items_pag:
        pos_codigo = f"{p.codigo}-{ca.orden:02d}-{tr.orden:02d}-{ti.orden:02d}-{ub.nivel}"
        filas.append(
            {
                "contenedor": c.numero_contenedor,
                "posicion": pos_codigo,
                "carril": str(ca.orden),
                "tramo": str(tr.orden),
                "tira": str(ti.orden),
                "altura": str(ub.nivel),
                "fecha": _formatear_fecha(c.created_at),
            }
        )

    kpis = [
        ReporteKpi(label="Total Ocupadas", value=str(total), tone="info"),
        ReporteKpi(label="Nivel 1 (Piso)", value=str(nivel_1), tone="success"),
        ReporteKpi(label="Nivel > 1 (Estiba)", value=str(nivel_superior), tone="warning"),
    ]

    return filas, total, kpis


async def obtener_datos_servicios_especiales(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> tuple[list[dict[str, Any]], int, list[ReporteKpi]]:
    stmt = (
        select(Movimiento, Contenedor, Cliente, Patio)
        .outerjoin(Contenedor, Movimiento.contenedor_id == Contenedor.id)
        .outerjoin(Cliente, Contenedor.cliente_id == Cliente.id)
        .outerjoin(Patio, Movimiento.patio_id == Patio.id)
        .where(Movimiento.tipo == TipoMovimiento.SERVICIO)
    )

    if patios_ids:
        stmt = stmt.where(Movimiento.patio_id.in_(patios_ids))
    if filtros.patio_id:
        stmt = stmt.where(Movimiento.patio_id == filtros.patio_id)
    if filtros.cliente_id:
        stmt = stmt.where(Contenedor.cliente_id == filtros.cliente_id)
    if filtros.fecha_inicio:
        inicio_dt = datetime.datetime.combine(filtros.fecha_inicio, datetime.time.min, tzinfo=datetime.timezone.utc)
        stmt = stmt.where(Movimiento.ts >= inicio_dt)
    if filtros.fecha_fin:
        fin_dt = datetime.datetime.combine(filtros.fecha_fin, datetime.time.max, tzinfo=datetime.timezone.utc)
        stmt = stmt.where(Movimiento.ts <= fin_dt)
    if filtros.busqueda:
        term = f"%{filtros.busqueda.strip()}%"
        stmt = stmt.where(
            Contenedor.numero_contenedor.ilike(term) | Movimiento.motivo_override.ilike(term)
        )

    res_all = await db.execute(stmt.order_by(Movimiento.ts.desc()))
    items_all = res_all.all()
    total = len(items_all)

    offset = (filtros.page - 1) * filtros.page_size
    items_pag = items_all[offset : offset + filtros.page_size]

    filas = []
    for m, c, cli, p in items_pag:
        nombre_servicio = m.motivo_override or "SERVICIO ESPECIAL"
        filas.append(
            {
                "servicio": nombre_servicio,
                "cliente": cli.razon_social if cli else "Sin cliente",
                "patio": p.nombre if p else "",
                "contenedor": c.numero_contenedor if c else "N/A",
                "fecha_servicio": _formatear_fecha(m.ts),
                "cantidad": 1,
                "unidad": "SERVICIO",
            }
        )

    kpis = [
        ReporteKpi(label="Total Servicios", value=str(total), tone="info"),
    ]

    return filas, total, kpis


async def obtener_datos_reporte(
    db: AsyncSession,
    tipo: ReporteTipo,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> tuple[list[dict[str, Any]], int, list[ReporteKpi]]:
    if tipo == ReporteTipo.CONTAINERS_IN_YARD:
        return await obtener_datos_contenedores_en_patio(db, filtros, patios_ids)
    elif tipo == ReporteTipo.ENTRY_MOVEMENTS:
        return await obtener_datos_movimientos_entrada(db, filtros, patios_ids)
    elif tipo == ReporteTipo.DEPARTURE_MOVEMENTS:
        return await obtener_datos_movimientos_salida(db, filtros, patios_ids)
    elif tipo == ReporteTipo.POSITIONS:
        return await obtener_datos_posiciones(db, filtros, patios_ids)
    elif tipo == ReporteTipo.SPECIAL_SERVICES:
        return await obtener_datos_servicios_especiales(db, filtros, patios_ids)
    else:
        raise ValueError(f"Tipo de reporte desconocido: {tipo}")


async def obtener_preview_reporte(
    db: AsyncSession,
    tipo: ReporteTipo,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> ReportePreviewOut:
    filas, total, kpis = await obtener_datos_reporte(db, tipo, filtros, patios_ids)
    titulo, subtitulo = TITULOS_POR_REPORTE.get(tipo, ("Reporte", "Reporte operativo"))
    columnas = COLUMNAS_POR_REPORTE.get(tipo, [])
    total_paginas = max(1, math.ceil(total / filtros.page_size)) if total > 0 else 1

    return ReportePreviewOut(
        tipo=tipo,
        titulo=titulo,
        subtitulo=subtitulo,
        total_registros=total,
        columnas=columnas,
        filas=filas,
        kpis=kpis,
        page=filtros.page,
        page_size=filtros.page_size,
        total_paginas=total_paginas,
    )
