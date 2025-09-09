#!/usr/bin/env python3
"""
Thread Pool Manager
Manages thread pools for offloading CPU-intensive tasks from the main asyncio event loop.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from threading import Lock
from typing import Any, Callable, Coroutine, Optional, TypeVar


logger = logging.getLogger(__name__)
T = TypeVar("T")


class ThreadPoolManager:
    """Manages thread pools for different types of background work."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._executor: Optional[ThreadPoolExecutor] = None
        self._lock = Lock()
        self._active_tasks = 0

    def _ensure_executor(self):
        """Ensure the thread pool executor is created."""
        if self._executor is None or self._executor._shutdown:
            with self._lock:
                if self._executor is None or self._executor._shutdown:
                    self._executor = ThreadPoolExecutor(
                        max_workers=self.max_workers, thread_name_prefix="bot-worker"
                    )
                    logger.info(f"Created thread pool with {self.max_workers} workers")

    async def run_in_thread(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Run a synchronous function in the thread pool.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function execution
        """
        self._ensure_executor()

        loop = asyncio.get_event_loop()
        self._active_tasks += 1

        try:
            start_time = time.time()
            logger.debug(f"Starting thread pool task: {func.__name__}")

            result = await loop.run_in_executor(self._executor, func, *args, **kwargs)

            duration = int((time.time() - start_time) * 1000)
            logger.debug(f"Thread pool task completed: {func.__name__} ({duration}ms)")

            return result

        except Exception as e:
            logger.error(f"Thread pool task failed: {func.__name__}: {e}")
            raise
        finally:
            self._active_tasks -= 1

    async def run_multiple(self, tasks: list) -> list:
        """
        Run multiple tasks concurrently in the thread pool.

        Args:
            tasks: List of (func, args, kwargs) tuples

        Returns:
            List of results in the same order as input tasks
        """
        self._ensure_executor()

        if not tasks:
            return []

        loop = asyncio.get_event_loop()
        futures = []

        for func, args, kwargs in tasks:
            future = loop.run_in_executor(self._executor, func, *args, **kwargs)
            futures.append(future)

        self._active_tasks += len(futures)

        try:
            results = await asyncio.gather(*futures)
            return results
        finally:
            self._active_tasks -= len(futures)

    def shutdown(self, wait: bool = True):
        """
        Shutdown the thread pool.

        Args:
            wait: Whether to wait for running tasks to complete
        """
        if self._executor and not self._executor._shutdown:
            logger.info("Shutting down thread pool")
            self._executor.shutdown(wait=wait)

    @property
    def active_tasks(self) -> int:
        """Get the number of currently active tasks."""
        return self._active_tasks

    @property
    def is_healthy(self) -> bool:
        """Check if the thread pool is healthy."""
        return (
            self._executor is not None
            and not self._executor._shutdown
            and self._active_tasks < self.max_workers * 2  # Allow some queuing
        )


# Global thread pool manager instance
thread_pool = ThreadPoolManager()


def run_in_thread(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Decorator to run a synchronous function in the thread pool.

    Args:
        func: Synchronous function to wrap

    Returns:
        Async wrapper function

    Usage:
        @run_in_thread
        def cpu_intensive_task(data):
            # Heavy computation here
            return result

        # Use in async context:
        result = await cpu_intensive_task(data)
    """

    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        return await thread_pool.run_in_thread(func, *args, **kwargs)

    return wrapper


# Common CPU-intensive tasks that can be offloaded to thread pool


@run_in_thread
def process_large_text(text: str, operation: str = "word_count") -> dict:
    """
    Process large text in a thread pool.

    Args:
        text: Text to process
        operation: Type of processing to perform

    Returns:
        Dict with processing results
    """
    import re
    from collections import Counter

    if operation == "word_count":
        words = re.findall(r"\b\w+\b", text.lower())
        return {
            "word_count": len(words),
            "unique_words": len(set(words)),
            "most_common": Counter(words).most_common(10),
        }
    elif operation == "analyze":
        lines = text.split("\n")
        words = re.findall(r"\b\w+\b", text.lower())
        sentences = re.split(r"[.!?]+", text)

        return {
            "characters": len(text),
            "words": len(words),
            "lines": len(lines),
            "sentences": len([s for s in sentences if s.strip()]),
            "avg_words_per_sentence": len(words) / max(1, len(sentences)),
            "reading_time_minutes": len(words) / 200,  # Average reading speed
        }
    else:
        return {"error": f"Unknown operation: {operation}"}


@run_in_thread
def format_markdown_content(content: str, style: str = "default") -> str:
    """
    Format markdown content with various styles.

    Args:
        content: Markdown content to format
        style: Formatting style to apply

    Returns:
        Formatted content
    """
    import re

    if style == "compact":
        # Remove extra whitespace, make more compact
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)  # Max 2 consecutive newlines
        content = re.sub(r"[ \t]+", " ", content)  # Normalize spaces
        return content.strip()

    elif style == "expanded":
        # Add more whitespace for readability
        content = re.sub(
            r"^(#{1,6}\s)", r"\n\1", content, flags=re.MULTILINE
        )  # Space before headers
        content = re.sub(r"\n\n", "\n\n\n", content)  # Triple spacing
        return content.strip()

    else:
        return content


@run_in_thread
def parse_discord_messages(messages: list) -> dict:
    """
    Parse and analyze Discord messages in thread pool.

    Args:
        messages: List of Discord message data

    Returns:
        Analysis results
    """
    import re
    from collections import Counter, defaultdict

    # Initialize analysis data
    user_stats = defaultdict(
        lambda: {
            "message_count": 0,
            "total_length": 0,
            "reactions_received": 0,
            "mentions_made": 0,
            "links_shared": 0,
        }
    )

    hourly_activity = defaultdict(int)
    emoji_usage = Counter()
    Counter()

    # Process each message
    for msg in messages:
        author = msg.get("author", "Unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp")
        reactions = msg.get("reactions", 0)

        # Update user stats
        user_stats[author]["message_count"] += 1
        user_stats[author]["total_length"] += len(content)
        user_stats[author]["reactions_received"] += reactions

        # Count mentions
        mentions = len(re.findall(r"<@!?\d+>", content))
        user_stats[author]["mentions_made"] += mentions

        # Count links
        links = len(re.findall(r"https?://\S+", content))
        user_stats[author]["links_shared"] += links

        # Extract emojis
        emojis = re.findall(
            r"<:\w+:\d+>|[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]",
            content,
        )
        emoji_usage.update(emojis)

        # Activity by hour
        if timestamp:
            try:
                hour = timestamp.hour
                hourly_activity[hour] += 1
            except Exception:
                pass

    # Calculate averages and insights
    total_messages = sum(stats["message_count"] for stats in user_stats.values())

    return {
        "user_stats": dict(user_stats),
        "total_messages": total_messages,
        "unique_users": len(user_stats),
        "hourly_activity": dict(hourly_activity),
        "top_emojis": emoji_usage.most_common(10),
        "most_active_hours": sorted(
            hourly_activity.items(), key=lambda x: x[1], reverse=True
        )[:5],
        "avg_message_length": sum(
            stats["total_length"] for stats in user_stats.values()
        )
        / max(1, total_messages),
    }


async def shutdown_thread_pool():
    """Gracefully shutdown the global thread pool."""
    logger.info("Shutting down thread pool manager")
    thread_pool.shutdown(wait=True)
