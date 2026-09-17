import pytest


@pytest.mark.anyio
async def test_health_returns_ok(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_health_db_returns_connected(client):
    response = await client.get("/api/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "connected"}
