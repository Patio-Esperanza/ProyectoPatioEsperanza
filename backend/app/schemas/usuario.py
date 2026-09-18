import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RolUsuario
from app.schemas.patio import PatioOut


class UsuarioCreate(BaseModel):
    nombre: str
    email: str
    password: str = Field(min_length=8)
    tipo: RolUsuario
    patio_ids: list[uuid.UUID] = []


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str | None
    email: str
    tipo: RolUsuario
    activo: bool
    patios: list[PatioOut] = []
