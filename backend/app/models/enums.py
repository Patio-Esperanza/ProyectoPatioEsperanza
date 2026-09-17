import enum


class TipoContenedor(str, enum.Enum):
    LLENO = "lleno"
    VACIO = "vacio"


class RolUsuario(str, enum.Enum):
    CLIENTE = "cliente"
    OPERADOR = "operador"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"
    GUARDIA = "guardia"
    DESPACHADOR = "despachador"


class TipoCliente(str, enum.Enum):
    AGENCIA_ADUANAL = "agencia_aduanal"
    IMPORTADOR_EXPORTADOR = "importador_exportador"
    TRANSPORTISTA = "transportista"
    SOCIO_API = "socio_api"
