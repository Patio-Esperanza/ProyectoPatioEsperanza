import uuid

from pydantic import BaseModel, ConfigDict, Field


class PatioCreate(BaseModel):
    nombre: str
    codigo: str
    anticipacion_minima_horas: int = Field(default=24, gt=0)


class PatioUpdate(BaseModel):
    anticipacion_minima_horas: int = Field(gt=0)


class PatioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    codigo: str
    activo: bool
    anticipacion_minima_horas: int
    ubicacion_entrada_id: uuid.UUID | None = None


class LayoutPatioCreate(BaseModel):
    carriles: int = Field(gt=0)
    tramos: int = Field(gt=0)
    tiras: int = Field(gt=0)
    niveles: int = Field(ge=1, le=5)


class LayoutPatioOut(BaseModel):
    carriles_creados: int
    carriles_saltados: int
    ubicaciones_creadas: int
