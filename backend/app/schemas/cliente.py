import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TipoCliente


class ClienteCreate(BaseModel):
    razon_social: str
    rfc: str
    tipo: TipoCliente


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    razon_social: str
    rfc: str
    tipo: TipoCliente
    activo: bool


class ClienteRegistro(BaseModel):
    nombre: str
    email: str
    password: str = Field(min_length=8)
    rfc: str


class ClienteVerificar(BaseModel):
    email: str
    codigo: str
