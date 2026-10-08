from app.config import settings
from app.core.email_templates import correo_codigo_verificacion, correo_pin_confirmacion


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


def test_el_pin_incluye_el_nombre_el_pin_y_el_contenedor():
    html = correo_pin_confirmacion(
        nombre="Juan Pérez", pin="8941", numero_contenedor="MSCU1234567"
    )

    assert "Juan Pérez" in html
    assert "8941" in html
    assert "MSCU1234567" in html


def test_el_pin_sin_nombre_saluda_al_cliente():
    html = correo_pin_confirmacion(nombre=None, pin="8941", numero_contenedor="MSCU1234567")

    assert "Estimado cliente" in html


def test_el_pin_advierte_que_es_intransferible():
    html = correo_pin_confirmacion(nombre="Juan", pin="8941", numero_contenedor="MSCU1234567")

    assert "personal e intransferible" in html
    assert "No lo compartas con nadie" in html


def test_el_boton_del_pin_lleva_a_mis_contenedores():
    html = correo_pin_confirmacion(nombre="Juan", pin="8941", numero_contenedor="MSCU1234567")

    assert f"{settings.app_base_url}/mis-contenedores" in html


def test_el_pin_incluye_el_logo_y_los_datos_de_contacto():
    html = correo_pin_confirmacion(nombre="Juan", pin="8941", numero_contenedor="MSCU1234567")

    assert settings.logo_url in html
    assert settings.contacto_telefono in html
    assert settings.contacto_email in html


def test_el_pin_escapa_el_nombre_y_el_contenedor():
    html = correo_pin_confirmacion(
        nombre="<script>alert(1)</script>", pin="8941", numero_contenedor="<b>MSCU1</b>"
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;b&gt;MSCU1&lt;/b&gt;" in html
