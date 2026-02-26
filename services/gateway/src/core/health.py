import asyncio
import logging
from contextlib import suppress

import httpx

logger = logging.getLogger(__name__)

class HealthChecker:
    """Background health-checker that maintains a cached list of healthy URLs.

    Periodically probes all configured Storage Services and updates an internal
    ``healthy_urls`` list.  The ``/data`` endpoint reads from this cached list
    instead of probing on every request, keeping the hot path fast.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        all_urls: list[str],
        interval: float = 5.0,
    ) -> None:
        self._client = client
        self._all_urls = all_urls
        self._interval = interval
        self._healthy_urls: list[str] = []
        self._statuses: dict[str, str] = {url: "down" for url in all_urls}
        self._task: asyncio.Task[None] | None = None

    @property
    def healthy_urls(self) -> list[str]:
        return list(self._healthy_urls)

    @property
    def statuses(self) -> dict[str, str]:
        return dict(self._statuses)

    async def probe_once(self) -> None:
        """Run a single health-check cycle against all configured URLs."""
        results = await asyncio.gather(
            *(self._probe_url(url) for url in self._all_urls),
            return_exceptions=False,
        )
        statuses: dict[str, str] = {url: status for url, status in results}
        healthy = [url for url, status in results if status == "up"]
        self._healthy_urls = healthy
        self._statuses = statuses

    async def _probe_url(self, url: str) -> tuple[str, str]:
        try:
            resp = await self._client.get(f"{url}/health")
            return url, "up" if resp.status_code == 200 else "down"
        except httpx.RequestError:
            return url, "down"

    async def _run(self) -> None:
        """Loop that probes services at a fixed interval."""
        while True:
            try:
                await self.probe_once()
            except Exception:  # noqa: BLE001
                logger.exception("Health-check cycle failed")
            await asyncio.sleep(self._interval)

    def start(self) -> None:
        """Launch the background health-check loop."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Cancel and await the background task."""
        task = self._task
        self._task = None
        if task is not None:
            if not task.done():
                task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    def mark_unhealthy(self, url: str) -> None:
        """Reactively remove a URL from the healthy list (called on request failure)."""
        self._statuses[url] = "down"
        self._healthy_urls = [u for u in self._healthy_urls if u != url]
