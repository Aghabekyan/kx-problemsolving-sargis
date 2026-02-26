import asyncio
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _service_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or url
    return host.split(".")[0]


def _parse_storage_urls(raw_urls: str) -> list[str]:
    urls = [url.strip().rstrip("/") for url in raw_urls.split(",") if url.strip()]
    if not urls:
        raise ValueError("STORAGE_URLS must contain at least one URL.")
    return urls


@dataclass
class ServiceStatus:
    name: str
    url: str
    available: bool = False
    last_checked: str | None = None
    last_error: str | None = "Not checked yet"


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
STATUSES = {
    service["name"]: ServiceStatus(name=service["name"], url=service["url"])
    for service in SERVICES
}

HTTP_CLIENT: httpx.AsyncClient | None = None
HEALTH_TASK: asyncio.Task[Any] | None = None
ROUND_ROBIN_INDEX = 0
ROUND_ROBIN_LOCK = asyncio.Lock()

router = APIRouter()


class DataItem(BaseModel):
    id: int
    name: str
    value: str


class DataResponse(BaseModel):
    instance: str
    data: list[DataItem]


async def _refresh_service_status(service: dict[str, str]) -> None:
    global HTTP_CLIENT

    name = service["name"]
    url = service["url"]
    status = STATUSES[name]
    checked_at = _utc_now_iso()

    if HTTP_CLIENT is None:
        status.available = False
        status.last_checked = checked_at
        status.last_error = "Gateway HTTP client is not initialized."
        return

    try:
        response = await HTTP_CLIENT.get(f"{url}/health")
        if response.status_code == 200:
            status.available = True
            status.last_error = None
        else:
            status.available = False
            status.last_error = f"Health check returned HTTP {response.status_code}"
    except Exception as exc:
        status.available = False
        status.last_error = f"{type(exc).__name__}: {exc}"

    status.last_checked = checked_at


async def _refresh_all_statuses() -> None:
    await asyncio.gather(*(_refresh_service_status(service) for service in SERVICES))


async def _healthcheck_loop() -> None:
    while True:
        await _refresh_all_statuses()
        await asyncio.sleep(HEALTHCHECK_INTERVAL_SECONDS)


async def _ordered_service_indices() -> list[int]:
    async with ROUND_ROBIN_LOCK:
        start = ROUND_ROBIN_INDEX
    return list(range(start, len(SERVICES))) + list(range(0, start))


async def _set_round_robin_index(next_index: int) -> None:
    global ROUND_ROBIN_INDEX
    async with ROUND_ROBIN_LOCK:
        ROUND_ROBIN_INDEX = next_index % len(SERVICES)


async def _fetch_from_service(service: dict[str, str]) -> dict[str, Any] | None:
    global HTTP_CLIENT

    name = service["name"]
    url = service["url"]
    status = STATUSES[name]
    checked_at = _utc_now_iso()

    if HTTP_CLIENT is None:
        status.available = False
        status.last_checked = checked_at
        status.last_error = "Gateway HTTP client is not initialized."
        return None

    try:
        response = await HTTP_CLIENT.get(f"{url}/data")
        response.raise_for_status()
        status.available = True
        status.last_checked = checked_at
        status.last_error = None
        return response.json()
    except Exception as exc:
        status.available = False
        status.last_checked = checked_at
        status.last_error = f"{type(exc).__name__}: {exc}"
        return None


async def startup_event() -> None:
    global HTTP_CLIENT, HEALTH_TASK
    HTTP_CLIENT = httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)
    await _refresh_all_statuses()
    HEALTH_TASK = asyncio.create_task(_healthcheck_loop())


async def shutdown_event() -> None:
    global HTTP_CLIENT, HEALTH_TASK

    if HEALTH_TASK is not None:
        HEALTH_TASK.cancel()
        try:
            await HEALTH_TASK
        except asyncio.CancelledError:
            pass
        HEALTH_TASK = None

    if HTTP_CLIENT is not None:
        await HTTP_CLIENT.aclose()
        HTTP_CLIENT = None


@router.get("/status")
async def status() -> dict[str, Any]:
    await _refresh_all_statuses()
    return {
        "services": [asdict(STATUSES[service["name"]]) for service in SERVICES],
    }


@router.get("/data", response_model=DataResponse)
async def data() -> DataResponse:
    await _refresh_all_statuses()
    ordered_indices = await _ordered_service_indices()

    for index in ordered_indices:
        service = SERVICES[index]
        service_status = STATUSES[service["name"]]
        if not service_status.available:
            continue

        payload = await _fetch_from_service(service)
        if payload is None:
            continue

        try:
            parsed_payload = DataResponse(
                instance=str(payload.get("service", service["name"])),
                data=payload.get("payload", []),
            )
        except ValidationError as exc:
            service_status.available = False
            service_status.last_error = f"ValidationError: {exc}"
            continue

        await _set_round_robin_index(index + 1)
        return parsed_payload

    raise HTTPException(
        status_code=503,
        detail="No Storage Services are currently available.",
    )
