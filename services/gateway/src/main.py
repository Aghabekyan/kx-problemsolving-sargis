from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from config import Settings
from core.counter import RoundRobinCounter
from core.health import HealthChecker
from routes import router

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(timeout=settings.request_timeout)
    app.state.health_checker = HealthChecker(
        client=app.state.client,
        all_urls=settings.storage_urls,
        interval=settings.health_check_interval,
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
