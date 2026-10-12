"""Normalización y presentación del sello de un contenedor.

El sello es un dato que el cliente captura a mano, así que llega con espacios
sobrantes y a veces con la propia leyenda que usamos para decir que no hay
sello. Todo eso se limpia aquí para que la base guarde una sola forma: el
código del sello, o `NULL` cuando no hay.

La leyenda nunca se guarda. Si se guardara, dejaría de ser posible distinguir
un contenedor sin sello de uno cuyo sello se llama literalmente "S/N", y las
consultas de "contenedores sin sello" dejarían de funcionar.
"""

LEYENDA_SIN_SELLO = "S/N"

# Formas con las que un capturista escribe "no tiene sello". Se guardan como
# ausencia de sello, no como texto.
_EQUIVALENTES_A_VACIO = {"S/N", "SN", "S / N", "N/A", "NA", "SIN SELLO"}


def normalizar_sellos(valor: str | None) -> str | None:
    """Devuelve el sello limpio, o `None` cuando no hay sello."""
    if valor is None:
        return None
    limpio = " ".join(valor.split())
    if not limpio or limpio.upper() in _EQUIVALENTES_A_VACIO:
        return None
    return limpio


def mostrar_sellos(valor: str | None) -> str:
    """Texto que se muestra al usuario: el sello, o la leyenda si no hay."""
    return valor if valor else LEYENDA_SIN_SELLO
