from typing import Any

from fastapi import APIRouter

from .config import settings
from .models import DataResponse, HealthResponse

DUMMY_DATA: list[dict[str, Any]] = [
    {"id": 1, "name": "item-1", "value": "alpha"},
    {"id": 2, "name": "item-2", "value": "beta"},
    {"id": 3, "name": "item-3", "value": "gamma"},
]


router = APIRouter()


@router.get("/data", response_model=DataResponse)
async def get_data() -> DataResponse:
    return DataResponse(instance=settings.instance_id, data=DUMMY_DATA)  # type: ignore[arg-type]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="healthy", instance=settings.instance_id)
