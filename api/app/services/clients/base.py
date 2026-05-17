import logging

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=5.0, read=30.0, write=5.0, pool=5.0)


class ClientError(Exception):
    """Raised when an upstream HTTP call fails or returns an unexpected payload."""


def _normalize_base_url(url: str) -> str:
    """Ensure base_url ends with a single slash so httpx joins paths correctly.

    httpx behavior: if base_url has no trailing slash and we pass a relative path,
    the last segment of base_url is replaced. With a trailing slash, the path is
    appended. We always want append behavior.
    """
    return url if url.endswith("/") else url + "/"


class BaseHTTPClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = _normalize_base_url(base_url)
        transport = httpx.AsyncHTTPTransport(retries=2)
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            transport=transport,
            headers=headers or {},
        )

    @property
    def base_url(self) -> str:
        return self._base_url

    async def aclose(self) -> None:
        if not self._client.is_closed:
            await self._client.aclose()

    async def _get_json(self, path: str, *, params: dict | None = None) -> dict:
        # Path must be relative (no leading slash) for proper join with base_url.
        relative = path.lstrip("/")
        try:
            response = await self._client.get(relative, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Upstream HTTP error: %s %s -> %s",
                relative,
                params,
                exc.response.status_code,
            )
            raise ClientError(
                f"Upstream {self._base_url}{relative} returned {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("Upstream network error: %s %s -> %s", relative, params, exc)
            raise ClientError(
                f"Upstream {self._base_url}{relative} unreachable: {exc}"
            ) from exc
        except ValueError as exc:
            raise ClientError(
                f"Upstream {self._base_url}{relative} returned invalid JSON"
            ) from exc
