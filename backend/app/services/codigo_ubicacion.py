"""Normalización de los códigos de ubicación que teclea el operador.

`sembrar_layout_uniforme` guarda los códigos con los tres primeros segmentos a
dos dígitos y el nivel sin relleno: `A01-T01-R01-N1`. Quien captura un código a
mano escribe indistintamente `N1` o `N01`, con o sin ceros en el carril y en
minúsculas, así que comparar contra la base sin normalizar produce un 404 que
parece decir que la ubicación no existe.
"""

import re

FORMATO_CODIGO = "A01-T01-R01-N1"

_PATRON = re.compile(
    r"^A0*(?P<carril>\d+)-T0*(?P<tramo>\d+)-R0*(?P<tira>\d+)-N0*(?P<nivel>\d+)$"
)


def normalizar_codigo_ubicacion(codigo: str) -> str:
    """Devuelve el código tal como está guardado en la tabla `ubicaciones`.

    Acepta mayúsculas o minúsculas, espacios alrededor de los guiones y ceros a
    la izquierda de más o de menos en cualquier segmento.

    Lanza `ValueError` si el código no trae los cuatro segmentos o si algún
    número es cero, porque la numeración empieza en 1.
    """
    compacto = re.sub(r"\s+", "", codigo).upper()
    coincidencia = _PATRON.match(compacto)
    if coincidencia is None:
        raise ValueError(
            f"Código de ubicación inválido: usa el formato {FORMATO_CODIGO}"
        )

    partes = {nombre: int(valor) for nombre, valor in coincidencia.groupdict().items()}
    if any(valor < 1 for valor in partes.values()):
        raise ValueError(
            f"Código de ubicación inválido: usa el formato {FORMATO_CODIGO}"
        )

    return (
        f"A{partes['carril']:02d}"
        f"-T{partes['tramo']:02d}"
        f"-R{partes['tira']:02d}"
        f"-N{partes['nivel']}"
    )
