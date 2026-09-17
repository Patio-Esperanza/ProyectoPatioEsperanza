"""Importa todos los modelos para que Base.metadata los conozca (usado por Alembic)."""

from app.models.auditoria import Auditoria  # noqa: F401
from app.models.cliente import Cliente  # noqa: F401
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion  # noqa: F401
from app.models.usuario import Usuario, UsuarioPatio  # noqa: F401
