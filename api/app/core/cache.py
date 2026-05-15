import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import redis.asyncio as redis_async

from app.core.config import settings

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

_redis_client: redis_async.Redis | None = None


def get_redis() -> redis_async.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_async.from_url(
            settings.redis_url,
            decode_responses=True,
            health_check_interval=30,
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


async def get_cached(key: str) -> Any | None:
    raw = await get_redis().get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


async def set_cached(key: str, value: Any, ttl: int | None = None) -> None:
    payload = json.dumps(value, default=str)
    await get_redis().set(key, payload, ex=ttl or settings.cache_default_ttl)


async def invalidate_prefix(prefix: str) -> int:
    """Delete all keys starting with `prefix`. Use sparingly — SCAN is O(N)."""
    client = get_redis()
    deleted = 0
    async for key in client.scan_iter(match=f"{prefix}*"):
        await client.delete(key)
        deleted += 1
    return deleted


def _make_key(prefix: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    raw = json.dumps({"args": args, "kwargs": kwargs}, default=str, sort_keys=True)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def cached(
    ttl: int | None = None,
    key_prefix: str = "cache",
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator that caches the result of an async function in Redis."""

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = _make_key(f"{key_prefix}:{func.__qualname__}", args, kwargs)
            hit = await get_cached(key)
            if hit is not None:
                return hit  # type: ignore[return-value]
            result = await func(*args, **kwargs)
            try:
                await set_cached(key, result, ttl)
            except Exception as exc:  # cache failure must not break business logic
                logger.warning("Cache set failed for %s: %s", key, exc)
            return result

        return wrapper

    return decorator
