from datetime import datetime, timezone

from fastapi import APIRouter

from config import Settings


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


settings = Settings()

DUMMY_PAYLOAD = [
    {"id": 1, "name": "item-1", "value": "alpha"},
    {"id": 2, "name": "item-2", "value": "beta"},
    {"id": 3, "name": "item-3", "value": "gamma"},
]

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"service": settings.instance_name, "status": "ok"}


@router.get("/data")
async def data() -> dict[str, object]:
    return {
        "service": settings.instance_name,
        "generated_at": _utc_now_iso(),
        "payload": DUMMY_PAYLOAD,
    }
