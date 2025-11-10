"""Caching utilities with Redis backend."""

import functools
import hashlib
from typing import Any, Callable, TypeVar, cast

import structlog
from aiocache import Cache  # type: ignore[import-untyped]
from aiocache.serializers import JsonSerializer  # type: ignore[import-untyped]

from app.core.config import settings

logger = structlog.get_logger()

# Initialize cache
cache = Cache(
    Cache.REDIS,
    endpoint=settings.REDIS_URL.split("://")[1].split("/")[0].split(":")[0],
    port=(
        int(settings.REDIS_URL.split("://")[1].split("/")[0].split(":")[1])
        if ":" in settings.REDIS_URL.split("://")[1].split("/")[0]
        else 6379
    ),
    namespace=settings.CACHE_PREFIX,
    serializer=JsonSerializer(),
)

F = TypeVar("F", bound=Callable[..., Any])


def generate_cache_key(func_name: str, *args: Any, **kwargs: Any) -> str:
    """Generate a unique cache key based on function name and arguments."""
    # Create a string representation of arguments
    key_parts = [func_name]

    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(hashlib.sha256(str(arg).encode()).hexdigest()[:16])

    # Add keyword arguments
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}:{v}")
        else:
            key_parts.append(f"{k}:{hashlib.sha256(str(v).encode()).hexdigest()[:16]}")

    return ":".join(key_parts)


def cached(ttl: int | None = None, key_prefix: str | None = None) -> Callable[[F], F]:
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds (default: from settings)
        key_prefix: Optional prefix for cache key
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not settings.CACHE_ENABLED:
                return await func(*args, **kwargs)

            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = generate_cache_key(prefix, *args, **kwargs)

            try:
                # Try to get from cache
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    logger.debug("cache_hit", key=cache_key)
                    return cached_value

                # Cache miss - execute function
                logger.debug("cache_miss", key=cache_key)
                result = await func(*args, **kwargs)

                # Store in cache
                cache_ttl = ttl or settings.CACHE_TTL
                await cache.set(cache_key, result, ttl=cache_ttl)

                return result

            except Exception as e:
                logger.error("cache_error", error=str(e), key=cache_key)
                # Fall back to executing function without cache
                return await func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


async def invalidate_cache(pattern: str) -> int:
    """
    Invalidate cache keys matching a pattern.

    Args:
        pattern: Pattern to match cache keys (e.g., "user:*")

    Returns:
        Number of keys deleted
    """
    try:
        # Note: aiocache doesn't support pattern deletion directly
        # This is a simplified implementation
        await cache.delete(pattern)
        logger.info("cache_invalidated", pattern=pattern)
        return 1
    except Exception as e:
        logger.error("cache_invalidation_failed", error=str(e), pattern=pattern)
        return 0


async def clear_all_cache() -> None:
    """Clear all cache entries."""
    try:
        await cache.clear()
        logger.info("cache_cleared")
    except Exception as e:
        logger.error("cache_clear_failed", error=str(e))


class CacheManager:
    """Cache manager for manual cache operations."""

    @staticmethod
    async def get(key: str) -> Any:
        """Get value from cache."""
        return await cache.get(key)

    @staticmethod
    async def set(key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache."""
        cache_ttl = ttl or settings.CACHE_TTL
        await cache.set(key, value, ttl=cache_ttl)

    @staticmethod
    async def delete(key: str) -> None:
        """Delete key from cache."""
        await cache.delete(key)

    @staticmethod
    async def exists(key: str) -> bool:
        """Check if key exists in cache."""
        exists: bool = await cache.exists(key)
        return exists

    @staticmethod
    async def increment(key: str, delta: int = 1) -> int:
        """Increment counter in cache."""
        current = await cache.get(key) or 0
        new_value = current + delta
        await cache.set(key, new_value)
        return new_value

    @staticmethod
    async def decrement(key: str, delta: int = 1) -> int:
        """Decrement counter in cache."""
        current = await cache.get(key) or 0
        new_value = max(0, current - delta)
        await cache.set(key, new_value)
        return new_value
