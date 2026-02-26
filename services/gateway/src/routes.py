from __future__ import annotations

import os
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException

from core.counter import RoundRobinCounter
from core.deps import get_gateway_service
from core.health import HealthChecker
from models import DataResponse, StatusResponse
from service import GatewayService, NoStorageAvailableError


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

router = APIRouter()


async def startup_event(app: FastAPI) -> None:
    app.state.client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)
    app.state.health_checker = HealthChecker(
        client=app.state.client,
        all_urls=STORAGE_URLS,
        interval=HEALTHCHECK_INTERVAL_SECONDS,
    )
    await app.state.health_checker.probe_once()
    app.state.health_checker.start()
    app.state.counter = RoundRobinCounter(start=0)


async def shutdown_event(app: FastAPI) -> None:
    checker = getattr(app.state, "health_checker", None)
    if checker is not None:
        await checker.stop()

    client = getattr(app.state, "client", None)
    if client is not None:
        await client.aclose()


@router.get("/status", response_model=StatusResponse)
async def status(
    gateway_service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> StatusResponse:
    return gateway_service.build_status_response()


@router.get("/data", response_model=DataResponse)
async def data(
    gateway_service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> DataResponse:
    try:
        return await gateway_service.fetch_data()
    except NoStorageAvailableError as exc:
        raise HTTPException(
            status_code=503,
            detail="No Storage Services are currently available.",
        ) from exc
