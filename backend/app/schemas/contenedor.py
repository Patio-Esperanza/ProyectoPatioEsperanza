import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.iso6346 import validar_iso6346
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoContenedor


class ContenedorCreate(BaseModel):
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    patio_id: uuid.UUID
    peso_kg: int

    @field_validator("numero_contenedor")
    @classmethod
    def numero_valido(cls, value: str) -> str:
        value = value.strip().upper()
        if not validar_iso6346(value):
            raise ValueError("numero_contenedor no cumple el checksum ISO 6346")
        return value


class ContenedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    patio_id: uuid.UUID
    estado: EstadoContenedor
    peso_kg: int
