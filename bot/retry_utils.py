#!/usr/bin/env python3
"""
Enhanced Retry Utilities

Provides comprehensive retry mechanisms with various strategies and backoff algorithms.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, TypeVar


try:
    from .reliability_config import RETRY_CONFIG
except ImportError:
    # Fallback configuration
    from types import SimpleNamespace

    RETRY_CONFIG = SimpleNamespace(
        max_retries=3, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True
    )


logger = logging.getLogger(__name__)
T = TypeVar("T")


class RetryError(Exception):
    """Exception raised when all retry attempts fail."""

    pass


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""

    attempt: int
    delay: float
    exception: Optional[Exception] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success: bool = False


class RetryStrategy:
    """Base class for retry strategies."""

    def get_delay(self, attempt: int) -> float:
        """Get delay for the given attempt number."""
        raise NotImplementedError

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if we should retry for the given attempt and exception."""
        raise NotImplementedError


class ExponentialBackoffStrategy(RetryStrategy):
    """Exponential backoff retry strategy."""

    def __init__(
        self,
        base_delay: float = None,
        max_delay: float = None,
        exponential_base: float = None,
        jitter: bool = None,
        max_retries: int = None,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        """Initialize exponential backoff strategy."""
        self.base_delay = base_delay or RETRY_CONFIG.base_delay
        self.max_delay = max_delay or RETRY_CONFIG.max_delay
        self.exponential_base = exponential_base or RETRY_CONFIG.exponential_base
        self.jitter = jitter if jitter is not None else RETRY_CONFIG.jitter
        self.max_retries = max_retries or RETRY_CONFIG.max_retries
        self.retryable_exceptions = retryable_exceptions

    def get_delay(self, attempt: int) -> float:
        """Calculate delay using exponential backoff."""
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add jitter to prevent thundering herd
            jitter_amount = delay * 0.1
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if we should retry."""
        if attempt >= self.max_retries:
            return False

        return isinstance(exception, self.retryable_exceptions)


class LinearBackoffStrategy(RetryStrategy):
    """Linear backoff retry strategy."""

    def __init__(
        self,
        base_delay: float = None,
        max_delay: float = None,
        increment: float = 1.0,
        jitter: bool = None,
        max_retries: int = None,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        """Initialize linear backoff strategy."""
        self.base_delay = base_delay or RETRY_CONFIG.base_delay
        self.max_delay = max_delay or RETRY_CONFIG.max_delay
        self.increment = increment
        self.jitter = jitter if jitter is not None else RETRY_CONFIG.jitter
        self.max_retries = max_retries or RETRY_CONFIG.max_retries
        self.retryable_exceptions = retryable_exceptions

    def get_delay(self, attempt: int) -> float:
        """Calculate delay using linear backoff."""
        delay = self.base_delay + (self.increment * (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            jitter_amount = delay * 0.1
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if we should retry."""
        if attempt >= self.max_retries:
            return False

        return isinstance(exception, self.retryable_exceptions)


class FixedDelayStrategy(RetryStrategy):
    """Fixed delay retry strategy."""

    def __init__(
        self,
        delay: float = None,
        jitter: bool = None,
        max_retries: int = None,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        """Initialize fixed delay strategy."""
        self.delay = delay or RETRY_CONFIG.base_delay
        self.jitter = jitter if jitter is not None else RETRY_CONFIG.jitter
        self.max_retries = max_retries or RETRY_CONFIG.max_retries
        self.retryable_exceptions = retryable_exceptions

    def get_delay(self, attempt: int) -> float:
        """Return fixed delay."""
        delay = self.delay

        if self.jitter:
            jitter_amount = delay * 0.1
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if we should retry."""
        if attempt >= self.max_retries:
            return False

        return isinstance(exception, self.retryable_exceptions)


class RetryHandler:
    """Handles retry logic with configurable strategies."""

    def __init__(self, strategy: Optional[RetryStrategy] = None):
        """Initialize retry handler with strategy."""
        self.strategy = strategy or ExponentialBackoffStrategy()
        self.attempts: list[RetryAttempt] = []

    async def execute_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute async function with retry logic."""
        self.attempts.clear()
        attempt = 0

        while True:
            attempt += 1
            start_time = datetime.now()

            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, func, *args, **kwargs
                    )

                # Success
                self.attempts.append(
                    RetryAttempt(
                        attempt=attempt,
                        delay=0,
                        start_time=start_time,
                        end_time=datetime.now(),
                        success=True,
                    )
                )

                logger.debug(f"Function succeeded on attempt {attempt}")
                return result

            except Exception as e:
                end_time = datetime.now()

                if self.strategy.should_retry(attempt, e):
                    delay = self.strategy.get_delay(attempt)

                    self.attempts.append(
                        RetryAttempt(
                            attempt=attempt,
                            delay=delay,
                            exception=e,
                            start_time=start_time,
                            end_time=end_time,
                            success=False,
                        )
                    )

                    logger.warning(
                        f"Function failed on attempt {attempt}, retrying in {delay:.2f}s: {e}"
                    )

                    if delay > 0:
                        await asyncio.sleep(delay)

                    continue
                else:
                    # No more retries
                    self.attempts.append(
                        RetryAttempt(
                            attempt=attempt,
                            delay=0,
                            exception=e,
                            start_time=start_time,
                            end_time=end_time,
                            success=False,
                        )
                    )

                    logger.error(f"Function failed after {attempt} attempts: {e}")
                    raise RetryError(
                        f"Function failed after {attempt} attempts: {e}"
                    ) from e

    def execute_sync(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute sync function with retry logic."""
        self.attempts.clear()
        attempt = 0

        while True:
            attempt += 1
            start_time = datetime.now()

            try:
                result = func(*args, **kwargs)

                # Success
                self.attempts.append(
                    RetryAttempt(
                        attempt=attempt,
                        delay=0,
                        start_time=start_time,
                        end_time=datetime.now(),
                        success=True,
                    )
                )

                logger.debug(f"Function succeeded on attempt {attempt}")
                return result

            except Exception as e:
                end_time = datetime.now()

                if self.strategy.should_retry(attempt, e):
                    delay = self.strategy.get_delay(attempt)

                    self.attempts.append(
                        RetryAttempt(
                            attempt=attempt,
                            delay=delay,
                            exception=e,
                            start_time=start_time,
                            end_time=end_time,
                            success=False,
                        )
                    )

                    logger.warning(
                        f"Function failed on attempt {attempt}, retrying in {delay:.2f}s: {e}"
                    )

                    if delay > 0:
                        time.sleep(delay)

                    continue
                else:
                    # No more retries
                    self.attempts.append(
                        RetryAttempt(
                            attempt=attempt,
                            delay=0,
                            exception=e,
                            start_time=start_time,
                            end_time=end_time,
                            success=False,
                        )
                    )

                    logger.error(f"Function failed after {attempt} attempts: {e}")
                    raise RetryError(
                        f"Function failed after {attempt} attempts: {e}"
                    ) from e

    def get_stats(self) -> dict[str, Any]:
        """Get retry statistics."""
        if not self.attempts:
            return {}

        total_attempts = len(self.attempts)
        successful_attempts = sum(1 for a in self.attempts if a.success)
        failed_attempts = total_attempts - successful_attempts

        total_time = sum(
            (a.end_time - a.start_time).total_seconds()
            for a in self.attempts
            if a.start_time and a.end_time
        )

        total_delay = sum(a.delay for a in self.attempts)

        return {
            "total_attempts": total_attempts,
            "successful_attempts": successful_attempts,
            "failed_attempts": failed_attempts,
            "success_rate": (
                successful_attempts / total_attempts if total_attempts > 0 else 0
            ),
            "total_execution_time": total_time,
            "total_delay_time": total_delay,
            "average_attempt_time": (
                total_time / total_attempts if total_attempts > 0 else 0
            ),
        }


def retry_async(
    strategy: Optional[RetryStrategy] = None,
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
):
    """Decorator for async functions with retry logic."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            if strategy is None:
                retry_strategy = ExponentialBackoffStrategy(
                    max_retries=max_retries,
                    base_delay=base_delay,
                    max_delay=max_delay,
                    retryable_exceptions=retryable_exceptions or (Exception,),
                )
            else:
                retry_strategy = strategy

            handler = RetryHandler(retry_strategy)
            return await handler.execute_async(func, *args, **kwargs)

        return wrapper

    return decorator


def retry_sync(
    strategy: Optional[RetryStrategy] = None,
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
):
    """Decorator for sync functions with retry logic."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if strategy is None:
                retry_strategy = ExponentialBackoffStrategy(
                    max_retries=max_retries,
                    base_delay=base_delay,
                    max_delay=max_delay,
                    retryable_exceptions=retryable_exceptions or (Exception,),
                )
            else:
                retry_strategy = strategy

            handler = RetryHandler(retry_strategy)
            return handler.execute_sync(func, *args, **kwargs)

        return wrapper

    return decorator


# Convenience functions
async def retry_async_call(
    func: Callable[..., T], *args, strategy: Optional[RetryStrategy] = None, **kwargs
) -> T:
    """Execute async function with retry logic."""
    handler = RetryHandler(strategy or ExponentialBackoffStrategy())
    return await handler.execute_async(func, *args, **kwargs)


def retry_sync_call(
    func: Callable[..., T], *args, strategy: Optional[RetryStrategy] = None, **kwargs
) -> T:
    """Execute sync function with retry logic."""
    handler = RetryHandler(strategy or ExponentialBackoffStrategy())
    return handler.execute_sync(func, *args, **kwargs)


# Pre-configured strategies for common use cases
def create_http_retry_strategy() -> RetryStrategy:
    """Create retry strategy optimized for HTTP requests."""
    return ExponentialBackoffStrategy(
        base_delay=1.0,
        max_delay=30.0,
        max_retries=3,
        retryable_exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,
        ),
    )


def create_database_retry_strategy() -> RetryStrategy:
    """Create retry strategy optimized for database operations."""
    return ExponentialBackoffStrategy(
        base_delay=0.5,
        max_delay=10.0,
        max_retries=5,
        retryable_exceptions=(
            ConnectionError,
            TimeoutError,
        ),
    )


def create_ai_service_retry_strategy() -> RetryStrategy:
    """Create retry strategy optimized for AI service calls."""
    return ExponentialBackoffStrategy(
        base_delay=2.0,
        max_delay=60.0,
        max_retries=3,
        retryable_exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,
        ),
    )


def create_file_operation_retry_strategy() -> RetryStrategy:
    """Create retry strategy optimized for file operations."""
    return LinearBackoffStrategy(
        base_delay=0.1,
        max_delay=5.0,
        increment=0.1,
        max_retries=10,
        retryable_exceptions=(
            OSError,
            IOError,
            PermissionError,
        ),
    )
