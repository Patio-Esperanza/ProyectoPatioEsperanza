import datetime
import math
import uuid
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.config import zona_horaria_app
from app.core.sellos import mostrar_sellos
from app.models.cliente import Cliente
from app.models.contenedor import Contenedor, Movimiento, InventarioDiario, v_estancias_table
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


class ReportResultList(list):
    def __init__(self, filas: list[Any], total: int, kpis: list[ReporteKpi]):
        super().__init__(filas)
        self.filas = filas
        self.total = total
        self.kpis = kpis

    def __iter__(self):
        return iter((self.filas, self.total, self.kpis))


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
    ReporteTipo.INVENTORY_AT_DATE: [
        ReporteColumna(key="contenedor", label="Contenedor", align="center"),
        ReporteColumna(key="cliente", label="Cliente", align="left"),
        ReporteColumna(key="ubicacion", label="Ubicación", align="center"),
        ReporteColumna(key="estado", label="Estado", align="center"),
        ReporteColumna(key="dias_estancia", label="Días de Estancia", align="center"),
    ],
    ReporteTipo.STAY_BY_CLIENT: [
        ReporteColumna(key="contenedor", label="Contenedor", align="center"),
        ReporteColumna(key="cliente", label="Cliente", align="left"),
        ReporteColumna(key="fecha_ingreso", label="Fecha Ingreso", align="center"),
        ReporteColumna(key="fecha_salida", label="Fecha Salida", align="center"),
        ReporteColumna(key="dias", label="Días", align="center"),
        ReporteColumna(key="dias_libres", label="Días Libres", align="center"),
        ReporteColumna(key="dias_cobrables", label="Días Cobrables", align="center"),
        ReporteColumna(key="servicios", label="Servicios Realizados", align="left"),
    ],
    ReporteTipo.DAILY_SUMMARY: [
        ReporteColumna(key="fecha", label="Fecha", align="center"),
        ReporteColumna(key="entradas", label="Entradas", align="right"),
        ReporteColumna(key="salidas", label="Salidas", align="right"),
        ReporteColumna(key="saldo_cierre", label="Saldo al Cierre", align="right"),
        ReporteColumna(key="ocupacion", label="Ocupación %", align="right"),
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
    ReporteTipo.INVENTORY_AT_DATE: (
        "Inventario a una Fecha",
        "Inventario histórico de contenedores en patio a una fecha específica",
    ),
    ReporteTipo.STAY_BY_CLIENT: (
        "Estadía por Cliente",
        "Reporte detallado de estadía, días libres y días cobrables por contenedor",
    ),
    ReporteTipo.DAILY_SUMMARY: (
        "Resumen Diario",
        "Resumen operativo diario de entradas, salidas, saldo al cierre y ocupación",
    ),
}


def _formatear_fecha(dt: datetime.datetime | None) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    dt_app = dt.astimezone(zona_horaria_app())
    return dt_app.strftime("%d/%m/%Y %H:%M:%S")


def _fecha_ultimo_ingreso():
    return (
        select(func.max(Movimiento.ts))
        .where(
            Movimiento.contenedor_id == Contenedor.id,
            Movimiento.tipo == TipoMovimiento.INGRESO,
        )
        .correlate(Contenedor)
        .scalar_subquery()
    )


