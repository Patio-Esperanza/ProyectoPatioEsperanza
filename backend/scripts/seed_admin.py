import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.core.security import hash_password
from app.models.enums import RolUsuario
from app.models.usuario import Usuario

NOMBRE = "xoyoc"
EMAIL = "xoyocl2@gmail.com"
PASSWORD = "Azrael1977$2025"


async def main() -> None:
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        existing = await db.execute(select(Usuario).where(Usuario.email == EMAIL))
        if existing.scalar_one_or_none() is not None:
            print(f"Usuario {EMAIL} ya existe, no se crea de nuevo.")
            return

        usuario = Usuario(
            nombre=NOMBRE,
            email=EMAIL,
            password_hash=hash_password(PASSWORD),
            tipo=RolUsuario.ADMIN,
            activo=True,
        )
        db.add(usuario)
        await db.commit()
        print(f"Usuario admin creado: {EMAIL} (id={usuario.id})")

    await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
