from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from core.deps import get_gateway_service
from models import DataResponse, StatusResponse
from service import GatewayService, NoStorageAvailableError

router = APIRouter()


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
