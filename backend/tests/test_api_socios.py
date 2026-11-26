import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.socio import CredencialSocio
from app.models.ubicacion import Patio
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, TipoContenedor, TamanoContenedor


@pytest.fixture
async def setup_socio_db(db_session: AsyncSession):
    patio = Patio(nombre="Patio Norte", codigo="PN1")
    db_session.add(patio)
    await db_session.flush()

    patio_forbidden = Patio(nombre="Patio Sur", codigo="PS1")
    db_session.add(patio_forbidden)
    await db_session.flush()

    hashed = hash_password("secret123")
    socio = CredencialSocio(
        nombre="Kasu Transportes",
        prefijo="kasu1234",
        secreto_hash=hashed,
        patios_permitidos=[patio.id],
        activo=True,
    )
    db_session.add(socio)
    await db_session.commit()

    return {"patio_id": patio.id, "patio_forbidden_id": patio_forbidden.id, "socio_id": socio.id, "prefijo": "kasu1234", "secreto": "secret123"}


@pytest.mark.asyncio
async def test_crear_solicitud_ingreso_socio(client: AsyncClient, db_session: AsyncSession, setup_socio_db):
    data_setup = setup_socio_db
    headers = {"Authorization": f"ApiKey {data_setup['prefijo']}.{data_setup['secreto']}"}

    payload = {
        "idempotency_key": "kasu:ref-001",
        "referencia_externa": "REF-001",
        "patio_id": str(data_setup["patio_id"]),
        "numero_contenedor": "MSCU1000001",
        "tipo": "lleno",
        "tamano": "40",
        "tipo_iso": "40HC",
        "peso_kg": 18500,
        "sellos": "SL123456",
        "cliente": {"tipo": "importador_exportador", "rfc": "IMM210702NL7", "nombre": "Importadora X"},
        "aduana": {"agencia": "LOGINCO", "num_refe": "LCLF0353/26"},
        "transporte": {"operador": "Juan Pérez", "telefono": "3311223344", "placas": "12AB3C", "numero_economico": "21"},
        "fecha_estimada_llegada": "2026-11-25T09:00:00Z"
    }

    response = await client.post("/api/socios/v1/solicitudes-ingreso", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "pin" in data
    assert data["estado"] == "solicitud_ingreso"
    assert data["referencia_externa"] == "REF-001"
    assert data["transporte_esperado"]["placas"] == "12AB3C"

    # Test idempotency
    response_idem = await client.post("/api/socios/v1/solicitudes-ingreso", json=payload, headers=headers)
    assert response_idem.status_code in (200, 201)
    assert response_idem.json()["id"] == data["id"]


@pytest.mark.asyncio
async def test_crear_solicitud_patio_no_permitido(client: AsyncClient, setup_socio_db):
    data_setup = setup_socio_db
    headers = {"Authorization": f"ApiKey {data_setup['prefijo']}.{data_setup['secreto']}"}

    payload = {
        "idempotency_key": "kasu:ref-002",
        "patio_id": str(data_setup["patio_forbidden_id"]),
        "numero_contenedor": "MSCU1000001",
        "tipo": "lleno",
        "tamano": "40",
        "peso_kg": 18500,
        "sellos": "SL123456",
        "cliente": {"tipo": "importador_exportador", "rfc": "IMM210702NL7", "nombre": "Importadora X"},
        "transporte": {"operador": "Juan Pérez", "placas": "12AB3C"}
    }

    response = await client.post("/api/socios/v1/solicitudes-ingreso", json=payload, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patch_y_cancelar_solicitud(client: AsyncClient, setup_socio_db):
    data_setup = setup_socio_db
    headers = {"Authorization": f"ApiKey {data_setup['prefijo']}.{data_setup['secreto']}"}

    payload = {
        "idempotency_key": "kasu:ref-003",
        "patio_id": str(data_setup["patio_id"]),
        "numero_contenedor": "TGHU1000002",
        "tipo": "vacio",
        "tamano": "20",
        "peso_kg": 2200,
        "cliente": {"tipo": "transportista", "rfc": "TRA210702NL7", "nombre": "Transportes T"},
        "transporte": {"operador": "Carlos Ruiz", "placas": "XYZ999"}
    }

    res_create = await client.post("/api/socios/v1/solicitudes-ingreso", json=payload, headers=headers)
    assert res_create.status_code == 201
    cont_id = res_create.json()["id"]

    # PATCH transport
    patch_payload = {
        "transporte": {"operador": "Carlos Ruiz Modificado", "placas": "XYZ888"}
    }
    res_patch = await client.patch(f"/api/socios/v1/solicitudes-ingreso/{cont_id}", json=patch_payload, headers=headers)
    assert res_patch.status_code == 200
    assert res_patch.json()["transporte_esperado"]["placas"] == "XYZ888"

    # CANCEL
    res_cancel = await client.post(f"/api/socios/v1/solicitudes-ingreso/{cont_id}/cancelar", headers=headers)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["estado"] == "rechazado"
