#!/usr/bin/env python3
"""
Resource Management Module for Project Automation

Provides resource pooling, cleanup, and lifecycle management.
"""

import asyncio
import gc
import logging
import os
import tempfile
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Optional,
    TypeVar,
)

import aiohttp


logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ResourceStats:
    """Statistics for resource usage."""

    created_count: int = 0
    active_count: int = 0
    max_active: int = 0
    cleanup_count: int = 0
    error_count: int = 0
    last_cleanup: Optional[datetime] = None


class ResourceManager(Generic[T]):
    """Generic resource manager with lifecycle management."""

    def __init__(
        self,
        name: str,
        max_resources: int = 100,
        cleanup_interval: int = 300,  # 5 minutes
        max_idle_time: int = 600,  # 10 minutes
    ):
        """Initialize resource manager."""
        self.name = name
        self.max_resources = max_resources
        self.cleanup_interval = cleanup_interval
        self.max_idle_time = max_idle_time

        self._resources: Dict[str, T] = {}
        self._resource_metadata: Dict[str, Dict[str, Any]] = {}
        self._stats = ResourceStats()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start resource manager."""
        if self._cleanup_task and not self._cleanup_task.done():
            return

        logger.info(f"Starting resource manager: {self.name}")
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop resource manager and cleanup all resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._cleanup_task

        await self.cleanup_all()
        logger.info(f"Stopped resource manager: {self.name}")

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup loop."""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_expired()
        except asyncio.CancelledError:
            logger.info(f"Resource manager cleanup loop cancelled: {self.name}")
        except Exception as e:
            logger.error(f"Resource manager cleanup loop error: {e}", exc_info=True)

    async def get_resource(self, key: str, factory: Callable[[], T]) -> T:
        """Get or create a resource."""
        async with self._lock:
            if key in self._resources:
                # Update last accessed time
                self._resource_metadata[key]["last_accessed"] = datetime.now()
                return self._resources[key]

            # Check resource limits
            if len(self._resources) >= self.max_resources:
                await self._cleanup_oldest()

            # Create new resource
            try:
                resource = (
                    factory()
                    if not asyncio.iscoroutinefunction(factory)
                    else await factory()
                )
                self._resources[key] = resource
                self._resource_metadata[key] = {
                    "created_at": datetime.now(),
                    "last_accessed": datetime.now(),
                    "access_count": 0,
                }

                self._stats.created_count += 1
                self._stats.active_count += 1
                self._stats.max_active = max(
                    self._stats.max_active, self._stats.active_count
                )

                logger.debug(f"Created resource '{key}' in manager '{self.name}'")
                return resource

            except Exception as e:
                self._stats.error_count += 1
                logger.error(f"Failed to create resource '{key}': {e}")
                raise

    async def release_resource(self, key: str) -> None:
        """Release a specific resource."""
        async with self._lock:
            if key in self._resources:
                resource = self._resources.pop(key)
                metadata = self._resource_metadata.pop(key, {})

                await self._cleanup_resource(resource)
                self._stats.active_count -= 1
                self._stats.cleanup_count += 1

                logger.debug(f"Released resource '{key}' from manager '{self.name}'")

    async def cleanup_expired(self) -> None:
        """Cleanup expired resources."""
        if not self._resources:
            return

        async with self._lock:
            current_time = datetime.now()
            expired_keys = []

            for key, metadata in self._resource_metadata.items():
                last_accessed = metadata.get("last_accessed", current_time)
                if (current_time - last_accessed).total_seconds() > self.max_idle_time:
                    expired_keys.append(key)

            for key in expired_keys:
                resource = self._resources.pop(key, None)
                if resource:
                    await self._cleanup_resource(resource)
                self._resource_metadata.pop(key, None)
                self._stats.active_count -= 1
                self._stats.cleanup_count += 1

            if expired_keys:
                logger.info(
                    f"Cleaned up {len(expired_keys)} expired resources in '{self.name}'"
                )

            self._stats.last_cleanup = current_time

    async def _cleanup_oldest(self) -> None:
        """Cleanup the oldest resource to make room for new ones."""
        if not self._resources:
            return

        # Find oldest resource by last accessed time
        oldest_key = min(
            self._resource_metadata.keys(),
            key=lambda k: self._resource_metadata[k].get("last_accessed", datetime.min),
        )

        resource = self._resources.pop(oldest_key)
        self._resource_metadata.pop(oldest_key)

        await self._cleanup_resource(resource)
        self._stats.active_count -= 1
        self._stats.cleanup_count += 1

        logger.debug(f"Cleaned up oldest resource '{oldest_key}' from '{self.name}'")

    async def cleanup_all(self) -> None:
        """Cleanup all resources."""
        async with self._lock:
            for resource in self._resources.values():
                await self._cleanup_resource(resource)

            count = len(self._resources)
            self._resources.clear()
            self._resource_metadata.clear()
            self._stats.active_count = 0
            self._stats.cleanup_count += count

            if count > 0:
                logger.info(f"Cleaned up all {count} resources in '{self.name}'")

    async def _cleanup_resource(self, resource: T) -> None:
        """Cleanup a specific resource."""
        try:
            # Try to close the resource if it has a close method
            if hasattr(resource, "close"):
                if asyncio.iscoroutinefunction(resource.close):
                    await resource.close()
                else:
                    resource.close()
            elif hasattr(resource, "__aexit__"):
                await resource.__aexit__(None, None, None)
            elif hasattr(resource, "__exit__"):
                resource.__exit__(None, None, None)

        except Exception as e:
            logger.warning(f"Error cleaning up resource: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get resource manager statistics."""
        return {
            "name": self.name,
            "active_count": self._stats.active_count,
            "max_active": self._stats.max_active,
            "created_count": self._stats.created_count,
            "cleanup_count": self._stats.cleanup_count,
            "error_count": self._stats.error_count,
            "last_cleanup": self._stats.last_cleanup.isoformat()
            if self._stats.last_cleanup
            else None,
            "max_resources": self.max_resources,
            "cleanup_interval": self.cleanup_interval,
            "max_idle_time": self.max_idle_time,
        }


class FileManager:
    """Manages temporary files and cleanup."""

    def __init__(self, max_files: int = 1000, max_age_hours: int = 24):
        """Initialize file manager."""
        self.max_files = max_files
        self.max_age_hours = max_age_hours
        self._temp_files: Dict[str, Path] = {}
        self._file_metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def temporary_file(
        self, suffix: str = ".tmp", prefix: str = "automation_"
    ) -> Path:
        """Create a temporary file with automatic cleanup."""
        temp_file = None
        file_id = None

        try:
            # Create temporary file
            fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            os.close(fd)  # Close file descriptor, keep path
            temp_file = Path(temp_path)

            file_id = str(temp_file)

            async with self._lock:
                self._temp_files[file_id] = temp_file
                self._file_metadata[file_id] = {
                    "created_at": datetime.now(),
                    "suffix": suffix,
                    "prefix": prefix,
                }

            logger.debug(f"Created temporary file: {temp_file}")
            yield temp_file

        finally:
            # Cleanup
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary file {temp_file}: {e}")

            if file_id:
                async with self._lock:
                    self._temp_files.pop(file_id, None)
                    self._file_metadata.pop(file_id, None)

    async def cleanup_old_files(self) -> None:
        """Cleanup old temporary files."""
        current_time = datetime.now()
        max_age = timedelta(hours=self.max_age_hours)

        async with self._lock:
            old_files = []

            for file_id, metadata in self._file_metadata.items():
                created_at = metadata.get("created_at", current_time)
                if current_time - created_at > max_age:
                    old_files.append(file_id)

            for file_id in old_files:
                temp_file = self._temp_files.pop(file_id, None)
                if temp_file and temp_file.exists():
                    try:
                        temp_file.unlink()
                        logger.debug(f"Cleaned up old temporary file: {temp_file}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup old file {temp_file}: {e}")

                self._file_metadata.pop(file_id, None)

            if old_files:
                logger.info(f"Cleaned up {len(old_files)} old temporary files")

    async def get_file_stats(self) -> Dict[str, Any]:
        """Get file manager statistics."""
        async with self._lock:
            total_size = 0
            for temp_file in self._temp_files.values():
                try:
                    if temp_file.exists():
                        total_size += temp_file.stat().st_size
                except Exception:
                    pass

            return {
                "active_files": len(self._temp_files),
                "total_size_bytes": total_size,
                "total_size_mb": total_size / 1024 / 1024,
                "max_files": self.max_files,
                "max_age_hours": self.max_age_hours,
            }


class HTTPSessionManager:
    """Manages HTTP sessions with connection pooling."""

    def __init__(self, max_sessions: int = 10):
        """Initialize HTTP session manager."""
        self.max_sessions = max_sessions
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
        self._session_metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_session(
        self, key: str = "default", **session_kwargs
    ) -> aiohttp.ClientSession:
        """Get or create an HTTP session."""
        async with self._lock:
            if key in self._sessions:
                session = self._sessions[key]
                if not session.closed:
                    self._session_metadata[key]["last_used"] = datetime.now()
                    return session
                else:
                    # Session is closed, remove it
                    del self._sessions[key]
                    del self._session_metadata[key]

            # Create new session
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )

            timeout = aiohttp.ClientTimeout(total=30, connect=10)

            session = aiohttp.ClientSession(
                connector=connector, timeout=timeout, **session_kwargs
            )

            self._sessions[key] = session
            self._session_metadata[key] = {
                "created_at": datetime.now(),
                "last_used": datetime.now(),
                "request_count": 0,
            }

            logger.debug(f"Created HTTP session: {key}")
            return session

    async def close_session(self, key: str) -> None:
        """Close a specific HTTP session."""
        async with self._lock:
            session = self._sessions.pop(key, None)
            if session and not session.closed:
                await session.close()
                logger.debug(f"Closed HTTP session: {key}")

            self._session_metadata.pop(key, None)

    async def close_all_sessions(self) -> None:
        """Close all HTTP sessions."""
        async with self._lock:
            for session in self._sessions.values():
                if not session.closed:
                    await session.close()

            count = len(self._sessions)
            self._sessions.clear()
            self._session_metadata.clear()

            if count > 0:
                logger.info(f"Closed all {count} HTTP sessions")

    def get_session_stats(self) -> Dict[str, Any]:
        """Get HTTP session statistics."""
        active_sessions = sum(1 for s in self._sessions.values() if not s.closed)

        return {
            "active_sessions": active_sessions,
            "total_sessions": len(self._sessions),
            "max_sessions": self.max_sessions,
            "sessions": {
                key: {
                    "created_at": meta.get("created_at", "").isoformat()
                    if meta.get("created_at")
                    else "",
                    "last_used": meta.get("last_used", "").isoformat()
                    if meta.get("last_used")
                    else "",
                    "closed": self._sessions[key].closed
                    if key in self._sessions
                    else True,
                }
                for key, meta in self._session_metadata.items()
            },
        }


