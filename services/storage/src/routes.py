import os
import socket
from datetime import datetime, timezone

from fastapi import APIRouter


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


SERVICE_NAME = os.getenv("SERVICE_NAME", socket.gethostname())

DUMMY_PAYLOAD = [
    {"id": 1, "name": "item-1", "value": "alpha"},
    {"id": 2, "name": "item-2", "value": "beta"},
    {"id": 3, "name": "item-3", "value": "gamma"},
]

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"service": SERVICE_NAME, "status": "ok"}


@router.get("/data")
async def data() -> dict[str, object]:
    return {
        "service": SERVICE_NAME,
        "generated_at": _utc_now_iso(),
        "payload": DUMMY_PAYLOAD,
    }
