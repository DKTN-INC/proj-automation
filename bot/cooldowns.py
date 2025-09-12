#!/usr/bin/env python3
"""
Cooldown Manager
Implements per-user cooldowns for Discord slash commands to prevent spam and rate limiting.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, Optional


# Import discord for type hints
try:
    import discord
except ImportError:
    discord = None


logger = logging.getLogger(__name__)


class CooldownManager:
    """Manages per-user cooldowns for Discord commands."""

    def __init__(self):
        self._cooldowns: Dict[str, Dict[int, float]] = defaultdict(
            dict
        )  # command -> user_id -> next_allowed_time
        self._cleanup_task: Optional[asyncio.Task] = None

    def _start_cleanup_task(self):
        """Start the background cleanup task."""
        try:
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_expired())
        except RuntimeError:
            # No event loop running, will start later
            pass

    async def _cleanup_expired(self):
        """Background task to clean up expired cooldowns."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                current_time = time.time()

                for command in self._cooldowns.keys():
                    expired_users = [
                        user_id
                        for user_id, next_time in self._cooldowns[command].items()
                        if current_time >= next_time
                    ]

                    for user_id in expired_users:
                        del self._cooldowns[command][user_id]

                    # Remove empty command entries
                    if not self._cooldowns[command]:
                        del self._cooldowns[command]

            except Exception as e:
                logger.error(f"Error in cooldown cleanup: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    def is_on_cooldown(self, user_id: int, command: str) -> bool:
        """
        Check if a user is on cooldown for a specific command.

        Args:
            user_id: Discord user ID
            command: Command name

        Returns:
            True if user is on cooldown, False otherwise
        """
        if command not in self._cooldowns:
            return False

        if user_id not in self._cooldowns[command]:
            return False

        current_time = time.time()
        next_allowed_time = self._cooldowns[command][user_id]

        if current_time >= next_allowed_time:
            # Cooldown expired, remove it
            del self._cooldowns[command][user_id]
            return False

        return True

    def get_remaining_cooldown(self, user_id: int, command: str) -> float:
        """
        Get remaining cooldown time in seconds.

        Args:
            user_id: Discord user ID
            command: Command name

        Returns:
            Remaining cooldown time in seconds, 0 if not on cooldown
        """
        if not self.is_on_cooldown(user_id, command):
            return 0.0

        current_time = time.time()
        next_allowed_time = self._cooldowns[command][user_id]

        return max(0.0, next_allowed_time - current_time)

    def add_cooldown(self, user_id: int, command: str, cooldown_seconds: float):
        """
        Add a cooldown for a user and command.

        Args:
            user_id: Discord user ID
            command: Command name
            cooldown_seconds: Cooldown duration in seconds
        """
        # Start cleanup task if not running
        self._start_cleanup_task()

        next_allowed_time = time.time() + cooldown_seconds
        self._cooldowns[command][user_id] = next_allowed_time

        logger.debug(
            f"Added cooldown for user {user_id} on command '{command}' for {cooldown_seconds}s"
        )

    def reset_cooldown(self, user_id: int, command: str):
        """
        Reset cooldown for a specific user and command.

        Args:
            user_id: Discord user ID
            command: Command name
        """
        if command in self._cooldowns and user_id in self._cooldowns[command]:
            del self._cooldowns[command][user_id]
            logger.debug(f"Reset cooldown for user {user_id} on command '{command}'")

    def reset_user_cooldowns(self, user_id: int):
        """
        Reset all cooldowns for a specific user.

        Args:
            user_id: Discord user ID
        """
        for command in self._cooldowns:
            if user_id in self._cooldowns[command]:
                del self._cooldowns[command][user_id]

        logger.debug(f"Reset all cooldowns for user {user_id}")

    def get_user_cooldowns(self, user_id: int) -> Dict[str, float]:
        """
        Get all active cooldowns for a user.

        Args:
            user_id: Discord user ID

        Returns:
            Dict mapping command names to remaining cooldown times
        """
        result = {}
        current_time = time.time()

        for command, users in self._cooldowns.items():
            if user_id in users:
                remaining = max(0.0, users[user_id] - current_time)
                if remaining > 0:
                    result[command] = remaining

        return result

    def get_cooldown_stats(self) -> Dict[str, int]:
        """
        Get statistics about active cooldowns.

        Returns:
            Dict with cooldown statistics
        """
        current_time = time.time()
        stats = {
            "total_commands": len(self._cooldowns),
            "total_active_cooldowns": 0,
            "commands_with_cooldowns": 0,
        }

        for _command, users in self._cooldowns.items():
            active_users = sum(
                1 for next_time in users.values() if next_time > current_time
            )
            if active_users > 0:
                stats["commands_with_cooldowns"] += 1
                stats["total_active_cooldowns"] += active_users

        return stats


class CooldownDecorator:
    """Decorator for applying cooldowns to Discord slash commands."""

    def __init__(self, manager: CooldownManager, cooldown_seconds: float):
        self.manager = manager
        self.cooldown_seconds = cooldown_seconds

    def __call__(self, func):
        """Decorator function."""
        import functools

        # Preserve the original function signature
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # First argument should be interaction
            interaction = args[0] if args else None
            if not hasattr(interaction, "user"):
                # Not a Discord interaction, just call the function
                return await func(*args, **kwargs)

            user_id = interaction.user.id
            command_name = interaction.command.name

            # Check if user is on cooldown
            if self.manager.is_on_cooldown(user_id, command_name):
                remaining = self.manager.get_remaining_cooldown(user_id, command_name)
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)

                time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

                await interaction.response.send_message(
                    f"⏰ You're on cooldown! Please wait {time_str} before using this command again.",
                    ephemeral=True,
                )
                return

            # Execute the command
            try:
                result = await func(*args, **kwargs)

                # Add cooldown after successful execution
                self.manager.add_cooldown(user_id, command_name, self.cooldown_seconds)

                return result

            except Exception as e:
                # Don't add cooldown if command failed
                logger.error(f"Command {command_name} failed for user {user_id}: {e}")
                raise

        return wrapper


# Global cooldown manager instance
cooldown_manager = CooldownManager()


def cooldown(seconds: float):
    """
    Decorator to add cooldown to a command.

    Args:
        seconds: Cooldown duration in seconds

    Usage:
        @cooldown(30)  # 30 second cooldown
        async def my_command(interaction, ...):
            ...
    """
    return CooldownDecorator(cooldown_manager, seconds)


def format_cooldown_time(seconds: float) -> str:
    """
    Format cooldown time in a human-readable way.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
