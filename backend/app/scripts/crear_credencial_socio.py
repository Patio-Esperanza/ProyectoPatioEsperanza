import asyncio
import argparse
import secrets
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import SessionLocal
from app.models.socio import CredencialSocio
from app.core.security import hash_password


async def crear_credencial(
    nombre: str,
    cliente_id: uuid.UUID | None = None,
    patios_permitidos: list[uuid.UUID] | None = None,
    webhook_url: str | None = None,
    webhook_secreto: str | None = None,
):
    prefijo = secrets.token_hex(4)  # 8 hex chars
    secreto = secrets.token_urlsafe(32)
    secreto_hash = hash_password(secreto)

    async with SessionLocal() as db:
        credencial = CredencialSocio(
            nombre=nombre,
            cliente_id=cliente_id,
            prefijo=prefijo,
            secreto_hash=secreto_hash,
            patios_permitidos=patios_permitidos or [],
            webhook_url=webhook_url,
            webhook_secreto=webhook_secreto,
            activo=True,
        )
        db.add(credencial)
        await db.commit()
        await db.refresh(credencial)

        print(f"Credencial creada exitosamente para el socio: {nombre}")
        print(f"ID: {credencial.id}")
        print(f"Prefijo: {prefijo}")
        print("API Key (GUARDE ESTE VALOR, NO SE VOLVERÁ A MOSTRAR):")
        print(f"ApiKey {prefijo}.{secreto}")


def main():
    parser = argparse.ArgumentParser(
        description="Crear credencial de API para socio externo"
    )
    parser.add_argument("--nombre", required=True, help="Nombre del socio (ej. Kasu)")
    parser.add_argument(
        "--cliente-id", help="UUID del cliente asociado (opcional)"
    )
    parser.add_argument(
        "--patios", help="IDs de patios permitidos separados por coma (UUIDs)"
    )
    parser.add_argument("--webhook-url", help="URL de webhook (opcional)")
    parser.add_argument(
        "--webhook-secreto", help="Secreto para webhook HMAC (opcional)"
    )

    args = parser.parse_args()

    cliente_uuid = uuid.UUID(args.cliente_id) if args.cliente_id else None
    patios_list = (
        [uuid.UUID(p.strip()) for p in args.patios.split(",")]
        if args.patios
        else []
    )

    asyncio.run(
        crear_credencial(
            nombre=args.nombre,
            cliente_id=cliente_uuid,
            patios_permitidos=patios_list,
            webhook_url=args.webhook_url,
            webhook_secreto=args.webhook_secreto,
        )
    )


if __name__ == "__main__":
    main()
