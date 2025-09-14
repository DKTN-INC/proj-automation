#!/usr/bin/env python3
"""
Reliability Configuration Module

Centralized configuration for reliability settings across the automation platform.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breakers."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3
    timeout: float = 30.0


@dataclass
class HealthMonitorConfig:
    """Configuration for health monitoring."""

    check_interval: int = 60
    memory_threshold_mb: int = 500
    cpu_threshold_percent: float = 85.0
    disk_threshold_percent: float = 85.0
    file_handles_threshold: int = 200
    enable_alerts: bool = True
    alert_cooldown_minutes: int = 15


@dataclass
class ResourceManagerConfig:
    """Configuration for resource management."""

    max_temp_files: int = 1000
    temp_file_max_age_hours: int = 24
    max_http_sessions: int = 10
    http_session_timeout: float = 30.0
    memory_gc_threshold_mb: int = 500
    resource_cleanup_interval: int = 300


@dataclass
class RetryConfig:
    """Configuration for retry mechanisms."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    openai_requests_per_minute: int = 60
    github_requests_per_hour: int = 5000
    discord_commands_per_minute: int = 30
    web_search_requests_per_minute: int = 10


class ReliabilityConfig:
    """Main reliability configuration class."""

    def __init__(self):
        """Initialize reliability configuration from environment variables."""
        self.circuit_breaker = self._load_circuit_breaker_config()
        self.health_monitor = self._load_health_monitor_config()
        self.resource_manager = self._load_resource_manager_config()
        self.retry = self._load_retry_config()
        self.rate_limit = self._load_rate_limit_config()

    def _load_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Load circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=int(os.getenv("CB_FAILURE_THRESHOLD", "5")),
            recovery_timeout=float(os.getenv("CB_RECOVERY_TIMEOUT", "60.0")),
            success_threshold=int(os.getenv("CB_SUCCESS_THRESHOLD", "3")),
            timeout=float(os.getenv("CB_TIMEOUT", "30.0")),
        )

    def _load_health_monitor_config(self) -> HealthMonitorConfig:
        """Load health monitor configuration."""
        return HealthMonitorConfig(
            check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "60")),
            memory_threshold_mb=int(os.getenv("HEALTH_MEMORY_THRESHOLD_MB", "500")),
            cpu_threshold_percent=float(os.getenv("HEALTH_CPU_THRESHOLD", "85.0")),
            disk_threshold_percent=float(os.getenv("HEALTH_DISK_THRESHOLD", "85.0")),
            file_handles_threshold=int(
                os.getenv("HEALTH_FILE_HANDLES_THRESHOLD", "200")
            ),
            enable_alerts=os.getenv("HEALTH_ENABLE_ALERTS", "true").lower() == "true",
            alert_cooldown_minutes=int(
                os.getenv("HEALTH_ALERT_COOLDOWN_MINUTES", "15")
            ),
        )

    def _load_resource_manager_config(self) -> ResourceManagerConfig:
        """Load resource manager configuration."""
        return ResourceManagerConfig(
            max_temp_files=int(os.getenv("RM_MAX_TEMP_FILES", "1000")),
            temp_file_max_age_hours=int(os.getenv("RM_TEMP_FILE_MAX_AGE_HOURS", "24")),
            max_http_sessions=int(os.getenv("RM_MAX_HTTP_SESSIONS", "10")),
            http_session_timeout=float(os.getenv("RM_HTTP_SESSION_TIMEOUT", "30.0")),
            memory_gc_threshold_mb=int(os.getenv("RM_MEMORY_GC_THRESHOLD_MB", "500")),
            resource_cleanup_interval=int(os.getenv("RM_CLEANUP_INTERVAL", "300")),
        )

    def _load_retry_config(self) -> RetryConfig:
        """Load retry configuration."""
        return RetryConfig(
            max_retries=int(os.getenv("RETRY_MAX_RETRIES", "3")),
            base_delay=float(os.getenv("RETRY_BASE_DELAY", "1.0")),
            max_delay=float(os.getenv("RETRY_MAX_DELAY", "60.0")),
            exponential_base=float(os.getenv("RETRY_EXPONENTIAL_BASE", "2.0")),
            jitter=os.getenv("RETRY_JITTER", "true").lower() == "true",
        )

    def _load_rate_limit_config(self) -> RateLimitConfig:
        """Load rate limiting configuration."""
        return RateLimitConfig(
            openai_requests_per_minute=int(os.getenv("RATE_LIMIT_OPENAI_RPM", "60")),
            github_requests_per_hour=int(os.getenv("RATE_LIMIT_GITHUB_RPH", "5000")),
            discord_commands_per_minute=int(os.getenv("RATE_LIMIT_DISCORD_CPM", "30")),
            web_search_requests_per_minute=int(
                os.getenv("RATE_LIMIT_WEB_SEARCH_RPM", "10")
            ),
        )

    def get_config_dict(self) -> dict[str, Any]:
        """Get configuration as dictionary."""
        return {
            "circuit_breaker": {
                "failure_threshold": self.circuit_breaker.failure_threshold,
                "recovery_timeout": self.circuit_breaker.recovery_timeout,
                "success_threshold": self.circuit_breaker.success_threshold,
                "timeout": self.circuit_breaker.timeout,
            },
            "health_monitor": {
                "check_interval": self.health_monitor.check_interval,
                "memory_threshold_mb": self.health_monitor.memory_threshold_mb,
                "cpu_threshold_percent": self.health_monitor.cpu_threshold_percent,
                "disk_threshold_percent": self.health_monitor.disk_threshold_percent,
                "file_handles_threshold": self.health_monitor.file_handles_threshold,
                "enable_alerts": self.health_monitor.enable_alerts,
                "alert_cooldown_minutes": self.health_monitor.alert_cooldown_minutes,
            },
            "resource_manager": {
                "max_temp_files": self.resource_manager.max_temp_files,
                "temp_file_max_age_hours": self.resource_manager.temp_file_max_age_hours,
                "max_http_sessions": self.resource_manager.max_http_sessions,
                "http_session_timeout": self.resource_manager.http_session_timeout,
                "memory_gc_threshold_mb": self.resource_manager.memory_gc_threshold_mb,
                "resource_cleanup_interval": self.resource_manager.resource_cleanup_interval,
            },
            "retry": {
                "max_retries": self.retry.max_retries,
                "base_delay": self.retry.base_delay,
                "max_delay": self.retry.max_delay,
                "exponential_base": self.retry.exponential_base,
                "jitter": self.retry.jitter,
            },
            "rate_limit": {
                "openai_requests_per_minute": self.rate_limit.openai_requests_per_minute,
                "github_requests_per_hour": self.rate_limit.github_requests_per_hour,
                "discord_commands_per_minute": self.rate_limit.discord_commands_per_minute,
                "web_search_requests_per_minute": self.rate_limit.web_search_requests_per_minute,
            },
        }

    def validate_config(self) -> tuple[bool, list[str]]:
        """Validate configuration values."""
        issues = []

        # Validate circuit breaker config
        if self.circuit_breaker.failure_threshold <= 0:
            issues.append("Circuit breaker failure threshold must be positive")
        if self.circuit_breaker.recovery_timeout <= 0:
            issues.append("Circuit breaker recovery timeout must be positive")
        if self.circuit_breaker.success_threshold <= 0:
            issues.append("Circuit breaker success threshold must be positive")
        if self.circuit_breaker.timeout <= 0:
            issues.append("Circuit breaker timeout must be positive")

        # Validate health monitor config
        if self.health_monitor.check_interval <= 0:
            issues.append("Health check interval must be positive")
        if self.health_monitor.memory_threshold_mb <= 0:
            issues.append("Memory threshold must be positive")
        if not 0 < self.health_monitor.cpu_threshold_percent <= 100:
            issues.append("CPU threshold must be between 0 and 100")
        if not 0 < self.health_monitor.disk_threshold_percent <= 100:
            issues.append("Disk threshold must be between 0 and 100")

        # Validate resource manager config
        if self.resource_manager.max_temp_files <= 0:
            issues.append("Max temp files must be positive")
        if self.resource_manager.temp_file_max_age_hours <= 0:
            issues.append("Temp file max age must be positive")
        if self.resource_manager.max_http_sessions <= 0:
            issues.append("Max HTTP sessions must be positive")

        # Validate retry config
        if self.retry.max_retries < 0:
            issues.append("Max retries must be non-negative")
        if self.retry.base_delay <= 0:
            issues.append("Base delay must be positive")
        if self.retry.max_delay <= 0:
            issues.append("Max delay must be positive")
        if self.retry.exponential_base <= 1:
            issues.append("Exponential base must be greater than 1")

        # Validate rate limit config
        if self.rate_limit.openai_requests_per_minute <= 0:
            issues.append("OpenAI requests per minute must be positive")
        if self.rate_limit.github_requests_per_hour <= 0:
            issues.append("GitHub requests per hour must be positive")
        if self.rate_limit.discord_commands_per_minute <= 0:
            issues.append("Discord commands per minute must be positive")

        return len(issues) == 0, issues

    def log_config(self) -> None:
        """Log current configuration."""
        logger.info("Reliability Configuration:")
        config_dict = self.get_config_dict()

        for section, values in config_dict.items():
            logger.info(f"  {section.replace('_', ' ').title()}:")
            for key, value in values.items():
                logger.info(f"    {key}: {value}")


# Global configuration instance
reliability_config = ReliabilityConfig()


def get_reliability_config() -> ReliabilityConfig:
    """Get the global reliability configuration."""
    return reliability_config


def validate_reliability_config() -> tuple[bool, list[str]]:
    """Validate the global reliability configuration."""
    return reliability_config.validate_config()


def log_reliability_config() -> None:
    """Log the global reliability configuration."""
    reliability_config.log_config()


# Configuration constants for easy access
CIRCUIT_BREAKER_CONFIG = reliability_config.circuit_breaker
HEALTH_MONITOR_CONFIG = reliability_config.health_monitor
RESOURCE_MANAGER_CONFIG = reliability_config.resource_manager
RETRY_CONFIG = reliability_config.retry
RATE_LIMIT_CONFIG = reliability_config.rate_limit
