from typing import Optional
from unittest.mock import patch

import httpx
import pytest
from httpx import AsyncClient

from services.gateway.src.core.health import HealthChecker

pytestmark = pytest.mark.asyncio

ALL_STORAGE = {"storage-1", "storage-2", "storage-3"}
RuntimeFixture = tuple[httpx.AsyncClient, HealthChecker]


def _instance_from_url(url: str) -> str:
    return url.split("//", 1)[1].split(":", 1)[0]


def _health_response(instance: str, url: str) -> httpx.Response:
    request = httpx.Request("GET", url)
    return httpx.Response(200, json={"status": "healthy", "instance": instance}, request=request)


def _data_response(instance: str, url: str) -> httpx.Response:
    request = httpx.Request("GET", url)
    return httpx.Response(
        200,
        json={
            "instance": instance,
            "data": [{"id": 1, "name": "item-1", "value": "alpha"}],
        },
        request=request,
    )


def _mock_get(
    down: Optional[set[str]] = None,
    data_log: Optional[list[str]] = None,
):
    down = down or set()

    async def get(url: str, **_: object) -> httpx.Response:
        instance = _instance_from_url(url)
        request = httpx.Request("GET", url)
        if instance in down:
            raise httpx.ConnectError("Connection refused", request=request)

        if url.endswith("/health"):
            return _health_response(instance, url)

        if url.endswith("/data"):
            if data_log is not None:
                data_log.append(instance)
            return _data_response(instance, url)

        raise AssertionError(f"Unexpected URL: {url}")

    return get


async def _seed_health(
    runtime: RuntimeFixture,
    down: Optional[set[str]] = None,
) -> None:
    client, checker = runtime
    with patch.object(client, "get", side_effect=_mock_get(down=down)):
        await checker.probe_once()


async def test_status_all_up(client: AsyncClient, runtime: RuntimeFixture):
    await _seed_health(runtime)

    resp = await client.get("/status")

    assert resp.status_code == 200
    services = resp.json()["services"]
    assert len(services) == 3
    assert all(item["status"] == "up" for item in services)


async def test_status_partial_down(client: AsyncClient, runtime: RuntimeFixture):
    await _seed_health(runtime, down={"storage-1"})

    resp = await client.get("/status")

    statuses = {item["url"]: item["status"] for item in resp.json()["services"]}
    assert statuses == {
        "http://storage-1:8000": "down",
        "http://storage-2:8000": "up",
        "http://storage-3:8000": "up",
    }


async def test_data_round_robin_wraps(client: AsyncClient, runtime: RuntimeFixture):
    await _seed_health(runtime)
    log: list[str] = []

    runtime_client, _ = runtime
    with patch.object(runtime_client, "get", side_effect=_mock_get(data_log=log)):
        for _ in range(6):
            resp = await client.get("/data")
            assert resp.status_code == 200

    assert log == ["storage-1", "storage-2", "storage-3", "storage-1", "storage-2", "storage-3"]


async def test_data_skips_down_service(client: AsyncClient, runtime: RuntimeFixture):
    await _seed_health(runtime, down={"storage-2"})
    log: list[str] = []

    with patch.object(
        runtime[0],
        "get",
        side_effect=_mock_get(down={"storage-2"}, data_log=log),
    ):
        for _ in range(4):
            resp = await client.get("/data")
            assert resp.status_code == 200

    assert log == ["storage-1", "storage-3", "storage-1", "storage-3"]


async def test_data_returns_503_when_everything_is_down(
    client: AsyncClient,
    runtime: RuntimeFixture,
):
    await _seed_health(runtime, down=ALL_STORAGE)

    resp = await client.get("/data")

    assert resp.status_code == 503
    assert "No storage services available" in resp.json()["detail"]


async def test_data_retry_uses_next_service(
    client: AsyncClient,
    runtime: RuntimeFixture,
):
    await _seed_health(runtime)

    with patch.object(
        runtime[0],
        "get",
        side_effect=_mock_get(down={"storage-1"}),
    ):
        resp = await client.get("/data")

    assert resp.status_code == 200
    assert resp.json()["instance"] == "storage-2"


async def test_data_retry_marks_service_unhealthy(
    client: AsyncClient,
    runtime: RuntimeFixture,
):
    await _seed_health(runtime)

    runtime_client, checker = runtime
    with patch.object(runtime_client, "get", side_effect=_mock_get(down={"storage-1"})):
        await client.get("/data")

    assert "http://storage-1:8000" not in checker.healthy_urls


async def test_data_retry_returns_503_if_all_crash(
    client: AsyncClient,
    runtime: RuntimeFixture,
):
    await _seed_health(runtime)

    with patch.object(
        runtime[0],
        "get",
        side_effect=_mock_get(down=ALL_STORAGE),
    ):
        resp = await client.get("/data")

    assert resp.status_code == 503
