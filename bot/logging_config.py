#!/usr/bin/env python3
"""
Structured Logging Configuration
Provides structured logging with JSON format and context-aware logging for the Discord bot.
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def __init__(self, service_name: str = "proj-automation-bot"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "guild_id"):
            log_entry["guild_id"] = record.guild_id
        if hasattr(record, "channel_id"):
            log_entry["channel_id"] = record.channel_id
        if hasattr(record, "command"):
            log_entry["command"] = record.command
        if hasattr(record, "duration"):
            log_entry["duration_ms"] = record.duration
        if hasattr(record, "error_type"):
            log_entry["error_type"] = record.error_type
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_entry, ensure_ascii=False)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for development/console output."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human reading."""
        formatted = super().format(record)

        # Add context if available
        context_parts = []
        if hasattr(record, "user_id"):
            context_parts.append(f"user:{record.user_id}")
        if hasattr(record, "command"):
            context_parts.append(f"cmd:{record.command}")
        if hasattr(record, "duration"):
            context_parts.append(f"took:{record.duration}ms")

        if context_parts:
            formatted += f" [{', '.join(context_parts)}]"

        return formatted


def setup_logging(
    level: str = "INFO",
    structured: bool = False,
    log_file: str | None = None,
    service_name: str = "proj-automation-bot",
) -> logging.Logger:
    """
    Set up structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        structured: Whether to use JSON structured logging
        log_file: Optional log file path
        service_name: Service name for structured logs

    Returns:
        Configured logger instance
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Choose formatter
    if structured:
        formatter = StructuredFormatter(service_name)
    else:
        formatter = HumanReadableFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, level.upper()))
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, level.upper()))
        root_logger.addHandler(file_handler)

    # Set up specific logger for this app
    app_logger = logging.getLogger(service_name)

    return app_logger


class LogContext:
    """Context manager for adding structured logging context."""

    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.original_factory = logging.getLogRecordFactory()

    def __enter__(self):
        """Enter context and modify log record factory."""

        def record_factory(*args, **kwargs):
            record = self.original_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original factory."""
        logging.setLogRecordFactory(self.original_factory)


def log_command_execution(logger: logging.Logger):
    """
    Decorator for logging Discord command execution.

    Args:
        logger: Logger instance to use

    Usage:
        @log_command_execution(logger)
        async def my_command(interaction, ...):
            ...
    """

    def decorator(func):
        import functools

        # Preserve the original function signature
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # First argument should be interaction
            interaction = args[0] if args else None
            if not hasattr(interaction, "user"):
                # Not a Discord interaction, just call the function
                return await func(*args, **kwargs)

            start_time = time.time()
            command_name = getattr(interaction.command, "name", "unknown")

            with LogContext(
                logger,
                user_id=interaction.user.id,
                guild_id=interaction.guild.id if interaction.guild else None,
                channel_id=interaction.channel.id if interaction.channel else None,
                command=command_name,
                request_id=f"{interaction.user.id}-{int(start_time)}",
            ):
                logger.info(
                    f"Command '{command_name}' started",
                    extra={"event_type": "command_start"},
                )

                try:
                    result = await func(*args, **kwargs)

                    duration = int((time.time() - start_time) * 1000)
                    logger.info(
                        f"Command '{command_name}' completed successfully",
                        extra={"event_type": "command_success", "duration": duration},
                    )

                    return result

                except Exception as e:
                    duration = int((time.time() - start_time) * 1000)
                    logger.error(
                        f"Command '{command_name}' failed: {e}",
                        extra={
                            "event_type": "command_error",
                            "duration": duration,
                            "error_type": type(e).__name__,
                        },
                        exc_info=True,
                    )
                    raise

        return wrapper

    return decorator


def log_async_operation(logger: logging.Logger, operation_name: str):
    """
    Decorator for logging async operations (like API calls).

    Args:
        logger: Logger instance to use
        operation_name: Name of the operation being logged

    Usage:
        @log_async_operation(logger, "openai_api_call")
        async def call_openai(...):
            ...
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            logger.debug(
                f"Starting {operation_name}",
                extra={"event_type": "operation_start", "operation": operation_name},
            )

            try:
                result = await func(*args, **kwargs)

                duration = int((time.time() - start_time) * 1000)
                logger.debug(
                    f"Completed {operation_name}",
                    extra={
                        "event_type": "operation_success",
                        "operation": operation_name,
                        "duration": duration,
                    },
                )

                return result

            except Exception as e:
                duration = int((time.time() - start_time) * 1000)
                logger.error(
                    f"Failed {operation_name}: {e}",
                    extra={
                        "event_type": "operation_error",
                        "operation": operation_name,
                        "duration": duration,
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


# Convenience functions for common logging patterns
def log_user_action(logger: logging.Logger, user_id: int, action: str, **extra):
    """Log a user action with structured context."""
    with LogContext(logger, user_id=user_id, event_type="user_action"):
        logger.info(f"User action: {action}", extra=extra)


def log_bot_event(logger: logging.Logger, event: str, **extra):
    """Log a bot event with structured context."""
    logger.info(f"Bot event: {event}", extra={"event_type": "bot_event", **extra})


def log_api_call(
    logger: logging.Logger,
    api: str,
    endpoint: str,
    success: bool,
    duration_ms: int = None,
    **extra,
):
    """Log an API call with structured context."""
    logger.info(
        f"API call to {api} {endpoint} {'succeeded' if success else 'failed'}",
        extra={
            "event_type": "api_call",
            "api": api,
            "endpoint": endpoint,
            "success": success,
            "duration": duration_ms,
            **extra,
        },
    )
