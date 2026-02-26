from contextlib import asynccontextmanager

import os

import httpx
from fastapi import FastAPI

from core.counter import RoundRobinCounter
from core.health import HealthChecker
from routes import router


def _parse_storage_urls(raw_urls: str) -> list[str]:
    urls = [url.strip().rstrip("/") for url in raw_urls.split(",") if url.strip()]
    if not urls:
        raise ValueError("STORAGE_URLS must contain at least one URL.")
    return urls


REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "1.5"))
HEALTHCHECK_INTERVAL_SECONDS = float(os.getenv("HEALTHCHECK_INTERVAL_SECONDS", "3"))
STORAGE_URLS = _parse_storage_urls(
    os.getenv(
        "STORAGE_URLS",
        "http://storage1:8000,http://storage2:8000,http://storage3:8000",
    )
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)
    app.state.health_checker = HealthChecker(
        client=app.state.client,
        all_urls=STORAGE_URLS,
        interval=HEALTHCHECK_INTERVAL_SECONDS,
    )
    await app.state.health_checker.probe_once()
    app.state.health_checker.start()
    app.state.counter = RoundRobinCounter(start=0)

    try:
        yield
    finally:
        checker = getattr(app.state, "health_checker", None)
        if checker is not None:
            await checker.stop()

        client = getattr(app.state, "client", None)
        if client is not None:
            await client.aclose()


app = FastAPI(title="Gateway Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)
