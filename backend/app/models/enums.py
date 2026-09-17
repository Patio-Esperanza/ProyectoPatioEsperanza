import enum


class TipoContenedor(str, enum.Enum):
    LLENO = "lleno"
    VACIO = "vacio"
