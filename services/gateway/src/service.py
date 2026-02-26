from __future__ import annotations

import logging

import httpx
from pydantic import ValidationError

from core.counter import RoundRobinCounter
from core.health import HealthChecker
from models import DataResponse, StatusResponse, StorageStatus

logger = logging.getLogger(__name__)


class NoStorageAvailableError(Exception):
    """Raised when no storage backend can serve the request."""


class GatewayService:
    """Encapsulates gateway routing/fallback behavior."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        checker: HealthChecker,
        counter: RoundRobinCounter,
    ) -> None:
        self._client = client
        self._checker = checker
        self._counter = counter

    def build_status_response(self) -> StatusResponse:
        return StatusResponse(
            services=[
                StorageStatus(url=url, status=status)
                for url, status in self._checker.statuses.items()
            ]
        )

    async def fetch_data(self) -> DataResponse:
        candidates = tuple(self._checker.healthy_urls)
        if not candidates:
            raise NoStorageAvailableError

        start_idx = self._counter.next(len(candidates))

        for url in candidates[start_idx:] + candidates[:start_idx]:
            try:
                resp = await self._client.get(f"{url}/data")
                resp.raise_for_status()
                payload = resp.json()
                return DataResponse(
                    instance=str(payload.get("service", url)),
                    data=payload.get("payload", []),
                )
            except (httpx.HTTPError, ValueError, ValidationError, TypeError) as exc:
                logger.warning(
                    "Storage request failed for %s: %s. Marking unhealthy and trying next.",
                    url,
                    exc,
                )
                self._checker.mark_unhealthy(url)

        raise NoStorageAvailableError
