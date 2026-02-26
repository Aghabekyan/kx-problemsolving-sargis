from typing import Annotated, cast

import httpx
from fastapi import Depends, Request

from ..service import GatewayService
from .counter import RoundRobinCounter
from .health import HealthChecker


async def get_http_client(
    request: Request,
) -> httpx.AsyncClient:
    return cast(httpx.AsyncClient, request.app.state.client)


async def get_health_checker(
    request: Request,
) -> HealthChecker:
    return cast(HealthChecker, request.app.state.health_checker)


async def get_counter(request: Request) -> RoundRobinCounter:
    return cast(RoundRobinCounter, request.app.state.counter)


async def get_gateway_service(
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    checker: Annotated[HealthChecker, Depends(get_health_checker)],
    counter: Annotated[RoundRobinCounter, Depends(get_counter)],
) -> GatewayService:
    return GatewayService(client=client, checker=checker, counter=counter)
