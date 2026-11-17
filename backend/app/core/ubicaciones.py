import re
from dataclasses import dataclass


@dataclass
class EtiquetaUbicacion:
    corta: str
    larga: str

    def __str__(self) -> str:
        return self.corta


def etiqueta_ubicacion(ubicacion) -> EtiquetaUbicacion:
    """Devuelve la etiqueta legible de una ubicación en formato corto y largo."""
    codigo = getattr(ubicacion, "codigo", None)
    nivel = getattr(ubicacion, "nivel", 1)

    carril_codigo = None
    tramo_codigo = None
    tira_codigo = None

    try:
        if hasattr(ubicacion, "tira") and ubicacion.tira:
            tira_codigo = ubicacion.tira.codigo
            if hasattr(ubicacion.tira, "tramo") and ubicacion.tira.tramo:
                tramo_codigo = ubicacion.tira.tramo.codigo
                if hasattr(ubicacion.tira.tramo, "carril") and ubicacion.tira.tramo.carril:
                    carril_codigo = ubicacion.tira.tramo.carril.codigo
    except Exception:
        pass

    if not carril_codigo or not tramo_codigo or not tira_codigo:
        if codigo:
            match = re.match(r"^(?P<carril>[\w-]+)-(?P<tramo>[\w-]+)-(?P<tira>[\w-]+)-N(?P<nivel>\d+)$", codigo)
            if match:
                d = match.groupdict()
                carril_codigo = d.get("carril")
                tramo_codigo = d.get("tramo")
                tira_codigo = d.get("tira")
                nivel = int(d.get("nivel", nivel))

    if not codigo and carril_codigo and tramo_codigo and tira_codigo:
        codigo = f"{carril_codigo}-{tramo_codigo}-{tira_codigo}-N{nivel}"

    corta = codigo or f"N{nivel}"
    carril_str = carril_codigo or "A01"
    tramo_str = tramo_codigo or "T01"
    tira_str = tira_codigo or "R01"

    larga = f"Carril {carril_str} · Tramo {tramo_str} · Tira {tira_str} · Nivel {nivel}"

    return EtiquetaUbicacion(corta=corta, larga=larga)
