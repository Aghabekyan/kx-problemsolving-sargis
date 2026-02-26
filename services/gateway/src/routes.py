from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from .core.deps import get_gateway_service
from .models import DataResponse, ErrorResponse, StatusResponse
from .service import GatewayService, NoStorageAvailableError

router = APIRouter()

GatewayServiceDep = Annotated[GatewayService, Depends(get_gateway_service)]


@router.get(
    "/status",
    response_model=StatusResponse,
)
async def get_status(
    service: GatewayServiceDep,
) -> StatusResponse:
    return service.build_status_response()


@router.get(
    "/data",
    response_model=DataResponse,
    responses={503: {"model": ErrorResponse}},
)
async def get_data(
    service: GatewayServiceDep,
) -> DataResponse:
    try:
        return await service.fetch_data()
    except NoStorageAvailableError as exc:
        raise HTTPException(status_code=503, detail="No storage services available") from exc
