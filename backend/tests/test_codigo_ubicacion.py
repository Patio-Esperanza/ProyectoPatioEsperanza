import pytest

from app.services.codigo_ubicacion import FORMATO_CODIGO, normalizar_codigo_ubicacion


@pytest.mark.parametrize(
    "entrada",
    [
        "A01-T01-R01-N1",
        "A01-T01-R01-N01",
        "A1-T1-R1-N1",
        "a01-t01-r01-n01",
        "  A01-T01-R01-N1  ",
        "A01 - T01 - R01 - N01",
    ],
)
def test_todas_las_formas_dan_el_mismo_codigo(entrada):
    assert normalizar_codigo_ubicacion(entrada) == "A01-T01-R01-N1"


def test_los_segmentos_de_dos_digitos_conservan_sus_digitos():
    assert normalizar_codigo_ubicacion("A12-T09-R10-N5") == "A12-T09-R10-N5"


def test_el_nivel_de_dos_digitos_reales_se_conserva():
    """El nivel no lleva cero a la izquierda, pero sí puede tener dos dígitos."""
    assert normalizar_codigo_ubicacion("A01-T01-R01-N12") == "A01-T01-R01-N12"


@pytest.mark.parametrize(
    "entrada",
    [
        "",
        "   ",
        "A01-T01-R01",
        "A01-T01-R01-N1-X01",
        "A01-T01-R01-X1",
        "T01-A01-R01-N1",
        "A01-T01-R01-N",
        "AA-T01-R01-N1",
        "A0-T01-R01-N1",
        "A01-T01-R01-N0",
    ],
)
def test_codigo_invalido_explica_el_formato(entrada):
    with pytest.raises(ValueError) as error:
        normalizar_codigo_ubicacion(entrada)

    assert FORMATO_CODIGO in str(error.value)
