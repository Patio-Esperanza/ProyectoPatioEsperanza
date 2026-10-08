from app.config import settings
from app.core.email_templates import correo_codigo_verificacion


def test_incluye_el_nombre_y_el_codigo():
    html = correo_codigo_verificacion(
        nombre="Juan Pérez", email="juan@empresa.mx", codigo="074723", minutos=15
    )

    assert "Juan Pérez" in html
    assert "074723" in html
    assert "15 minutos" in html


def test_sin_nombre_saluda_al_cliente():
    html = correo_codigo_verificacion(
        nombre=None, email="juan@empresa.mx", codigo="074723", minutos=15
    )

    assert "Estimado cliente" in html


def test_el_boton_precarga_el_correo_y_el_codigo():
    html = correo_codigo_verificacion(
        nombre="Juan", email="juan+alta@empresa.mx", codigo="074723", minutos=15
    )

    esperado = (
        f"{settings.app_base_url}/registro/verificar"
        "?email=juan%2Balta%40empresa.mx&codigo=074723"
    )
    assert esperado in html


def test_incluye_el_logo_y_los_datos_de_contacto():
    html = correo_codigo_verificacion(
        nombre="Juan", email="juan@empresa.mx", codigo="074723", minutos=15
    )

    assert settings.logo_url in html
    assert settings.contacto_telefono in html
    assert settings.contacto_email in html
    assert settings.sitio_web in html


def test_escapa_el_nombre_para_no_inyectar_html():
    html = correo_codigo_verificacion(
        nombre='<script>alert(1)</script>', email="juan@empresa.mx", codigo="074723", minutos=15
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
