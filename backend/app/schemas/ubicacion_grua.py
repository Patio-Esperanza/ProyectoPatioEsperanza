import uuid
from pydantic import BaseModel, Field

from app.models.enums import TipoMovimiento


class UbicacionUbicarCreate(BaseModel):
    ubicacion_id: uuid.UUID
    tipo_movimiento: TipoMovimiento = TipoMovimiento.REUBICACION
    override_manual: bool = False
    motivo_override: str | None = None
    score_sugerido: float | None = None
    score_elegido: float | None = None


class UbicacionUbicarResponse(BaseModel):
    contenedor: "ContenedorOut"

    class Config:
        from_attributes = True


from app.schemas.contenedor import ContenedorOut
UbicacionUbicarResponse.model_rebuild()
