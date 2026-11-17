import uuid
from pydantic import BaseModel, Field

from app.models.enums import TipoMovimiento


class SalidaDespacharCreate(BaseModel):
    pin_salida: str = Field(min_length=4, max_length=10)


class SalidaDespacharResponse(BaseModel):
    contenedor: "ContenedorOut"

    class Config:
        from_attributes = True


class SalidaListoCreate(BaseModel):
    pass  # No additional fields needed for marking as ready at gate


class SalidaListoResponse(BaseModel):
    contenedor: "ContenedorOut"

    class Config:
        from_attributes = True


# Forward reference for ContenedorOut
from app.schemas.contenedor import ContenedorOut
SalidaDespacharResponse.model_rebuild()
SalidaListoResponse.model_rebuild()