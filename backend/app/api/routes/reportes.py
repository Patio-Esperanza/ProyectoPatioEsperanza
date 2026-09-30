import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.db import get_db
from app.models.enums import RolUsuario
from app.models.reporte_programado import ReporteProgramado
from app.schemas.reportes import (
    FiltrosReporte,
    ReporteProgramadoCreate,
    ReporteProgramadoOut,
    ReporteProgramadoUpdate,
    ReportePreviewOut,
    ReporteTipo,
)
from app.services import reportes_scheduler
from app.services.reportes_datos import TITULOS_POR_REPORTE, obtener_preview_reporte
from app.services.reportes_excel import generar_excel_reporte

router = APIRouter()

_ROLES_STAFF = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.get("/{tipo}/preview", response_model=ReportePreviewOut)
async def preview_reporte(
    tipo: ReporteTipo,
    filtros: FiltrosReporte = Depends(),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_STAFF)),
) -> ReportePreviewOut:
    patios_ids = user.patios or None
    return await obtener_preview_reporte(db, tipo, filtros, patios_ids)


@router.get("/{tipo}/exportar")
async def exportar_reporte_excel(
    tipo: ReporteTipo,
    filtros: FiltrosReporte = Depends(),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_STAFF)),
) -> StreamingResponse:
    patios_ids = user.patios or None
    preview = await obtener_preview_reporte(db, tipo, filtros, patios_ids)
    titulo, subtitulo = TITULOS_POR_REPORTE.get(tipo, ("Reporte", ""))

    buffer = generar_excel_reporte(
        tipo=tipo,
        datos=preview.filas,
        total_registros=preview.total_registros,
        subtitulo=subtitulo,
    )
    nombre_archivo = f"{titulo.replace(' ', '_')}.xlsx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.get("/programados", response_model=list[ReporteProgramadoOut])
async def listar_reportes_programados(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_STAFF)),
) -> list[ReporteProgramado]:
    result = await db.execute(select(ReporteProgramado))
    return list(result.scalars().all())


@router.post(
    "/programados", response_model=ReporteProgramadoOut, status_code=status.HTTP_201_CREATED
)
async def crear_reporte_programado(
    payload: ReporteProgramadoCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_STAFF)),
) -> ReporteProgramado:
    prog = ReporteProgramado(**payload.model_dump())
    db.add(prog)
    await db.flush()
    await db.refresh(prog)

    reportes_scheduler.programar_job_reporte(prog)

    await db.commit()
    return prog


@router.get("/programados/{prog_id}", response_model=ReporteProgramadoOut)
async def obtener_reporte_programado(
    prog_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_STAFF)),
) -> ReporteProgramado:
    prog = await db.get(ReporteProgramado, prog_id)
    if prog is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reporte programado no encontrado")
    return prog


@router.patch("/programados/{prog_id}", response_model=ReporteProgramadoOut)
async def actualizar_reporte_programado(
    prog_id: uuid.UUID,
    payload: ReporteProgramadoUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_STAFF)),
) -> ReporteProgramado:
    prog = await db.get(ReporteProgramado, prog_id)
    if prog is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reporte programado no encontrado")

    datos = payload.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(prog, campo, valor)

    await db.flush()
    await db.refresh(prog)

    if prog.activo:
        reportes_scheduler.programar_job_reporte(prog)
    else:
        reportes_scheduler.remover_job_reporte(prog.id)

    await db.commit()
    return prog


@router.delete("/programados/{prog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_reporte_programado(
    prog_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_STAFF)),
) -> Response:
    prog = await db.get(ReporteProgramado, prog_id)
    if prog is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reporte programado no encontrado")

    reportes_scheduler.remover_job_reporte(prog.id)
    await db.delete(prog)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/programados/{prog_id}/ejecutar")
async def ejecutar_reporte_programado_manual(
    prog_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_STAFF)),
) -> dict[str, str]:
    prog = await db.get(ReporteProgramado, prog_id)
    if prog is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reporte programado no encontrado")

    await reportes_scheduler.ejecutar_envio_reporte_programado(prog_id, db)
    await db.commit()
    return {"detail": "Reporte enviado correctamente"}
