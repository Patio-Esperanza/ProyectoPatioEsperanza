import uuid

from pydantic import BaseModel, ConfigDict


class PatioCreate(BaseModel):
    nombre: str
    codigo: str


class PatioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    codigo: str
    activo: bool