class MemoryManager:
    """Manages memory usage and cleanup."""

    def __init__(self, gc_threshold_mb: int = 500):
        """Initialize memory manager."""
        self.gc_threshold_mb = gc_threshold_mb
        self._objects_tracked = 0

    async def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return statistics."""
        logger.debug("Forcing garbage collection")

        # Force garbage collection
        collected = [gc.collect(generation) for generation in range(3)]
        total_collected = sum(collected)

        # Get memory info
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        stats = {
            "collected_objects": total_collected,
            "collections_by_generation": collected,
            "memory_rss_mb": memory_info.rss / 1024 / 1024,
            "memory_vms_mb": memory_info.vms / 1024 / 1024,
            "gc_counts": gc.get_count(),
            "gc_stats": gc.get_stats(),
        }

        logger.info(
            f"GC collected {total_collected} objects, RSS: {stats['memory_rss_mb']:.1f}MB"
        )
        return stats

    async def check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure."""
        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            if memory_mb > self.gc_threshold_mb:
                logger.warning(
                    f"Memory pressure detected: {memory_mb:.1f}MB > {self.gc_threshold_mb}MB"
                )
                await self.force_garbage_collection()
                return True

            return False
        except Exception as e:
            logger.warning(f"Failed to check memory pressure: {e}")
            return False


# Global resource managers
file_manager = FileManager()
http_session_manager = HTTPSessionManager()
memory_manager = MemoryManager()


# Convenience functions
@asynccontextmanager
async def temporary_file(suffix: str = ".tmp", prefix: str = "automation_") -> Path:
    """Create a temporary file with automatic cleanup."""
    async with file_manager.temporary_file(suffix=suffix, prefix=prefix) as temp_file:
        yield temp_file


async def get_http_session(key: str = "default", **kwargs) -> aiohttp.ClientSession:
    """Get a managed HTTP session."""
    return await http_session_manager.get_session(key, **kwargs)


async def cleanup_resources() -> None:
    """Cleanup all managed resources."""
    await file_manager.cleanup_old_files()
    await http_session_manager.close_all_sessions()
    await memory_manager.force_garbage_collection()


async def get_resource_stats() -> Dict[str, Any]:
    """Get statistics for all resource managers."""
    return {
        "files": await file_manager.get_file_stats(),
        "http_sessions": http_session_manager.get_session_stats(),
        "memory": {
            "gc_threshold_mb": memory_manager.gc_threshold_mb,
            "gc_counts": gc.get_count(),
        },
    }
