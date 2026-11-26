import uuid
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.socio_security import verificar_api_key, CurrentSocio
from app.models.socio import CredencialSocio
from app.models.ubicacion import Patio


@pytest.mark.anyio
async def test_verificar_api_key_missing_header():
    with pytest.raises(HTTPException) as exc:
        await verificar_api_key(authorization=None, db=None)  # type: ignore
    assert exc.value.status_code == 401
    assert "requerido" in exc.value.detail


@pytest.mark.anyio
async def test_verificar_api_key_invalid_scheme():
    with pytest.raises(HTTPException) as exc:
        await verificar_api_key(authorization="Bearer token123", db=None)  # type: ignore
    assert exc.value.status_code == 401
    assert "esquema" in exc.value.detail.lower()


@pytest.mark.anyio
async def test_verificar_api_key_invalid_format():
    with pytest.raises(HTTPException) as exc:
        await verificar_api_key(authorization="ApiKey nodot", db=None)  # type: ignore
    assert exc.value.status_code == 401
    assert "formato" in exc.value.detail.lower()


@pytest.mark.anyio
async def test_verificar_api_key_not_found(db_session: AsyncSession):
    with pytest.raises(HTTPException) as exc:
        await verificar_api_key(authorization="ApiKey nonexist.secret", db=db_session)
    assert exc.value.status_code == 401
    assert "no encontrada" in exc.value.detail.lower()


@pytest.mark.anyio
async def test_verificar_api_key_inactive(db_session: AsyncSession):
    patio = Patio(nombre="Patio Test", codigo="PT1")
    db_session.add(patio)
    await db_session.flush()

    hashed = hash_password("secret123")
    socio = CredencialSocio(
        nombre="Kasu Inactivo",
        prefijo="inactive",
        secreto_hash=hashed,
        patios_permitidos=[patio.id],
        activo=False,
    )
    db_session.add(socio)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await verificar_api_key(authorization="ApiKey inactive.secret123", db=db_session)
    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_verificar_api_key_wrong_secret(db_session: AsyncSession):
    patio = Patio(nombre="Patio Test", codigo="PT2")
    db_session.add(patio)
    await db_session.flush()

    hashed = hash_password("secret123")
    socio = CredencialSocio(
        nombre="Kasu Activo",
        prefijo="active01",
        secreto_hash=hashed,
        patios_permitidos=[patio.id],
        activo=True,
    )
    db_session.add(socio)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await verificar_api_key(authorization="ApiKey active01.wrongsecret", db=db_session)
    assert exc.value.status_code == 401
    assert "inválida" in exc.value.detail.lower()


@pytest.mark.anyio
async def test_verificar_api_key_success(db_session: AsyncSession):
    patio = Patio(nombre="Patio Test", codigo="PT3")
    db_session.add(patio)
    await db_session.flush()

    hashed = hash_password("secret123")
    socio = CredencialSocio(
        nombre="Kasu Partner",
        prefijo="kasu0010",
        secreto_hash=hashed,
        patios_permitidos=[patio.id],
        webhook_url="https://example.com/webhook",
        webhook_secreto="wh-sec",
        activo=True,
    )
    db_session.add(socio)
    await db_session.flush()

    current_socio = await verificar_api_key(
        authorization="ApiKey kasu0010.secret123", db=db_session
    )

    assert isinstance(current_socio, CurrentSocio)
    assert current_socio.id == socio.id
    assert current_socio.nombre == "Kasu Partner"
    assert current_socio.patios_permitidos == [patio.id]
    assert current_socio.webhook_url == "https://example.com/webhook"
    assert current_socio.webhook_secreto == "wh-sec"
    assert socio.ultimo_uso_en is not None
