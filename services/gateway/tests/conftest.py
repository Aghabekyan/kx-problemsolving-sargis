from collections.abc import AsyncGenerator

import httpx
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from services.gateway.src.core.counter import RoundRobinCounter
from services.gateway.src.core.deps import get_health_checker, get_http_client
from services.gateway.src.core.health import HealthChecker
from services.gateway.src.main import app

URLS = [
    "http://storage-1:8000",
    "http://storage-2:8000",
    "http://storage-3:8000",
]


@pytest_asyncio.fixture
async def runtime() -> AsyncGenerator[tuple[httpx.AsyncClient, HealthChecker]]:
    runtime_client = httpx.AsyncClient(timeout=2.0)
    checker = HealthChecker(client=runtime_client, all_urls=URLS)

    async def _override_http_client() -> httpx.AsyncClient:
        return runtime_client

    async def _override_health_checker() -> HealthChecker:
        return checker

    app.dependency_overrides[get_http_client] = _override_http_client
    app.dependency_overrides[get_health_checker] = _override_health_checker
    app.state.counter = RoundRobinCounter()

    try:
        yield runtime_client, checker
    finally:
        app.dependency_overrides.pop(get_http_client, None)
        app.dependency_overrides.pop(get_health_checker, None)
        await runtime_client.aclose()


@pytest_asyncio.fixture
async def client(runtime: tuple[httpx.AsyncClient, HealthChecker]) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
