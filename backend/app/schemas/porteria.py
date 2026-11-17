import uuid
from pydantic import BaseModel, Field
from app.schemas.contenedor import ContenedorOut
from app.schemas.ubicacion import SugerenciaUbicacionResponse


class PorteriaIngresoCreate(BaseModel):
    pin: str
    placas: str | None = None
    operador: str | None = None
    sellos: str | None = None
    danos: dict | None = None
    notas: str | None = None
    evidencias: list[str] = Field(min_length=1)


class PorteriaIngresoResponse(BaseModel):
    contenedor: ContenedorOut
    sugerencias: list[SugerenciaUbicacionResponse]
