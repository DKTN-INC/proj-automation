#!/usr/bin/env python3
"""
Integration Tests for Reliability Features

Tests the reliability and resiliency improvements across the automation platform.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict


# Add bot directory to path
sys.path.insert(0, str(Path(__file__).parent / "bot"))

try:
    from circuit_breaker import CircuitBreaker, CircuitBreakerError, CircuitConfig
    from health_monitor import HealthMonitor, get_system_health
    from openai_wrapper import OpenAIWrapper
    from reliability_config import get_reliability_config
    from resource_manager import (
        FileManager,
        HTTPSessionManager,
        MemoryManager,
        cleanup_resources,
        get_http_session,
        temporary_file,
    )
    from retry_utils import (
        ExponentialBackoffStrategy,
        RetryHandler,
        create_http_retry_strategy,
        retry_async,
    )
except ImportError as e:
    print(f"Error importing reliability modules: {e}")
    print("Make sure you're running from the repository root")
    sys.exit(1)


# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ReliabilityTester:
    """Test suite for reliability features."""

    def __init__(self):
        """Initialize the reliability tester."""
        self.results: Dict[str, Dict[str, Any]] = {}

    async def run_all_tests(self) -> bool:
        """Run all reliability tests."""
        logger.info("Starting reliability integration tests...")

        tests = [
            ("health_monitoring", self.test_health_monitoring),
            ("circuit_breaker", self.test_circuit_breaker),
            ("resource_management", self.test_resource_management),
            ("retry_mechanisms", self.test_retry_mechanisms),
            ("configuration", self.test_configuration),
            ("openai_wrapper", self.test_openai_wrapper_reliability),
            ("end_to_end", self.test_end_to_end_reliability),
        ]

        all_passed = True

        for test_name, test_func in tests:
            logger.info(f"Running test: {test_name}")
            try:
                result = await test_func()
                self.results[test_name] = {
                    "status": "PASSED" if result else "FAILED",
                    "details": result if isinstance(result, dict) else {},
                }
                if not result:
                    all_passed = False
                    logger.error(f"Test {test_name} FAILED")
                else:
                    logger.info(f"Test {test_name} PASSED")
            except Exception as e:
                logger.error(f"Test {test_name} ERROR: {e}", exc_info=True)
                self.results[test_name] = {
                    "status": "ERROR",
                    "details": {"error": str(e)},
                }
                all_passed = False

        return all_passed

    async def test_health_monitoring(self) -> bool:
        """Test health monitoring functionality."""
        try:
            # Test basic health check
            health_monitor = HealthMonitor(check_interval=1)
            health_status = await health_monitor.check_all_health()

            # Verify health status structure
            assert hasattr(health_status, "overall_status")
            assert hasattr(health_status, "metrics")
            assert health_status.overall_status in [
                "healthy",
                "warning",
                "critical",
                "unknown",
            ]

            # Check that basic metrics are present
            expected_metrics = [
                "memory_usage",
                "disk_usage",
                "cpu_usage",
                "file_handles",
                "process_memory",
            ]
            for metric in expected_metrics:
                assert metric in health_status.metrics, f"Missing metric: {metric}"

            # Test custom health check registration
            def custom_check():
                return {
                    "status": "healthy",
                    "value": 100,
                    "message": "Custom test check",
                }

            health_monitor.register_custom_check("test_check", custom_check)
            health_status = await health_monitor.check_all_health()
            assert "test_check" in health_status.metrics

            # Test health monitoring start/stop
            await health_monitor.start_monitoring()
            await asyncio.sleep(2)  # Let it run for a bit
            await health_monitor.stop_monitoring()

            logger.info("Health monitoring test completed successfully")
            return True

        except Exception as e:
            logger.error(f"Health monitoring test failed: {e}")
            return False

    async def test_circuit_breaker(self) -> bool:
        """Test circuit breaker functionality."""
        try:
            # Test basic circuit breaker
            config = CircuitConfig(
                failure_threshold=2,
                recovery_timeout=1.0,
                success_threshold=1,
                timeout=5.0,
            )

            circuit_breaker = CircuitBreaker("test_service", config)

            # Test function that always fails
            def failing_function():
                raise ConnectionError("Test failure")

            # Test function that succeeds
            def succeeding_function():
                return "success"

            # Test normal failure handling
            try:
                await circuit_breaker.call(failing_function)
                assert False, "Should have raised exception"
            except ConnectionError:
                pass  # Expected

            # Trigger circuit breaker opening
            try:
                await circuit_breaker.call(failing_function)
                assert False, "Should have raised exception"
            except ConnectionError:
                pass  # Expected, circuit should open now

            # Next call should fail fast
            try:
                await circuit_breaker.call(failing_function)
                assert False, "Should have raised CircuitBreakerError"
            except CircuitBreakerError:
                pass  # Expected

            # Test circuit breaker stats
            stats = circuit_breaker.get_stats()
            assert stats["state"] == "open"
            assert stats["total_failures"] >= 2

            # Wait for recovery timeout and test half-open state
            await asyncio.sleep(1.5)

            # Should transition to half-open and allow one call
            result = await circuit_breaker.call(succeeding_function)
            assert result == "success"

            # Circuit should be closed now
            stats = circuit_breaker.get_stats()
            assert stats["state"] == "closed"

            logger.info("Circuit breaker test completed successfully")
            return True

        except Exception as e:
            logger.error(f"Circuit breaker test failed: {e}")
            return False

    async def test_resource_management(self) -> bool:
        """Test resource management functionality."""
        try:
            # Test file manager
            file_manager = FileManager(max_files=5, max_age_hours=1)

            # Test temporary file creation and cleanup
            async with temporary_file(
                suffix=".test", prefix="reliability_test_"
            ) as temp_file:
                assert temp_file.exists()

                # Write some data
                temp_file.write_text("test data")
                assert temp_file.read_text() == "test data"

            # File should be cleaned up after context exit
            assert not temp_file.exists()

            # Test HTTP session manager
            session_manager = HTTPSessionManager(max_sessions=3)

            session1 = await session_manager.get_session("test1")
            session2 = await session_manager.get_session("test2")

            assert not session1.closed
            assert not session2.closed

            # Test session cleanup
            await session_manager.close_session("test1")
            assert session1.closed

            await session_manager.close_all_sessions()
            assert session2.closed

            # Test memory manager
            memory_manager = MemoryManager(gc_threshold_mb=10)
            gc_stats = await memory_manager.force_garbage_collection()

            assert "collected_objects" in gc_stats
            assert "memory_rss_mb" in gc_stats

            # Test global cleanup
            await cleanup_resources()

            logger.info("Resource management test completed successfully")
            return True

        except Exception as e:
            logger.error(f"Resource management test failed: {e}")
            return False

    async def test_retry_mechanisms(self) -> bool:
        """Test retry mechanisms."""
        try:
            # Test exponential backoff strategy
            strategy = ExponentialBackoffStrategy(
                base_delay=0.1,
                max_delay=1.0,
                max_retries=3,
                retryable_exceptions=(ValueError,),
            )

            handler = RetryHandler(strategy)

            # Test function that fails twice then succeeds
            call_count = 0

            def flaky_function():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise ValueError(f"Attempt {call_count} failed")
                return f"Success on attempt {call_count}"

            # Test successful retry
            result = await handler.execute_async(flaky_function)
            assert result == "Success on attempt 3"
            assert call_count == 3

            # Test retry statistics
            stats = handler.get_stats()
            assert stats["total_attempts"] == 3
            assert stats["successful_attempts"] == 1
            assert stats["failed_attempts"] == 2

            # Test decorator
            call_count = 0

            @retry_async(max_retries=2, base_delay=0.1)
            async def decorated_function():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ConnectionError("First attempt failed")
                return "Decorated success"

            result = await decorated_function()
            assert result == "Decorated success"
            assert call_count == 2

            # Test HTTP retry strategy
            http_strategy = create_http_retry_strategy()
            assert http_strategy.max_retries == 3
            assert http_strategy.base_delay == 1.0

            logger.info("Retry mechanisms test completed successfully")
            return True

        except Exception as e:
            logger.error(f"Retry mechanisms test failed: {e}")
            return False

    async def test_configuration(self) -> bool:
        """Test reliability configuration."""
        try:
            config = get_reliability_config()

            # Test configuration access
            assert hasattr(config, "circuit_breaker")
            assert hasattr(config, "health_monitor")
            assert hasattr(config, "resource_manager")
            assert hasattr(config, "retry")
            assert hasattr(config, "rate_limit")

            # Test configuration validation
            is_valid, issues = config.validate_config()
            if not is_valid:
                logger.warning(f"Configuration issues: {issues}")

            # Test configuration dictionary
            config_dict = config.get_config_dict()
            assert "circuit_breaker" in config_dict
            assert "health_monitor" in config_dict

            # Test specific configuration values
            cb_config = config.circuit_breaker
            assert cb_config.failure_threshold > 0
            assert cb_config.recovery_timeout > 0

            hm_config = config.health_monitor
            assert hm_config.check_interval > 0
            assert 0 < hm_config.cpu_threshold_percent <= 100

            logger.info("Configuration test completed successfully")
            return True

        except Exception as e:
            logger.error(f"Configuration test failed: {e}")
            return False

    async def test_openai_wrapper_reliability(self) -> bool:
        """Test OpenAI wrapper reliability features."""
        try:
            # Test OpenAI wrapper with circuit breaker (without real API key)
            wrapper = OpenAIWrapper(
                api_key="test-key-not-real",
                enable_circuit_breaker=True,
                rate_limit_requests_per_minute=10,
            )

            # Test statistics
            stats = wrapper.get_stats()
            assert "total_requests" in stats
            assert "circuit_breaker_enabled" in stats
            assert stats["circuit_breaker_enabled"] is True

            # Test health status
            health_status = await wrapper.get_health_status()
            assert "status" in health_status
            assert "stats" in health_status

            # The circuit breaker should be available
            assert wrapper._circuit_breaker is not None

            await wrapper.close()

            logger.info("OpenAI wrapper reliability test completed successfully")
            return True

        except Exception as e:
            logger.error(f"OpenAI wrapper reliability test failed: {e}")
            return False

    async def test_end_to_end_reliability(self) -> bool:
        """Test end-to-end reliability scenario."""
        try:
            # Simulate a complex operation with multiple reliability features

            # 1. Health check
            health_status = await get_system_health()
            if health_status.overall_status == "critical":
                logger.warning("System health is critical, proceeding with caution")

            # 2. Resource management
            async with temporary_file(suffix=".e2e") as temp_file:
                # 3. Retry mechanism for file operation
                @retry_async(max_retries=3, base_delay=0.1)
                async def write_file_operation():
                    temp_file.write_text("End-to-end test data")
                    return temp_file.read_text()

                content = await write_file_operation()
                assert content == "End-to-end test data"

            # 4. Circuit breaker for external service simulation
            circuit_breaker = CircuitBreaker("e2e_service")

            async def reliable_operation():
                # Simulate some work
                await asyncio.sleep(0.1)
                return {"status": "success", "data": "test_result"}

            result = await circuit_breaker.call(reliable_operation)
            assert result["status"] == "success"

            # 5. Resource cleanup
            await cleanup_resources()

            logger.info("End-to-end reliability test completed successfully")
            return True

        except Exception as e:
            logger.error(f"End-to-end reliability test failed: {e}")
            return False

    def print_results(self) -> None:
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("RELIABILITY INTEGRATION TEST RESULTS")
        print("=" * 60)

        passed = sum(1 for r in self.results.values() if r["status"] == "PASSED")
        failed = sum(1 for r in self.results.values() if r["status"] == "FAILED")
        errors = sum(1 for r in self.results.values() if r["status"] == "ERROR")
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print(f"Success Rate: {(passed / total) * 100:.1f}%" if total > 0 else "N/A")

        print("\nDetailed Results:")
        for test_name, result in self.results.items():
            status = result["status"]
            emoji = "✅" if status == "PASSED" else "❌" if status == "FAILED" else "⚠️"
            print(f"  {emoji} {test_name}: {status}")

            if result["details"] and status != "PASSED":
                for key, value in result["details"].items():
                    print(f"    {key}: {value}")

        print("=" * 60)


async def main():
    """Main test function."""
    tester = ReliabilityTester()

    print("Starting Reliability Integration Tests...")
    print("This will test all reliability and resiliency features.")

    success = await tester.run_all_tests()
    tester.print_results()

    if success:
        print("\n🎉 All reliability tests PASSED!")
        return 0
    else:
        print("\n💥 Some reliability tests FAILED!")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test execution failed: {e}")
        sys.exit(1)
