#!/usr/bin/env python3
"""
Health Monitoring Module for Project Automation Bot

Provides health checks, monitoring capabilities, and system status tracking.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import psutil


logger = logging.getLogger(__name__)


@dataclass
class HealthMetric:
    """Represents a health metric with status and details."""

    name: str
    status: str  # "healthy", "warning", "critical"
    value: Any
    threshold: float | None = None
    message: str = ""
    last_check: datetime = field(default_factory=datetime.now)


@dataclass
class SystemHealth:
    """Aggregated system health status."""

    overall_status: str  # "healthy", "warning", "critical"
    metrics: dict[str, HealthMetric] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


class HealthMonitor:
    """Monitors system health and provides status information."""

    def __init__(self, check_interval: int = 60):
        """Initialize health monitor with check interval in seconds."""
        self.check_interval = check_interval
        self.metrics: dict[str, HealthMetric] = {}
        self.custom_checks: dict[str, Callable] = {}
        self._monitoring_task: asyncio.Task | None = None
        self._alerts_enabled = True
        self._alert_cooldowns: dict[str, datetime] = {}

    def register_custom_check(self, name: str, check_func: Callable) -> None:
        """Register a custom health check function."""
        self.custom_checks[name] = check_func

    def enable_alerts(self, enabled: bool = True) -> None:
        """Enable or disable health alerts."""
        self._alerts_enabled = enabled

    async def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Health monitoring already running")
            return

        logger.info("Starting health monitoring")
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Health monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        try:
            while True:
                await self.check_all_health()
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            logger.info("Health monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Health monitoring loop error: {e}", exc_info=True)

    async def check_all_health(self) -> SystemHealth:
        """Check all health metrics and return system status."""
        try:
            # System metrics
            await self._check_memory_usage()
            await self._check_disk_usage()
            await self._check_cpu_usage()
            await self._check_file_handles()
            await self._check_process_health()

            # Custom checks
            for name, check_func in self.custom_checks.items():
                try:
                    await self._run_custom_check(name, check_func)
                except Exception as e:
                    self.metrics[name] = HealthMetric(
                        name=name,
                        status="critical",
                        value=None,
                        message=f"Check failed: {e}",
                    )

            # Determine overall status
            overall_status = self._determine_overall_status()

            # Check for alerts
            if self._alerts_enabled:
                await self._check_alerts()

            return SystemHealth(
                overall_status=overall_status,
                metrics=self.metrics.copy(),
                last_updated=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return SystemHealth(
                overall_status="critical",
                metrics={"error": HealthMetric("error", "critical", str(e))},
                last_updated=datetime.now(),
            )

    async def _check_memory_usage(self) -> None:
        """Check system memory usage."""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent

            status = "healthy"
            if usage_percent > 90:
                status = "critical"
            elif usage_percent > 80:
                status = "warning"

            self.metrics["memory_usage"] = HealthMetric(
                name="memory_usage",
                status=status,
                value=usage_percent,
                threshold=80.0,
                message=(
                    f"{usage_percent:.1f}% used "
                    f"({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)"
                ),
            )
        except Exception as e:
            self.metrics["memory_usage"] = HealthMetric(
                name="memory_usage",
                status="critical",
                value=None,
                message=f"Failed to check memory: {e}",
            )

    async def _check_disk_usage(self) -> None:
        """Check disk usage for current directory."""
        try:
            usage = psutil.disk_usage(".")
            usage_percent = (usage.used / usage.total) * 100

            status = "healthy"
            if usage_percent > 95:
                status = "critical"
            elif usage_percent > 85:
                status = "warning"

            self.metrics["disk_usage"] = HealthMetric(
                name="disk_usage",
                status=status,
                value=usage_percent,
                threshold=85.0,
                message=(
                    f"{usage_percent:.1f}% used "
                    f"({usage.used / 1024**3:.1f}GB / {usage.total / 1024**3:.1f}GB)"
                ),
            )
        except Exception as e:
            self.metrics["disk_usage"] = HealthMetric(
                name="disk_usage",
                status="critical",
                value=None,
                message=f"Failed to check disk: {e}",
            )

    async def _check_cpu_usage(self) -> None:
        """Check CPU usage."""
        try:
            # Get CPU usage over 1 second interval
            cpu_percent = psutil.cpu_percent(interval=1)

            status = "healthy"
            if cpu_percent > 95:
                status = "critical"
            elif cpu_percent > 85:
                status = "warning"

            self.metrics["cpu_usage"] = HealthMetric(
                name="cpu_usage",
                status=status,
                value=cpu_percent,
                threshold=85.0,
                message=f"{cpu_percent:.1f}% used",
            )
        except Exception as e:
            self.metrics["cpu_usage"] = HealthMetric(
                name="cpu_usage",
                status="critical",
                value=None,
                message=f"Failed to check CPU: {e}",
            )

    async def _check_file_handles(self) -> None:
        """Check open file handles for current process."""
        try:
            process = psutil.Process()
            open_files = len(process.open_files())

            # Reasonable thresholds for file handles
            status = "healthy"
            if open_files > 500:
                status = "critical"
            elif open_files > 200:
                status = "warning"

            self.metrics["file_handles"] = HealthMetric(
                name="file_handles",
                status=status,
                value=open_files,
                threshold=200,
                message=f"{open_files} open files",
            )
        except Exception as e:
            self.metrics["file_handles"] = HealthMetric(
                name="file_handles",
                status="warning",
                value=None,
                message=f"Failed to check file handles: {e}",
            )

    async def _check_process_health(self) -> None:
        """Check process-specific health metrics."""
        try:
            process = psutil.Process()

            # Check memory leaks by monitoring RSS growth
            memory_info = process.memory_info()
            rss_mb = memory_info.rss / 1024 / 1024

            status = "healthy"
            if rss_mb > 1000:  # 1GB
                status = "critical"
            elif rss_mb > 500:  # 500MB
                status = "warning"

            self.metrics["process_memory"] = HealthMetric(
                name="process_memory",
                status=status,
                value=rss_mb,
                threshold=500,
                message=f"{rss_mb:.1f}MB RSS",
            )

            # Check thread count
            num_threads = process.num_threads()
            status = "healthy"
            if num_threads > 100:
                status = "critical"
            elif num_threads > 50:
                status = "warning"

            self.metrics["thread_count"] = HealthMetric(
                name="thread_count",
                status=status,
                value=num_threads,
                threshold=50,
                message=f"{num_threads} threads",
            )

        except Exception as e:
            self.metrics["process_health"] = HealthMetric(
                name="process_health",
                status="warning",
                value=None,
                message=f"Failed to check process health: {e}",
            )

    async def _run_custom_check(self, name: str, check_func: Callable) -> None:
        """Run a custom health check function."""
        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()

            if isinstance(result, HealthMetric):
                self.metrics[name] = result
            elif isinstance(result, dict):
                self.metrics[name] = HealthMetric(name=name, **result)
            else:
                self.metrics[name] = HealthMetric(
                    name=name, status="healthy", value=result, message=str(result)
                )
        except Exception as e:
            logger.error(f"Custom health check '{name}' failed: {e}")
            raise

    def _determine_overall_status(self) -> str:
        """Determine overall system status from individual metrics."""
        if not self.metrics:
            return "unknown"

        has_critical = any(m.status == "critical" for m in self.metrics.values())
        has_warning = any(m.status == "warning" for m in self.metrics.values())

        if has_critical:
            return "critical"
        elif has_warning:
            return "warning"
        else:
            return "healthy"

    async def _check_alerts(self) -> None:
        """Check for alert conditions and send notifications."""
        current_time = datetime.now()

        for name, metric in self.metrics.items():
            if metric.status in ["warning", "critical"]:
                # Check if we're in cooldown for this alert
                last_alert = self._alert_cooldowns.get(name)
                if last_alert and current_time - last_alert < timedelta(minutes=15):
                    continue

                # Send alert
                await self._send_alert(metric)
                self._alert_cooldowns[name] = current_time

    async def _send_alert(self, metric: HealthMetric) -> None:
        """Send health alert (can be overridden for specific notification systems)."""
        logger.warning(f"Health Alert - {metric.name}: {metric.status} - {metric.message}")

    def get_health_report(self) -> dict[str, Any]:
        """Get a comprehensive health report."""
        overall_status = self._determine_overall_status()

        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "metrics": {},
            "summary": {
                "total_checks": len(self.metrics),
                "healthy": sum(1 for m in self.metrics.values() if m.status == "healthy"),
                "warnings": sum(1 for m in self.metrics.values() if m.status == "warning"),
                "critical": sum(1 for m in self.metrics.values() if m.status == "critical"),
            },
        }

        for name, metric in self.metrics.items():
            report["metrics"][name] = {
                "status": metric.status,
                "value": metric.value,
                "threshold": metric.threshold,
                "message": metric.message,
                "last_check": metric.last_check.isoformat(),
            }

        return report

    async def health_check_endpoint(self) -> dict[str, Any]:
        """Simple health check endpoint for external monitoring."""
        try:
            await self.check_all_health()
            overall_status = self._determine_overall_status()

            return {
                "status": overall_status,
                "timestamp": datetime.now().isoformat(),
                "checks": {
                    name: {"status": metric.status, "message": metric.message}
                    for name, metric in self.metrics.items()
                },
            }
        except Exception as e:
            return {
                "status": "critical",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }


# Global health monitor instance
health_monitor = HealthMonitor()


# Utility functions for easy integration
async def get_system_health() -> SystemHealth:
    """Get current system health status."""
    return await health_monitor.check_all_health()


async def start_health_monitoring(interval: int = 60) -> None:
    """Start health monitoring with specified interval."""
    health_monitor.check_interval = interval
    await health_monitor.start_monitoring()


async def stop_health_monitoring() -> None:
    """Stop health monitoring."""
    await health_monitor.stop_monitoring()


def register_health_check(name: str, check_func: Callable) -> None:
    """Register a custom health check."""
    health_monitor.register_custom_check(name, check_func)
