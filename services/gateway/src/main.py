from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from .config import Settings
from .core.counter import RoundRobinCounter
from .core.health import HealthChecker
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    settings = Settings()

    app.state.counter = RoundRobinCounter()
    app.state.client = httpx.AsyncClient(timeout=settings.request_timeout)
    app.state.health_checker = HealthChecker(
        client=app.state.client,
        all_urls=settings.storage_urls,
        interval=settings.health_check_interval,
    )

    try:
        await app.state.health_checker.probe_once()
        app.state.health_checker.start()
        yield
    finally:
        await app.state.health_checker.stop()
        await app.state.client.aclose()


app = FastAPI(
    title="Gateway Service",
    lifespan=lifespan,
)

app.include_router(router)
