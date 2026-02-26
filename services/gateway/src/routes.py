import asyncio
import os
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from core.health import HealthChecker
from core.counter import RoundRobinCounter


def _service_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or url
    return host.split(".")[0]


def _parse_storage_urls(raw_urls: str) -> list[str]:
    urls = [url.strip().rstrip("/") for url in raw_urls.split(",") if url.strip()]
    if not urls:
        raise ValueError("STORAGE_URLS must contain at least one URL.")
    return urls


class DataItem(BaseModel):
    id: int
    name: str
    value: str


class DataResponse(BaseModel):
    instance: str
    data: list[DataItem]


REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "1.5"))
HEALTHCHECK_INTERVAL_SECONDS = float(os.getenv("HEALTHCHECK_INTERVAL_SECONDS", "3"))
STORAGE_URLS = _parse_storage_urls(
    os.getenv(
        "STORAGE_URLS",
        "http://storage1:8000,http://storage2:8000,http://storage3:8000",
    )
)

SERVICES = [
    {
        "name": _service_name_from_url(url),
        "url": url,
    }
    for url in STORAGE_URLS
]
SERVICE_NAME_BY_URL = {service["url"]: service["name"] for service in SERVICES}

HTTP_CLIENT: httpx.AsyncClient | None = None
HEALTH_CHECKER: HealthChecker | None = None
ROUND_ROBIN_COUNTER = RoundRobinCounter(start=0)
ROUND_ROBIN_LOCK = asyncio.Lock()

router = APIRouter()


def _get_health_checker() -> HealthChecker:
    if HEALTH_CHECKER is None:
        raise HTTPException(status_code=503, detail="Gateway health checker is not initialized.")
    return HEALTH_CHECKER


async def _ordered_healthy_urls(healthy_urls: list[str]) -> list[str]:
    if not healthy_urls:
        return []

    async with ROUND_ROBIN_LOCK:
        start = ROUND_ROBIN_COUNTER.next(len(healthy_urls))

    return healthy_urls[start:] + healthy_urls[:start]


async def _fetch_data_from_url(url: str) -> DataResponse | None:
    client = HTTP_CLIENT
    if client is None:
        return None

    checker = HEALTH_CHECKER
    default_instance = SERVICE_NAME_BY_URL.get(url, url)

    try:
        response = await client.get(f"{url}/data")
        response.raise_for_status()
        payload = response.json()
        return DataResponse(
            instance=str(payload.get("service", default_instance)),
            data=payload.get("payload", []),
        )
    except (httpx.HTTPError, ValidationError, ValueError, TypeError):
        if checker is not None:
            checker.mark_unhealthy(url)
        return None


async def startup_event() -> None:
    global HTTP_CLIENT, HEALTH_CHECKER, ROUND_ROBIN_COUNTER

    HTTP_CLIENT = httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)
    HEALTH_CHECKER = HealthChecker(
        client=HTTP_CLIENT,
        all_urls=[service["url"] for service in SERVICES],
        interval=HEALTHCHECK_INTERVAL_SECONDS,
    )
    await HEALTH_CHECKER.probe_once()
    HEALTH_CHECKER.start()
    ROUND_ROBIN_COUNTER = RoundRobinCounter(start=0)


async def shutdown_event() -> None:
    global HTTP_CLIENT, HEALTH_CHECKER

    checker = HEALTH_CHECKER
    HEALTH_CHECKER = None
    if checker is not None:
        await checker.stop()

    if HTTP_CLIENT is not None:
        await HTTP_CLIENT.aclose()
        HTTP_CLIENT = None


@router.get("/status")
async def status() -> dict[str, Any]:
    checker = _get_health_checker()
    statuses = checker.statuses
    return {
        "services": [
            {
                "name": service["name"],
                "url": service["url"],
                "status": statuses.get(service["url"], "down"),
                "available": statuses.get(service["url"], "down") == "up",
            }
            for service in SERVICES
        ],
    }


@router.get("/data", response_model=DataResponse)
async def data() -> DataResponse:
    checker = _get_health_checker()
    healthy_urls = checker.healthy_urls

    if not healthy_urls:
        raise HTTPException(
            status_code=503,
            detail="No Storage Services are currently available.",
        )

    candidates = await _ordered_healthy_urls(healthy_urls)

    for url in candidates:
        parsed_payload = await _fetch_data_from_url(url)
        if parsed_payload is None:
            continue

        return parsed_payload

    raise HTTPException(
        status_code=503,
        detail="No Storage Services are currently available.",
    )
