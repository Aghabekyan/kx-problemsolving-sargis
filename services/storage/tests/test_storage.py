import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_data_response_shape(client: AsyncClient):
    resp = await client.get("/data")

    assert resp.status_code == 200
    body = resp.json()
    assert body["instance"] == "test-storage"
    assert body["data"]
    assert {"id", "name", "value"}.issubset(body["data"][0])


async def test_health_response(client: AsyncClient):
    resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy", "instance": "test-storage"}
