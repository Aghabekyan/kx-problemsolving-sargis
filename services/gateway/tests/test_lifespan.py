import httpx
import pytest

from services.gateway.src.core.counter import RoundRobinCounter
from services.gateway.src.core.health import HealthChecker
from services.gateway.src.main import app

pytestmark = pytest.mark.asyncio


async def test_lifespan_initializes_and_shuts_down_runtime(monkeypatch: pytest.MonkeyPatch):
    urls = [
        "http://storage-1:8000",
        "http://storage-2:8000",
        "http://storage-3:8000",
    ]
    monkeypatch.setenv("STORAGE_SERVICES", ",".join(urls))
    monkeypatch.setenv("HEALTH_CHECK_INTERVAL", "3600")

    async def _mock_get(self: httpx.AsyncClient, url: str, **_: object) -> httpx.Response:
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            json={"status": "healthy", "instance": "mock-storage"},
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", _mock_get)

    async with app.router.lifespan_context(app):
        assert isinstance(app.state.counter, RoundRobinCounter)
        assert isinstance(app.state.client, httpx.AsyncClient)
        assert isinstance(app.state.health_checker, HealthChecker)
        assert app.state.health_checker.healthy_urls == urls
        assert set(app.state.health_checker.statuses.values()) == {"up"}

    assert app.state.client.is_closed


async def test_lifespan_fails_fast_without_storage_services(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("STORAGE_SERVICES", raising=False)

    with pytest.raises(ValueError, match="STORAGE_SERVICES"):
        async with app.router.lifespan_context(app):
            pass
