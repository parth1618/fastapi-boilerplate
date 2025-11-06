"""Circuit breaker and retry logic for resilience."""

import asyncio
import functools
from typing import Any, Callable, TypeVar, cast

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = structlog.get_logger()

F = TypeVar("F", bound=Callable[..., Any])


def with_retry(
    max_attempts: int | None = None,
    wait_multiplier: int | None = None,
    wait_max: int | None = None,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """
    Decorator to add retry logic to a function.

    Args:
        max_attempts: Maximum number of retry attempts
        wait_multiplier: Multiplier for exponential backoff
        wait_max: Maximum wait time between retries
        retry_on: Tuple of exceptions to retry on
    """

    def decorator(func: F) -> F:
        if not settings.RETRY_ENABLED:
            return func

        max_attempts_val = max_attempts or settings.RETRY_MAX_ATTEMPTS
        wait_multiplier_val = wait_multiplier or settings.RETRY_WAIT_EXPONENTIAL_MULTIPLIER
        wait_max_val = wait_max or settings.RETRY_WAIT_EXPONENTIAL_MAX

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            @retry(
                stop=stop_after_attempt(max_attempts_val),
                wait=wait_exponential(multiplier=wait_multiplier_val, max=wait_max_val),
                retry=retry_if_exception_type(retry_on),
                reraise=True,
            )
            async def _retry_wrapper() -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        error=str(e),
                    )
                    raise

            return await _retry_wrapper()

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            @retry(
                stop=stop_after_attempt(max_attempts_val),
                wait=wait_exponential(multiplier=wait_multiplier_val, max=wait_max_val),
                retry=retry_if_exception_type(retry_on),
                reraise=True,
            )
            def _retry_wrapper() -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        error=str(e),
                    )
                    raise

            return _retry_wrapper()

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    return decorator


def with_circuit_breaker(
    failure_threshold: int | None = None,
    recovery_timeout: int | None = None,
    expected_exception: type[Exception] = Exception,
) -> Callable[[F], F]:
    """
    Decorator to add circuit breaker pattern to a function.

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type that triggers circuit breaker
    """

    def decorator(func: F) -> F:
        if not settings.CIRCUIT_BREAKER_ENABLED:
            return func

        failure_threshold_val = failure_threshold or settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        recovery_timeout_val = recovery_timeout or settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT

        # Import circuit breaker here to avoid issues with typing
        try:
            from circuitbreaker import CircuitBreaker  # type: ignore[import-untyped]

            breaker = CircuitBreaker(
                failure_threshold=failure_threshold_val,
                recovery_timeout=recovery_timeout_val,
                expected_exception=expected_exception,
            )
        except ImportError:
            # If circuit breaker not available, return function as-is
            logger.warning("circuitbreaker module not available")
            return func

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await breaker.call_async(func, *args, **kwargs)
            except Exception as e:
                logger.error(
                    "circuit_breaker_failure",
                    function=func.__name__,
                    error=str(e),
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return breaker.call(func, *args, **kwargs)
            except Exception as e:
                logger.error(
                    "circuit_breaker_failure",
                    function=func.__name__,
                    error=str(e),
                )
                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    return decorator


def resilient(
    max_attempts: int | None = None,
    circuit_failure_threshold: int | None = None,
    circuit_recovery_timeout: int | None = None,
) -> Callable[[F], F]:
    """
    Decorator combining both retry and circuit breaker patterns.

    Args:
        max_attempts: Maximum retry attempts
        circuit_failure_threshold: Circuit breaker failure threshold
        circuit_recovery_timeout: Circuit breaker recovery timeout
    """

    def decorator(func: F) -> F:
        # Apply circuit breaker first, then retry
        func_with_cb = with_circuit_breaker(
            failure_threshold=circuit_failure_threshold,
            recovery_timeout=circuit_recovery_timeout,
        )(func)
        return with_retry(max_attempts=max_attempts)(func_with_cb)

    return decorator
