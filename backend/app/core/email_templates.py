"""Plantillas HTML de los correos salientes.

Los clientes de correo ignoran las hojas de estilo externas y buena parte de
CSS moderno, así que el diseño se construye con tablas anidadas y estilos en
línea. Es verboso a propósito: es la única forma de que el mismo correo se vea
igual en Gmail, Outlook y los clientes móviles.
"""

from html import escape
from urllib.parse import quote, urlencode

from app.config import settings
from app.core.qr import qr_png_bytes

COLOR_DORADO = "#d3a860"
COLOR_TEXTO = "#26242b"
COLOR_TEXTO_SUAVE = "#5f5c66"
COLOR_FONDO = "#f3f2f5"
COLOR_PIE = "#26242b"
COLOR_TEXTO_PIE = "#d8d7de"

FUENTE = "Arial, Helvetica, sans-serif"


def _plantilla_base(titulo_oculto: str, contenido: str) -> str:
    """Envuelve el contenido del mensaje en el encabezado y el pie de la marca.

    `titulo_oculto` es el texto de vista previa que algunos clientes muestran
    junto al asunto en la bandeja de entrada.
    """
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Patio Esperanza</title>
</head>
<body style="margin:0;padding:0;background-color:{COLOR_FONDO};">
<div style="display:none;font-size:1px;color:{COLOR_FONDO};line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">{escape(titulo_oculto)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{COLOR_FONDO};">
  <tr>
    <td align="center" style="padding:24px 12px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;background-color:#ffffff;border-radius:8px;overflow:hidden;">
        <tr>
          <td align="center" style="background-color:#ffffff;padding:32px 24px 16px 24px;">
            <img src="{settings.logo_url}" alt="Patio Esperanza" width="200" style="width:200px;max-width:70%;height:auto;display:block;border:0;">
          </td>
        </tr>
        <tr>
          <td style="padding:8px 32px 32px 32px;font-family:{FUENTE};color:{COLOR_TEXTO};">
{contenido}
          </td>
        </tr>
        <tr>
          <td style="background-color:{COLOR_PIE};padding:28px 32px;font-family:{FUENTE};color:{COLOR_TEXTO_PIE};font-size:13px;line-height:20px;">
            <p style="margin:0 0 4px 0;color:#ffffff;font-size:16px;font-weight:bold;">Patio Esperanza</p>
            <p style="margin:0 0 16px 0;color:{COLOR_DORADO};font-size:13px;">Resguarda, cuida y envía con seguridad.</p>
            <p style="margin:0 0 4px 0;">Teléfono: <a href="tel:{settings.contacto_telefono.replace(' ', '')}" style="color:{COLOR_TEXTO_PIE};text-decoration:none;">{settings.contacto_telefono}</a></p>
            <p style="margin:0 0 4px 0;">Correo: <a href="mailto:{settings.contacto_email}" style="color:{COLOR_TEXTO_PIE};text-decoration:none;">{settings.contacto_email}</a></p>
            <p style="margin:0 0 16px 0;">Sitio web: <a href="{settings.app_base_url}" style="color:{COLOR_TEXTO_PIE};text-decoration:none;">{settings.sitio_web}</a></p>
            <p style="margin:0;color:#8e8b96;font-size:12px;">Este es un mensaje automático, por favor no respondas a este correo.</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


def correo_codigo_verificacion(
    nombre: str | None, email: str, codigo: str, minutos: int
) -> str:
    """Correo con el código de verificación del registro de un cliente."""
    saludo = escape(nombre) if nombre else "Estimado cliente"
    consulta = urlencode({"email": email, "codigo": codigo})
    url_verificacion = f"{settings.app_base_url}/registro/verificar?{consulta}"

    contenido = f"""            <p style="margin:0 0 16px 0;font-size:16px;line-height:24px;">Hola, {saludo},</p>
            <p style="margin:0 0 24px 0;font-size:15px;line-height:24px;color:{COLOR_TEXTO_SUAVE};">
              Estás a un paso de completar tu registro en Patio Esperanza. Para garantizar la
              seguridad de tu cuenta y tus envíos, generamos el siguiente código de verificación:
            </p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td align="center" style="padding:8px 0 24px 0;">
                  <div style="font-family:{FUENTE};font-size:40px;font-weight:bold;letter-spacing:8px;color:{COLOR_DORADO};">{codigo}</div>
                </td>
              </tr>
            </table>
            <p style="margin:0 0 24px 0;font-size:15px;line-height:24px;color:{COLOR_TEXTO_SUAVE};">
              Este código es válido únicamente durante los próximos {minutos} minutos.
              Si no solicitaste este registro, ignora este mensaje.
            </p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td align="center" style="padding:0 0 24px 0;">
                  <a href="{url_verificacion}" style="display:inline-block;background-color:{COLOR_DORADO};color:#ffffff;font-family:{FUENTE};font-size:16px;font-weight:bold;text-decoration:none;padding:14px 32px;border-radius:6px;">Verificar mi cuenta</a>
                </td>
              </tr>
            </table>
            <p style="margin:0;font-size:13px;line-height:20px;color:{COLOR_TEXTO_SUAVE};">
              Si el botón no funciona, abre esta dirección en tu navegador:<br>
              <a href="{url_verificacion}" style="color:{COLOR_DORADO};">{url_verificacion}</a>
            </p>"""

    return _plantilla_base(
        f"Tu código de verificación es {codigo}. Expira en {minutos} minutos.", contenido
    )


def correo_pin_confirmacion(
    nombre: str | None,
    pin: str,
    numero_contenedor: str,
    tipo: str = "",
    tamano: str = "",
    peso_kg: int | None = None,
    sellos: str | None = None,
    fecha_estimada_retiro: str = "",
) -> tuple[str, list[tuple[str, bytes, str]]]:
    """Correo con el PIN y hoja de verificación con QR.

    Devuelve `(html, imagenes_inline)` para que `enviar_correo` adjunte el QR
    como imagen inline referenciada por CID.

    El QR lleva solo el número de contenedor en la URL de portería. El PIN NO
    va en el QR: si lo llevara, escanear la foto del correo verificaría la
    entrada sola y la verificación dejaría de servir para algo.
    """
    saludo = escape(nombre) if nombre else "Estimado cliente"
    contenedor = escape(numero_contenedor)
    url_porteria = (
        f"{settings.app_base_url}/porteria?contenedor={quote(numero_contenedor, safe='')}"
    )
    url_pase = f"{settings.app_base_url}/mis-contenedores"

    # Leyenda del sello
    sellos_texto = escape(sellos) if sellos else "S/N"

    # Detalles del contenedor para la hoja
    detalles_filas = f"""
              <tr><td style="padding:4px 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO_SUAVE};border-bottom:1px solid #eee;"><strong>Contenedor</strong></td><td style="padding:4px 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO};border-bottom:1px solid #eee;">{contenedor}</td></tr>"""

    if tipo:
        detalles_filas += f"""
              <tr><td style="padding:4px 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO_SUAVE};border-bottom:1px solid #eee;"><strong>Tipo</strong></td><td style="padding:4px 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO};border-bottom:1px solid #eee;">{escape(tipo)}</td></tr>"""

    if tamano:
        detalles_filas += f"""
              <tr><td style="padding:4px 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO_SUAVE};border-bottom:1px solid #eee;"><strong>Tamaño</strong></td><td style="padding:4px 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO};border-bottom:1px solid #eee;">{escape(tamano)}</td></tr>"""

    if peso_kg is not None:
        detalles_filas += f"""
              <tr><td style="padding:4px 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO_SUAVE};border-bottom:1px solid #eee;"><strong>Peso</strong></td><td style="padding:4px 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO};border-bottom:1px solid #eee;">{peso_kg:,} kg</td></tr>"""

    detalles_filas += f"""
              <tr><td style="padding:4px 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO_SUAVE};border-bottom:1px solid #eee;"><strong>Sellos</strong></td><td style="padding:4px 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO};border-bottom:1px solid #eee;">{sellos_texto}</td></tr>"""

    if fecha_estimada_retiro:
        detalles_filas += f"""
              <tr><td style="padding:4px 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO_SUAVE};"><strong>Fecha est. retiro</strong></td><td style="padding:4px 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO};">{escape(fecha_estimada_retiro)}</td></tr>"""

    contenido = f"""            <p style="margin:0 0 16px 0;font-size:16px;line-height:24px;">Hola, {saludo},</p>
            <p style="margin:0 0 24px 0;font-size:15px;line-height:24px;color:{COLOR_TEXTO_SUAVE};">
              Generaste un PIN de acceso para el contenedor
              <strong style="color:{COLOR_TEXTO};">{contenedor}</strong>.
              Presenta el siguiente código al operador en la entrada del patio:
            </p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td align="center" style="padding:8px 0 24px 0;">
                  <div style="font-family:{FUENTE};font-size:52px;font-weight:bold;letter-spacing:10px;color:{COLOR_DORADO};">{pin}</div>
                </td>
              </tr>
            </table>
            <p style="margin:0 0 8px 0;font-size:15px;font-weight:bold;color:{COLOR_TEXTO};">Instrucciones importantes</p>
            <ul style="margin:0 0 24px 0;padding-left:20px;font-size:15px;line-height:24px;color:{COLOR_TEXTO_SUAVE};">
              <li style="margin-bottom:6px;">Este PIN es de uso personal e intransferible.</li>
              <li style="margin-bottom:6px;">No lo compartas con nadie más.</li>
              <li>Si no solicitaste este acceso, ignora este mensaje.</li>
            </ul>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td align="center" style="padding:0 0 8px 0;">
                  <a href="{url_pase}" style="display:inline-block;background-color:{COLOR_DORADO};color:#ffffff;font-family:{FUENTE};font-size:16px;font-weight:bold;text-decoration:none;padding:14px 32px;border-radius:6px;">Ver mi pase de acceso</a>
                </td>
              </tr>
            </table>

            <!-- Hoja de verificación para el portero -->
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:32px;border:2px dashed {COLOR_DORADO};border-radius:8px;">
              <tr>
                <td style="padding:20px 24px;">
                  <p style="margin:0 0 4px 0;font-family:{FUENTE};font-size:11px;color:{COLOR_TEXTO_SUAVE};text-transform:uppercase;letter-spacing:2px;">Patio Esperanza</p>
                  <p style="margin:0 0 16px 0;font-family:{FUENTE};font-size:18px;font-weight:bold;color:{COLOR_TEXTO};">Hoja de verificación de entrada</p>
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                      <td style="vertical-align:top;width:65%;">
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
{detalles_filas}
                        </table>
                        <p style="margin:16px 0 0 12px;font-family:{FUENTE};font-size:14px;color:{COLOR_TEXTO_SUAVE};">
                          PIN: <strong style="font-size:24px;letter-spacing:6px;color:{COLOR_DORADO};">{pin}</strong>
                        </p>
                      </td>
                      <td style="vertical-align:middle;text-align:center;width:35%;padding:8px;">
                        <a href="{url_porteria}" style="text-decoration:none;"><img src="cid:qr_porteria" alt="QR verificación" width="140" height="140" style="width:140px;height:140px;display:block;margin:0 auto;border:0;" /></a>
                        <p style="margin:8px 0 0 0;font-family:{FUENTE};font-size:11px;color:{COLOR_TEXTO_SUAVE};">Escanear para verificar</p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>"""

    html = _plantilla_base(
        f"Tu PIN de acceso para el contenedor {numero_contenedor} es {pin}.", contenido
    )

    qr_bytes = qr_png_bytes(url_porteria)
    imagenes = [("qr_porteria", qr_bytes, "qr_porteria.png")]

    return html, imagenes
