import uuid

from pydantic import BaseModel

from app.models.enums import EstadoContenedor, TamanoContenedor, TipoContenedor


class TiraMapaOut(BaseModel):
    id: uuid.UUID
    codigo: str
    orden: int
    niveles_totales: int
    niveles_activos: int
    niveles_ocupados: int


class TramoMapaOut(BaseModel):
    id: uuid.UUID
    codigo: str
    orden: int
    tiras: list[TiraMapaOut]


class CarrilMapaOut(BaseModel):
    id: uuid.UUID
    codigo: str
    orden: int
    tipo_teorico: TipoContenedor | None
    tramos: list[TramoMapaOut]


class ResumenMapaOut(BaseModel):
    ubicaciones_activas: int
    ocupadas: int


class MapaPatioOut(BaseModel):
    patio_id: uuid.UUID
    ubicacion_entrada_id: uuid.UUID | None
    resumen: ResumenMapaOut
    carriles: list[CarrilMapaOut]


class ContenedorEnNivelOut(BaseModel):
    id: uuid.UUID
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    peso_kg: int
    estado: EstadoContenedor


class NivelTiraOut(BaseModel):
    nivel: int
    ubicacion_id: uuid.UUID
    codigo: str
    activo: bool
    capacidad_peso_kg: int
    contenedor: ContenedorEnNivelOut | None


class DetalleTiraOut(BaseModel):
    tira_id: uuid.UUID
    codigo: str
    niveles: list[NivelTiraOut]
