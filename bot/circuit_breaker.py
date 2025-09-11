#!/usr/bin/env python3
"""
Circuit Breaker Module for Project Automation

Provides circuit breaker patterns for external service calls and error recovery.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar


logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit breaker is open, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Number of failures to open circuit
    recovery_timeout: float = 60.0  # Seconds before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: float = 30.0  # Request timeout in seconds
    expected_exceptions: tuple = (Exception,)  # Exceptions that count as failures


@dataclass
class CircuitStats:
    """Circuit breaker statistics."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    total_requests: int = 0
    total_failures: int = 0
    state_changed_time: datetime = field(default_factory=datetime.now)


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class CircuitBreakerTimeoutError(Exception):
    """Exception raised when operation times out."""

    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting external service calls.

    Prevents cascading failures by failing fast when a service is down,
    and automatically attempts recovery.
    """

    def __init__(self, name: str, config: Optional[CircuitConfig] = None):
        """Initialize circuit breaker with name and configuration."""
        self.name = name
        self.config = config or CircuitConfig()
        self.stats = CircuitStats()
        self._lock = asyncio.Lock()

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: When circuit is open
            CircuitBreakerTimeoutError: When operation times out
        """
        async with self._lock:
            self.stats.total_requests += 1

            # Check if circuit is open
            if self.stats.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    logger.warning(
                        f"Circuit breaker '{self.name}' is open, failing fast"
                    )
                    raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")

        # Execute the function with timeout
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs), timeout=self.config.timeout
                )
            else:
                # Run synchronous function in thread pool with timeout
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, func, *args, **kwargs
                    ),
                    timeout=self.config.timeout,
                )

            await self._on_success()
            return result

        except asyncio.TimeoutError as e:
            logger.warning(f"Circuit breaker '{self.name}' operation timed out")
            await self._on_failure(CircuitBreakerTimeoutError("Operation timed out"))
            raise CircuitBreakerTimeoutError("Operation timed out") from e

        except self.config.expected_exceptions as e:
            logger.warning(
                f"Circuit breaker '{self.name}' caught expected exception: {e}"
            )
            await self._on_failure(e)
            raise type(e)(str(e)) from e

        except Exception as e:
            logger.error(
                f"Circuit breaker '{self.name}' caught unexpected exception: {e}"
            )
            await self._on_failure(e)
            raise

    async def _on_success(self) -> None:
        """Handle successful operation."""
        async with self._lock:
            self.stats.success_count += 1
            self.stats.last_success_time = datetime.now()

            # If we're in HALF_OPEN and we've reached the success threshold,
            # transition back to CLOSED.
            if (
                self.stats.state == CircuitState.HALF_OPEN
                and self.stats.success_count >= self.config.success_threshold
            ):
                self._transition_to_closed()

    async def _on_failure(self, exception: Exception) -> None:
        """Handle failed operation."""
        async with self._lock:
            self.stats.failure_count += 1
            self.stats.total_failures += 1
            self.stats.last_failure_time = datetime.now()

            if self.stats.state == CircuitState.CLOSED:
                if self.stats.failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
            elif self.stats.state == CircuitState.HALF_OPEN:
                self._transition_to_open()

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset to half-open."""
        if self.stats.last_failure_time is None:
            return True

        time_since_failure = datetime.now() - self.stats.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout

    def _transition_to_closed(self) -> None:
        """Transition to closed state."""
        logger.info(f"Circuit breaker '{self.name}' transitioning to CLOSED")
        self.stats.state = CircuitState.CLOSED
        self.stats.failure_count = 0
        self.stats.success_count = 0
        self.stats.state_changed_time = datetime.now()

    def _transition_to_open(self) -> None:
        """Transition to open state."""
        logger.warning(f"Circuit breaker '{self.name}' transitioning to OPEN")
        self.stats.state = CircuitState.OPEN
        self.stats.success_count = 0
        self.stats.state_changed_time = datetime.now()

    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
        self.stats.state = CircuitState.HALF_OPEN
        self.stats.failure_count = 0
        self.stats.success_count = 0
        self.stats.state_changed_time = datetime.now()

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "total_requests": self.stats.total_requests,
            "total_failures": self.stats.total_failures,
            "failure_rate": self.stats.total_failures
            / max(1, self.stats.total_requests),
            "last_failure_time": self.stats.last_failure_time.isoformat()
            if self.stats.last_failure_time
            else None,
            "last_success_time": self.stats.last_success_time.isoformat()
            if self.stats.last_success_time
            else None,
            "state_changed_time": self.stats.state_changed_time.isoformat(),
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
            },
        }

    async def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        async with self._lock:
            logger.info(f"Manually resetting circuit breaker '{self.name}'")
            self._transition_to_closed()


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""

    def __init__(self):
        """Initialize circuit breaker manager."""
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(
        self, name: str, config: Optional[CircuitConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all circuit breakers."""
        total_breakers = len(self._breakers)
        open_breakers = sum(
            1 for b in self._breakers.values() if b.stats.state == CircuitState.OPEN
        )
        half_open_breakers = sum(
            1
            for b in self._breakers.values()
            if b.stats.state == CircuitState.HALF_OPEN
        )

        status = "healthy"
        if open_breakers > 0:
            status = "critical" if open_breakers > total_breakers * 0.5 else "warning"
        elif half_open_breakers > 0:
            status = "warning"

        return {
            "status": status,
            "total_breakers": total_breakers,
            "open_breakers": open_breakers,
            "half_open_breakers": half_open_breakers,
            "closed_breakers": total_breakers - open_breakers - half_open_breakers,
        }


# Global circuit breaker manager
circuit_manager = CircuitBreakerManager()


def circuit_breaker(name: str, config: Optional[CircuitConfig] = None):
    """
    Decorator for applying circuit breaker to functions.

    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        breaker = circuit_manager.get_breaker(name, config)

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            return await breaker.call(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            return asyncio.run(breaker.call(func, *args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Utility functions for common use cases
async def call_with_circuit_breaker(
    name: str,
    func: Callable[..., T],
    *args,
    config: Optional[CircuitConfig] = None,
    **kwargs,
) -> T:
    """Call function with circuit breaker protection."""
    breaker = circuit_manager.get_breaker(name, config)
    return await breaker.call(func, *args, **kwargs)


def create_http_circuit_config(timeout: float = 30.0) -> CircuitConfig:
    """Create circuit breaker config optimized for HTTP calls."""
    return CircuitConfig(
        failure_threshold=3,
        recovery_timeout=30.0,
        success_threshold=2,
        timeout=timeout,
        expected_exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,
        ),
    )


def create_database_circuit_config(timeout: float = 10.0) -> CircuitConfig:
    """Create circuit breaker config optimized for database calls."""
    return CircuitConfig(
        failure_threshold=5,
        recovery_timeout=60.0,
        success_threshold=3,
        timeout=timeout,
        expected_exceptions=(
            ConnectionError,
            TimeoutError,
        ),
    )


def create_ai_service_circuit_config(timeout: float = 60.0) -> CircuitConfig:
    """Create circuit breaker config optimized for AI service calls."""
    return CircuitConfig(
        failure_threshold=3,
        recovery_timeout=120.0,  # AI services may need longer recovery
        success_threshold=2,
        timeout=timeout,
        expected_exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,
        ),
    )