async def obtener_datos_contenedores_en_patio(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> ReportResultList:
    estados_activos = [
        EstadoContenedor.INGRESADO,
        EstadoContenedor.UBICADO,
        EstadoContenedor.EN_ESTADIA,
        EstadoContenedor.EN_SERVICIO_ESPECIAL,
    ]

    fecha_entrada = _fecha_ultimo_ingreso()

    stmt = (
        select(Contenedor, Cliente, Patio, v_estancias_table.c.ingresado_en, v_estancias_table.c.dias_estancia, fecha_entrada)
        .outerjoin(v_estancias_table, Contenedor.id == v_estancias_table.c.contenedor_id)
        .outerjoin(Cliente, Contenedor.cliente_id == Cliente.id)
        .outerjoin(Patio, Contenedor.patio_id == Patio.id)
        .where(Contenedor.estado.in_(estados_activos))
    )

    if patios_ids:
        stmt = stmt.where(Contenedor.patio_id.in_(patios_ids))
    if filtros.patio_id:
        stmt = stmt.where(Contenedor.patio_id == filtros.patio_id)
    if filtros.cliente_id and not isinstance(filtros.cliente_id, int):
        stmt = stmt.where(Contenedor.cliente_id == filtros.cliente_id)
    if filtros.fecha_inicio:
        inicio_dt = datetime.datetime.combine(filtros.fecha_inicio, datetime.time.min, tzinfo=zona_horaria_app())
        stmt = stmt.where(v_estancias_table.c.ingresado_en >= inicio_dt)
    if filtros.fecha_fin:
        fin_dt = datetime.datetime.combine(filtros.fecha_fin, datetime.time.max, tzinfo=zona_horaria_app())
        stmt = stmt.where(v_estancias_table.c.ingresado_en <= fin_dt)
    if filtros.busqueda:
        term = f"%{filtros.busqueda.strip()}%"
        stmt = stmt.where(Contenedor.numero_contenedor.ilike(term))

    res_all = await db.execute(stmt.order_by(Contenedor.created_at.desc()))
    items_all = res_all.all()
    total = len(items_all)

    ahora = datetime.datetime.now(zona_horaria_app())
    llenos = 0
    vacios = 0
    dias_totales = 0

    for c, cli, p, ing_en, dias_v, entrada in items_all:
        if c.tipo == TipoContenedor.LLENO:
            llenos += 1
        else:
            vacios += 1
        dias = dias_v if dias_v is not None else (max(0, (ahora - entrada).days) + 1 if entrada else 0)
        dias_totales += dias

    estadia_promedio = (dias_totales / total) if total > 0 else 0.0

    offset = (filtros.page - 1) * filtros.page_size
    items_pag = items_all[offset : offset + filtros.page_size]

    filas = []
    for c, cli, p, ing_en, dias_v, entrada in items_pag:
        dias = dias_v if dias_v is not None else (max(0, (ahora - entrada).days) + 1 if entrada else 0)
        tipo_str = "Lleno" if c.tipo == TipoContenedor.LLENO else "Vacío"
        tamano_val = c.tamano.value if hasattr(c.tamano, "value") else str(c.tamano)
        filas.append(
            {
                "contenedor": c.numero_contenedor,
                "cliente": cli.razon_social if cli else "Sin cliente",
                "tipo": tipo_str,
                "tamano": f"CONTENEDOR ESTANDAR {tamano_val}\"",
                "estadia": dias,
                "fecha_entrada": _formatear_fecha(ing_en or entrada),
                "sellos": mostrar_sellos(c.sellos),
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

    return ReportResultList(filas, total, kpis)


async def obtener_datos_movimientos_entrada(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> ReportResultList:
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
    if filtros.cliente_id and not isinstance(filtros.cliente_id, int):
        stmt = stmt.where(Contenedor.cliente_id == filtros.cliente_id)
    if filtros.fecha_inicio:
        inicio_dt = datetime.datetime.combine(filtros.fecha_inicio, datetime.time.min, tzinfo=zona_horaria_app())
        stmt = stmt.where(Movimiento.ts >= inicio_dt)
    if filtros.fecha_fin:
        fin_dt = datetime.datetime.combine(filtros.fecha_fin, datetime.time.max, tzinfo=zona_horaria_app())
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

    return ReportResultList(filas, total, kpis)


async def obtener_datos_movimientos_salida(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> ReportResultList:
    ingreso = aliased(Movimiento)
    ingreso_previo = (
        select(func.max(ingreso.ts))
        .where(
            ingreso.contenedor_id == Movimiento.contenedor_id,
            ingreso.tipo == TipoMovimiento.INGRESO,
            ingreso.ts <= Movimiento.ts,
        )
        .correlate(Movimiento)
        .scalar_subquery()
    )

    stmt = (
        select(Movimiento, Contenedor, Cliente, Patio, Usuario, ingreso_previo)
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
    if filtros.cliente_id and not isinstance(filtros.cliente_id, int):
        stmt = stmt.where(Contenedor.cliente_id == filtros.cliente_id)
    if filtros.fecha_inicio:
        inicio_dt = datetime.datetime.combine(filtros.fecha_inicio, datetime.time.min, tzinfo=zona_horaria_app())
        stmt = stmt.where(Movimiento.ts >= inicio_dt)
    if filtros.fecha_fin:
        fin_dt = datetime.datetime.combine(filtros.fecha_fin, datetime.time.max, tzinfo=zona_horaria_app())
        stmt = stmt.where(Movimiento.ts <= fin_dt)
    if filtros.busqueda:
        term = f"%{filtros.busqueda.strip()}%"
        stmt = stmt.where(Contenedor.numero_contenedor.ilike(term))

    res_all = await db.execute(stmt.order_by(Movimiento.ts.desc()))
    items_all = res_all.all()
    total = len(items_all)

    llenos = sum(1 for m, c, cli, p, u, entrada in items_all if c.tipo == TipoContenedor.LLENO)
    vacios = total - llenos

    offset = (filtros.page - 1) * filtros.page_size
    items_pag = items_all[offset : offset + filtros.page_size]

    filas = []
    for idx, (m, c, cli, p, u, entrada) in enumerate(items_pag, start=offset + 1):
        condicion_str = "Lleno" if c.tipo == TipoContenedor.LLENO else "Vacío"
        mes_ano = m.ts.strftime("%b%y").upper() if m.ts else "26"
        numero_viaje = f"SAL{str(m.id)[:6].upper()}-{mes_ano}"
        filas.append(
            {
                "folio": idx,
                "numero_viaje": numero_viaje,
                "fecha_entrada": _formatear_fecha(entrada),
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

    return ReportResultList(filas, total, kpis)


async def obtener_datos_posiciones(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> ReportResultList:
    estados_activos = [
        EstadoContenedor.INGRESADO,
        EstadoContenedor.UBICADO,
        EstadoContenedor.EN_ESTADIA,
        EstadoContenedor.EN_SERVICIO_ESPECIAL,
    ]

    fecha_entrada = _fecha_ultimo_ingreso()

    stmt = (
        select(Contenedor, Ubicacion, Tira, Tramo, Carril, fecha_entrada)
        .join(Ubicacion, Contenedor.ubicacion_id == Ubicacion.id)
        .join(Tira, Ubicacion.tira_id == Tira.id)
        .join(Tramo, Tira.tramo_id == Tramo.id)
        .join(Carril, Tramo.carril_id == Carril.id)
        .where(Contenedor.ubicacion_id.isnot(None))
        .where(Contenedor.estado.in_(estados_activos))
    )

    if patios_ids:
        stmt = stmt.where(Contenedor.patio_id.in_(patios_ids))
    if filtros.patio_id:
        stmt = stmt.where(Contenedor.patio_id == filtros.patio_id)
    if filtros.cliente_id and not isinstance(filtros.cliente_id, int):
        stmt = stmt.where(Contenedor.cliente_id == filtros.cliente_id)
    if filtros.fecha_inicio:
        inicio_dt = datetime.datetime.combine(filtros.fecha_inicio, datetime.time.min, tzinfo=zona_horaria_app())
        stmt = stmt.where(fecha_entrada >= inicio_dt)
    if filtros.fecha_fin:
        fin_dt = datetime.datetime.combine(filtros.fecha_fin, datetime.time.max, tzinfo=zona_horaria_app())
        stmt = stmt.where(fecha_entrada <= fin_dt)
    if filtros.busqueda:
        term = f"%{filtros.busqueda.strip()}%"
        stmt = stmt.where(Contenedor.numero_contenedor.ilike(term))

    res_all = await db.execute(stmt.order_by(Carril.orden, Tramo.orden, Tira.orden, Ubicacion.nivel))
    items_all = res_all.all()
    total = len(items_all)

    nivel_1 = sum(1 for c, ub, ti, tr, ca, entrada in items_all if ub.nivel == 1)
    nivel_superior = total - nivel_1

    offset = (filtros.page - 1) * filtros.page_size
    items_pag = items_all[offset : offset + filtros.page_size]

    filas = []
    for c, ub, ti, tr, ca, entrada in items_pag:
        filas.append(
            {
                "contenedor": c.numero_contenedor,
                "posicion": ub.codigo,
                "carril": ca.codigo,
                "tramo": tr.codigo,
                "tira": ti.codigo,
                "altura": str(ub.nivel),
                "fecha": _formatear_fecha(entrada),
            }
        )

    kpis = [
        ReporteKpi(label="Total Ocupadas", value=str(total), tone="info"),
        ReporteKpi(label="Nivel 1 (Piso)", value=str(nivel_1), tone="success"),
        ReporteKpi(label="Nivel > 1 (Estiba)", value=str(nivel_superior), tone="warning"),
    ]

    return ReportResultList(filas, total, kpis)


async def obtener_datos_servicios_especiales(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> ReportResultList:
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
    if filtros.cliente_id and not isinstance(filtros.cliente_id, int):
        stmt = stmt.where(Contenedor.cliente_id == filtros.cliente_id)
    if filtros.fecha_inicio:
        inicio_dt = datetime.datetime.combine(filtros.fecha_inicio, datetime.time.min, tzinfo=zona_horaria_app())
        stmt = stmt.where(Movimiento.ts >= inicio_dt)
    if filtros.fecha_fin:
        fin_dt = datetime.datetime.combine(filtros.fecha_fin, datetime.time.max, tzinfo=zona_horaria_app())
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

    return ReportResultList(filas, total, kpis)


async def obtener_datos_inventario_a_fecha(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> ReportResultList:
    target_fecha = filtros.fecha or datetime.datetime.now(zona_horaria_app()).date()

    stmt = (
        select(InventarioDiario, Contenedor, Cliente, Ubicacion)
        .join(Contenedor, InventarioDiario.contenedor_id == Contenedor.id)
        .outerjoin(Cliente, InventarioDiario.cliente_id == Cliente.id)
        .outerjoin(Ubicacion, InventarioDiario.ubicacion_id == Ubicacion.id)
        .where(InventarioDiario.fecha == target_fecha)
    )

    if patios_ids:
        stmt = stmt.where(InventarioDiario.patio_id.in_(patios_ids))
    if filtros.patio_id:
        stmt = stmt.where(InventarioDiario.patio_id == filtros.patio_id)
    if filtros.cliente_id and not isinstance(filtros.cliente_id, int):
        stmt = stmt.where(InventarioDiario.cliente_id == filtros.cliente_id)
    if filtros.busqueda:
        term = f"%{filtros.busqueda.strip()}%"
        stmt = stmt.where(Contenedor.numero_contenedor.ilike(term))

    res_all = await db.execute(stmt.order_by(Contenedor.numero_contenedor))
    items_all = res_all.all()

    if not items_all and target_fecha == datetime.datetime.now(zona_horaria_app()).date():
        estados_activos = [
            EstadoContenedor.INGRESADO,
            EstadoContenedor.UBICADO,
            EstadoContenedor.EN_ESTADIA,
            EstadoContenedor.EN_SERVICIO_ESPECIAL,
        ]
        stmt_fallback = (
            select(Contenedor, Cliente, Ubicacion, v_estancias_table.c.dias_estancia)
            .join(v_estancias_table, Contenedor.id == v_estancias_table.c.contenedor_id)
            .outerjoin(Cliente, Contenedor.cliente_id == Cliente.id)
            .outerjoin(Ubicacion, Contenedor.ubicacion_id == Ubicacion.id)
            .where(Contenedor.estado.in_(estados_activos))
        )
        if patios_ids:
            stmt_fallback = stmt_fallback.where(Contenedor.patio_id.in_(patios_ids))
        if filtros.patio_id:
            stmt_fallback = stmt_fallback.where(Contenedor.patio_id == filtros.patio_id)
        if filtros.cliente_id and not isinstance(filtros.cliente_id, int):
            stmt_fallback = stmt_fallback.where(Contenedor.cliente_id == filtros.cliente_id)
        if filtros.busqueda:
            term = f"%{filtros.busqueda.strip()}%"
            stmt_fallback = stmt_fallback.where(Contenedor.numero_contenedor.ilike(term))

        res_fb = await db.execute(stmt_fallback)
        items_fb = res_fb.all()
        total = len(items_fb)
        offset = (filtros.page - 1) * filtros.page_size
        items_pag = items_fb[offset : offset + filtros.page_size]

        filas = []
        for c, cli, ub, dias in items_pag:
            filas.append(
                {
                    "contenedor": c.numero_contenedor,
                    "cliente": cli.razon_social if cli else "Sin cliente",
                    "ubicacion": ub.codigo if ub else "Sin ubicación",
                    "estado": c.estado.value if hasattr(c.estado, "value") else str(c.estado),
                    "dias_estancia": dias or 1,
                }
            )
        kpis = [
            ReporteKpi(label="Total Contenedores", value=str(total), tone="info"),
        ]
        return ReportResultList(filas, total, kpis)

    total = len(items_all)
    offset = (filtros.page - 1) * filtros.page_size
    items_pag = items_all[offset : offset + filtros.page_size]

    filas = []
    for inv, c, cli, ub in items_pag:
        filas.append(
            {
                "contenedor": c.numero_contenedor if c else "",
                "cliente": cli.razon_social if cli else "Sin cliente",
                "ubicacion": ub.codigo if ub else "Sin ubicación",
                "estado": inv.estado,
                "dias_estancia": inv.dias_estancia,
            }
        )

    kpis = [
        ReporteKpi(label="Total Contenedores", value=str(total), tone="info"),
    ]

    return ReportResultList(filas, total, kpis)


async def obtener_datos_estancia_por_cliente(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> ReportResultList:
    stmt = (
        select(v_estancias_table, Contenedor, Cliente, Patio)
        .join(Contenedor, v_estancias_table.c.contenedor_id == Contenedor.id)
        .outerjoin(Cliente, v_estancias_table.c.cliente_id == Cliente.id)
        .outerjoin(Patio, v_estancias_table.c.patio_id == Patio.id)
    )

    if patios_ids:
        stmt = stmt.where(v_estancias_table.c.patio_id.in_(patios_ids))
    if filtros.patio_id:
        stmt = stmt.where(v_estancias_table.c.patio_id == filtros.patio_id)
    if filtros.cliente_id and not isinstance(filtros.cliente_id, int):
        stmt = stmt.where(v_estancias_table.c.cliente_id == filtros.cliente_id)
    if filtros.fecha_inicio:
        inicio_dt = datetime.datetime.combine(filtros.fecha_inicio, datetime.time.min, tzinfo=zona_horaria_app())
        stmt = stmt.where(v_estancias_table.c.ingresado_en >= inicio_dt)
    if filtros.fecha_fin:
        fin_dt = datetime.datetime.combine(filtros.fecha_fin, datetime.time.max, tzinfo=zona_horaria_app())
        stmt = stmt.where(v_estancias_table.c.ingresado_en <= fin_dt)
    if filtros.busqueda:
        term = f"%{filtros.busqueda.strip()}%"
        stmt = stmt.where(Contenedor.numero_contenedor.ilike(term))

    res_all = await db.execute(stmt.order_by(v_estancias_table.c.ingresado_en.desc()))
    items_all = res_all.all()
    total = len(items_all)

    dias_totales = sum(row.dias_estancia for row, c, cli, p in items_all)
    dias_cobrables_totales = sum(row.dias_cobrables for row, c, cli, p in items_all)
    promedio_estadia = (dias_totales / total) if total > 0 else 0.0

    offset = (filtros.page - 1) * filtros.page_size
    items_pag = items_all[offset : offset + filtros.page_size]

    filas = []
    for row, c, cli, p in items_pag:
        serv_res = await db.execute(
            select(Movimiento.motivo_override)
            .where(Movimiento.contenedor_id == c.id, Movimiento.tipo == TipoMovimiento.SERVICIO)
        )
        servicios_list = [m[0] for m in serv_res.all() if m[0]]
        servicios_str = ", ".join(servicios_list) if servicios_list else "Ninguno"

        filas.append(
            {
                "contenedor": c.numero_contenedor,
                "cliente": cli.razon_social if cli else "Sin cliente",
                "fecha_ingreso": _formatear_fecha(row.ingresado_en),
                "fecha_salida": _formatear_fecha(row.fecha_salida) if row.fecha_salida else "En patio",
                "dias": row.dias_estancia,
                "dias_libres": row.dias_libres,
                "dias_cobrables": row.dias_cobrables,
                "servicios": servicios_str,
            }
        )

    kpis = [
        ReporteKpi(label="Total Contenedores", value=str(total), tone="info"),
        ReporteKpi(label="Días Totales", value=str(dias_totales), tone="info"),
        ReporteKpi(label="Días Cobrables", value=str(dias_cobrables_totales), tone="warning"),
        ReporteKpi(label="Estadía Promedio", value=f"{promedio_estadia:.1f} días", tone="success"),
    ]

    return ReportResultList(filas, total, kpis)


async def obtener_datos_resumen_diario(
    db: AsyncSession,
    filtros: FiltrosReporte,
    patios_ids: list[uuid.UUID] | None = None,
) -> ReportResultList:
    stmt = (
        select(
            InventarioDiario.fecha,
            func.count(InventarioDiario.contenedor_id).label("saldo_cierre"),
        )
        .group_by(InventarioDiario.fecha)
        .order_by(InventarioDiario.fecha.desc())
    )

    if patios_ids:
        stmt = stmt.where(InventarioDiario.patio_id.in_(patios_ids))
    if filtros.patio_id:
        stmt = stmt.where(InventarioDiario.patio_id == filtros.patio_id)
    if filtros.fecha_inicio:
        stmt = stmt.where(InventarioDiario.fecha >= filtros.fecha_inicio)
    if filtros.fecha_fin:
        stmt = stmt.where(InventarioDiario.fecha <= filtros.fecha_fin)

    res_all = await db.execute(stmt)
    items_all = res_all.all()
    total = len(items_all)

    offset = (filtros.page - 1) * filtros.page_size
    items_pag = items_all[offset : offset + filtros.page_size]

    filas = []
    for fecha_val, saldo_cierre in items_pag:
        inicio_dt = datetime.datetime.combine(fecha_val, datetime.time.min, tzinfo=zona_horaria_app())
        fin_dt = datetime.datetime.combine(fecha_val, datetime.time.max, tzinfo=zona_horaria_app())

        entradas_res = await db.execute(
            select(func.count(Movimiento.id)).where(
                Movimiento.tipo == TipoMovimiento.INGRESO,
                Movimiento.ts >= inicio_dt,
                Movimiento.ts <= fin_dt,
            )
        )
        entradas = entradas_res.scalar() or 0

        salidas_res = await db.execute(
            select(func.count(Movimiento.id)).where(
                Movimiento.tipo == TipoMovimiento.SALIDA,
                Movimiento.ts >= inicio_dt,
                Movimiento.ts <= fin_dt,
            )
        )
        salidas = salidas_res.scalar() or 0

        ubicaciones_res = await db.execute(select(func.count(Ubicacion.id)).where(Ubicacion.activo == True))
        total_ubicaciones = ubicaciones_res.scalar() or 1
        ocupacion_pct = (saldo_cierre / total_ubicaciones) * 100

        filas.append(
            {
                "fecha": fecha_val.strftime("%d/%m/%Y") if hasattr(fecha_val, "strftime") else str(fecha_val),
                "entradas": entradas,
                "salidas": salidas,
                "saldo_cierre": saldo_cierre,
                "ocupacion": f"{ocupacion_pct:.1f}%",
            }
        )

    kpis = [
        ReporteKpi(label="Total Días", value=str(total), tone="info"),
    ]

    return ReportResultList(filas, total, kpis)


async def obtener_datos_reporte(
    db: AsyncSession,
    tipo: ReporteTipo | str,
    filtros: FiltrosReporte | None = None,
    patios_ids: list[uuid.UUID] | None = None,
    cliente_id: uuid.UUID | int | None = None,
) -> ReportResultList:
    if isinstance(tipo, str):
        try:
            tipo = ReporteTipo(tipo)
        except ValueError:
            raise ValueError(f"Tipo de reporte desconocido: {tipo}")

    if filtros is None:
        filtros = FiltrosReporte()
    if cliente_id is not None and filtros.cliente_id is None:
        filtros.cliente_id = cliente_id  # type: ignore

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
    elif type_matches := tipo == ReporteTipo.INVENTORY_AT_DATE:
        return await obtener_datos_inventario_a_fecha(db, filtros, patios_ids)
    elif tipo == ReporteTipo.STAY_BY_CLIENT:
        return await obtener_datos_estancia_por_cliente(db, filtros, patios_ids)
    elif tipo == ReporteTipo.DAILY_SUMMARY:
        return await obtener_datos_resumen_diario(db, filtros, patios_ids)
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
