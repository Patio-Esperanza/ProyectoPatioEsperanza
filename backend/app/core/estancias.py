import zoneinfo
from datetime import datetime


def calcular_dias_estancia(
    ingreso: datetime, salida: datetime | None, zona_horaria: str = "America/Mexico_City"
) -> int:
    """Calcula los días de estancia de un contenedor.

    Regla:
    - Se cuentan días calendario en zona horaria local.
    - El día de ingreso cuenta como día 1.
    - Si ya salió, la fecha fin es la fecha local de salida; si sigue en patio,
      se usa el momento actual en zona local.
    - dias_estancia = fecha_fin - fecha_inicio + 1, con un mínimo de 1.
    """
    tz = zoneinfo.ZoneInfo(zona_horaria)
    ingreso_local = ingreso.astimezone(tz)
    fecha_inicio = ingreso_local.date()

    if salida is not None:
        salida_local = salida.astimezone(tz)
        fecha_fin = salida_local.date()
    else:
        fecha_fin = datetime.now(tz).date()

    delta = (fecha_fin - fecha_inicio).days
    return max(1, delta + 1)
