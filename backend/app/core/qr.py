import io
import segno

def qr_png_bytes(texto: str, scale: int = 5) -> bytes:
    """Genera imagen QR como bytes PNG."""
    qr = segno.make(texto, error="L")
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=scale)
    return buffer.getvalue()
