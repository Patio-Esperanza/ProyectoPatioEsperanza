import datetime
import enum
from typing import Any, Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ReporteTipo(str, enum.Enum):
    CONTAINERS_IN_YARD = "containers-in-yard"
    ENTRY_MOVEMENTS = "entry-movements"
    DEPARTURE_MOVEMENTS = "departure-movements"
    POSITIONS = "positions"
    SPECIAL_SERVICES = "special-services"


class FrecuenciaReporte(str, enum.Enum):
    DIARIO = "diario"
    SEMANAL = "semanal"
    MENSUAL = "mensual"


class FiltrosReporte(BaseModel):
    fecha_inicio: datetime.date | None = None
    fecha_fin: datetime.date | None = None
    patio_id: uuid.UUID | None = None
    cliente_id: uuid.UUID | None = None
    busqueda: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=500)


class ReporteColumna(BaseModel):
    key: str
    label: str
    align: Literal["left", "center", "right"] = "left"


class ReporteKpi(BaseModel):
    label: str
    value: str
    subtext: str | None = None
    tone: Literal["info", "success", "warning", "danger"] = "info"


class ReportePreviewOut(BaseModel):
    tipo: ReporteTipo
    titulo: str
    subtitulo: str
    total_registros: int
    columnas: list[ReporteColumna]
    filas: list[dict[str, Any]]
    kpis: list[ReporteKpi]
    page: int = 1
    page_size: int = 25
    total_paginas: int = 1


class ReporteProgramadoCreate(BaseModel):
    nombre: str = Field(..., max_length=150)
    tipo_reporte: ReporteTipo
    patio_id: uuid.UUID | None = None
    cliente_id: uuid.UUID | None = None
    frecuencia: FrecuenciaReporte
    hora: int = Field(..., ge=0, le=23)
    minuto: int = Field(..., ge=0, le=59)
    dia_semana: int | None = Field(default=None, ge=0, le=6)
    dia_mes: int | None = Field(default=None, ge=1, le=31)
    destinatarios: list[str] = Field(..., min_length=1)
    asunto: str = Field(..., max_length=255)
    mensaje: str | None = None
    activo: bool = True


class ReporteProgramadoUpdate(BaseModel):
    nombre: str | None = Field(default=None, max_length=150)
    patio_id: uuid.UUID | None = None
    cliente_id: uuid.UUID | None = None
    frecuencia: FrecuenciaReporte | None = None
    hora: int | None = Field(default=None, ge=0, le=23)
    minuto: int | None = Field(default=None, ge=0, le=59)
    dia_semana: int | None = Field(default=None, ge=0, le=6)
    dia_mes: int | None = Field(default=None, ge=1, le=31)
    destinatarios: list[str] | None = None
    asunto: str | None = Field(default=None, max_length=255)
    mensaje: str | None = None
    activo: bool | None = None


class ReporteProgramadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    tipo_reporte: ReporteTipo
    patio_id: uuid.UUID | None
    cliente_id: uuid.UUID | None
    frecuencia: FrecuenciaReporte
    hora: int
    minuto: int
    dia_semana: int | None
    dia_mes: int | None
    destinatarios: list[str]
    asunto: str
    mensaje: str | None
    activo: bool
    ultimo_envio: datetime.datetime | None
    ultimo_estado: str | None
    ultimo_error: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
