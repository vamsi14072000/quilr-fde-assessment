import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


PRIMARY_TIMEOUT_SECONDS = 3.0


class ProviderError(Exception):
    """Internal provider failure."""


class ProviderRateLimited(ProviderError):
    """Provider returned HTTP 429."""


@dataclass
class ProviderResponse:
    provider: str
    data: dict[str, Any]


ProviderCallable = Callable[
    [dict[str, Any]],
    Awaitable[dict[str, Any]],
]


class ProviderRouter:
    def __init__(
        self,
        primary: ProviderCallable,
        secondary: ProviderCallable,
        timeout_seconds: float = PRIMARY_TIMEOUT_SECONDS,
    ):
        self.primary = primary
        self.secondary = secondary
        self.timeout_seconds = timeout_seconds

    async def _call_secondary(
        self,
        payload: dict[str, Any],
    ) -> ProviderResponse:
        try:
            result = await self.secondary(payload)

            return ProviderResponse(
                provider="secondary",
                data=result,
            )

        except Exception as exc:
            raise ProviderError(
                "All providers unavailable"
            ) from exc

    async def call(
        self,
        payload: dict[str, Any],
    ) -> ProviderResponse:
        try:
            result = await asyncio.wait_for(
                self.primary(payload),
                timeout=self.timeout_seconds,
            )

            return ProviderResponse(
                provider="primary",
                data=result,
            )

        except ProviderRateLimited:
            return await self._call_secondary(payload)

        except (TimeoutError, asyncio.TimeoutError):
            return await self._call_secondary(payload)

        except Exception as exc:
            raise ProviderError(
                "Primary provider failed"
            ) from exc