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


class TamanoContenedor(str, enum.Enum):
    VEINTE = "20"
    CUARENTA = "40"
    CUARENTA_Y_CINCO = "45"


class EstadoContenedor(str, enum.Enum):
    SOLICITUD_INGRESO = "solicitud_ingreso"
    QR_INGRESO_EMITIDO = "qr_ingreso_emitido"
    EN_PORTERIA = "en_porteria"
    INGRESADO = "ingresado"
    UBICADO = "ubicado"
    EN_ESTADIA = "en_estadia"
    EN_SERVICIO_ESPECIAL = "en_servicio_especial"
    SOLICITUD_SALIDA = "solicitud_salida"
    QR_SALIDA_EMITIDO = "qr_salida_emitido"
    EN_PORTERIA_SALIDA = "en_porteria_salida"
    DESPACHADO = "despachado"
    RECHAZADO = "rechazado"


class TipoMovimiento(str, enum.Enum):
    INGRESO = "ingreso"
    REUBICACION = "reubicacion"
    SERVICIO = "servicio"
    SALIDA = "salida"
