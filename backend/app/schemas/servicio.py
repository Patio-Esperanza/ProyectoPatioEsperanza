import datetime
import uuid
from pydantic import BaseModel, Field
from app.models.servicio import EstadoServicio, UnidadRelacionadaTipo


class ServicioCatalogoOut(BaseModel):
    id: uuid.UUID
    patio_id: uuid.UUID | None = None
    codigo: str
    nombre: str
    descripcion: str | None = None
    requiere_evidencia: bool
    bloquea_salida: bool
    requiere_mover: bool
    requiere_unidad_relacionada: bool
    cliente_puede_solicitar: bool
    activo: bool

    class Config:
        from_attributes = True


class ServicioCatalogoCreate(BaseModel):
    patio_id: uuid.UUID | None = None
    codigo: str = Field(max_length=10)
    nombre: str = Field(max_length=100)
    descripcion: str | None = None
    requiere_evidencia: bool = False
    bloquea_salida: bool = False
    requiere_mover: bool = False
    requiere_unidad_relacionada: bool = False
    cliente_puede_solicitar: bool = False
    activo: bool = True


class ServicioCatalogoUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=100)
    descripcion: str | None = None
    requiere_evidencia: bool | None = None
    bloquea_salida: bool | None = None
    requiere_mover: bool | None = None
    requiere_unidad_relacionada: bool | None = None
    cliente_puede_solicitar: bool | None = None
    activo: bool | None = None


class ServicioContenedorCreate(BaseModel):
    servicio_catalogo_id: uuid.UUID
    cliente_id: uuid.UUID | None = None
    notas: str | None = None
    unidad_relacionada_tipo: UnidadRelacionadaTipo | None = None
    contenedor_relacionado_id: uuid.UUID | None = None
    unidad_relacionada_ref: str | None = Field(None, max_length=100)


class ServicioContenedorProgramar(BaseModel):
    programado_para: datetime.datetime
    asignado_a: uuid.UUID | None = None


class ServicioContenedorTerminar(BaseModel):
    notas: str | None = None
    evidencias: list[str] | None = None  # URLs of evidence photos


class ServicioContenedorMotivo(BaseModel):
    motivo: str = Field(min_length=1)


class EvidenciaOut(BaseModel):
    id: uuid.UUID
    url: str
    tipo: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class ServicioContenedorOut(BaseModel):
    id: uuid.UUID
    contenedor_id: uuid.UUID
    servicio_catalogo_id: uuid.UUID
    cliente_id: uuid.UUID | None = None
    estado: EstadoServicio
    solicitado_por: uuid.UUID
    asignado_a: uuid.UUID | None = None
    realizado_por: uuid.UUID | None = None
    programado_para: datetime.datetime | None = None
    solicitado_en: datetime.datetime
    iniciado_en: datetime.datetime | None = None
    terminado_en: datetime.datetime | None = None
    notas: str | None = None
    motivo: str | None = None
    unidad_relacionada_tipo: UnidadRelacionadaTipo | None = None
    contenedor_relacionado_id: uuid.UUID | None = None
    unidad_relacionada_ref: str | None = None
    catalogo: ServicioCatalogoOut | None = None
    evidencias: list[EvidenciaOut] = []

    class Config:
        from_attributes = True
