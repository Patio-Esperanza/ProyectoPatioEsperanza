import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.cliente import Cliente
from app.models.enums import TipoCliente

def validar_numero_contenedor(numero: str) -> bool:
    """
    Valida formato ISO 6346 de número de contenedor:
    4 letras seguidas de 7 dígitos (ej. MSCU1234567).
    """
    if not numero or not isinstance(numero, str):
        return False
    pattern = r"^[A-Z]{4}[0-9]{7}$"
    return bool(re.match(pattern, numero.upper().strip()))

async def resolver_o_crear_cliente(
    db: AsyncSession,
    tipo: TipoCliente,
    rfc: str,
    nombre: str
) -> Cliente:
    """
    Busca un cliente por RFC; si no existe, lo crea con alta_por_socio=True y dias_libres=0.
    """
    stmt = select(Cliente).where(Cliente.rfc == rfc.strip().upper())
    result = await db.execute(stmt)
    cliente = result.scalar_one_or_none()

    if cliente:
        return cliente

    cliente = Cliente(
        razon_social=nombre.strip(),
        rfc=rfc.strip().upper(),
        tipo=tipo,
        dias_libres=0,
        activo=True,
        alta_por_socio=True
    )
    db.add(cliente)
    await db.flush()
    return cliente
