#!/usr/bin/env python3
"""
Async Discord Webhook Helper
Provides async functionality for posting to Discord webhooks using aiohttp
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
import aiohttp


logger = logging.getLogger(__name__)


class AsyncDiscordWebhook:
    """Async Discord webhook client using aiohttp."""

    def __init__(
        self, webhook_url: str, session: Optional[aiohttp.ClientSession] = None
    ):
        """
        Initialize async Discord webhook client.

        Args:
            webhook_url: Discord webhook URL
            session: Optional aiohttp session (will create one if not provided)
        """
        self.webhook_url = webhook_url
        self.session = session
        self._should_close_session = session is None

    async def __aenter__(self):
        """Async context manager entry."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._should_close_session and self.session:
            await self.session.close()

    async def send_message(
        self,
        content: str,
        username: str = "Bot",
        avatar_url: Optional[str] = None,
        embeds: Optional[List[Dict]] = None,
    ) -> bool:
        """
        Send a text message to Discord.

        Args:
            content: Message content
            username: Bot username
            avatar_url: Bot avatar URL
            embeds: List of embed objects

        Returns:
            True if successful, False otherwise
        """
        payload = {"content": content, "username": username}

        if avatar_url:
            payload["avatar_url"] = avatar_url

        if embeds:
            payload["embeds"] = embeds

        try:
            async with self.session.post(
                self.webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 204:
                    logger.info("Successfully sent message to Discord")
                    return True
                else:
                    logger.error(
                        f"Discord webhook failed: {response.status} - {await response.text()}"
                    )
                    return False

        except asyncio.TimeoutError:
            logger.error("Discord webhook request timed out")
            return False
        except Exception as e:
            logger.error(f"Error sending message to Discord: {e}")
            return False

    async def send_pdf(
        self,
        pdf_path: str,
        message: Optional[str] = None,
        username: str = "PDF Bot",
        avatar_url: Optional[str] = None,
    ) -> bool:
        """
        Send a PDF file to Discord via webhook.

        Args:
            pdf_path: Path to the PDF file
            message: Optional message to send with the PDF
            username: Bot username for the message
            avatar_url: Avatar URL for the bot

        Returns:
            True if successful, False otherwise
        """
        pdf_file = Path(pdf_path)

        if not pdf_file.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return False

        if pdf_file.suffix.lower() != ".pdf":
            logger.error(f"File is not a PDF: {pdf_path}")
            return False

        file_size = pdf_file.stat().st_size
        max_size = 25 * 1024 * 1024  # 25MB Discord limit

        if file_size > max_size:
            logger.error(
                f"PDF file too large: {file_size / (1024 * 1024):.1f}MB (max 25MB)"
            )
            return False

        try:
            # Prepare the payload
            payload = {
                "username": username,
                "content": message or f"📄 New idea sheet: **{pdf_file.stem}**",
            }

            if avatar_url:
                payload["avatar_url"] = avatar_url

            # Create embed with file info
            embed = {
                "title": "📋 Idea Sheet Published",
                "description": f"**File:** {pdf_file.name}\n**Size:** {file_size / 1024:.1f} KB",
                "color": 0x3498DB,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": "Project Automation Platform"},
                "fields": [
                    {
                        "name": "📅 Generated",
                        "value": datetime.now(timezone.utc).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "inline": True,
                    }
                ],
            }

            payload["embeds"] = [embed]

            # Send the file
            async with aiofiles.open(pdf_file, "rb") as f:
                pdf_data = await f.read()

                form_data = aiohttp.FormData()
                form_data.add_field("payload_json", json.dumps(payload))
                form_data.add_field(
                    "file",
                    pdf_data,
                    filename=pdf_file.name,
                    content_type="application/pdf",
                )

                async with self.session.post(
                    self.webhook_url,
                    data=form_data,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 204:
                        logger.info(f"Successfully sent {pdf_file.name} to Discord")
                        return True
                    else:
                        logger.error(
                            f"Discord webhook failed: {response.status} - {await response.text()}"
                        )
                        return False

        except asyncio.TimeoutError:
            logger.error("Discord webhook request timed out")
            return False
        except Exception as e:
            logger.error(f"Error sending PDF to Discord: {e}")
            return False

    async def send_multiple_pdfs(
        self,
        pdf_paths: List[str],
        batch_message: Optional[str] = None,
        username: str = "PDF Bot",
    ) -> Dict[str, bool]:
        """
        Send multiple PDF files to Discord.

        Args:
            pdf_paths: List of PDF file paths
            batch_message: Optional batch message
            username: Bot username

        Returns:
            Dictionary mapping file paths to success status
        """
        results = {}

        if batch_message:
            await self.send_message(batch_message, username=username)

        for pdf_path in pdf_paths:
            results[pdf_path] = await self.send_pdf(pdf_path, username=username)
            # Small delay between uploads to avoid rate limiting
            await asyncio.sleep(1)

        return results


async def send_notification(
    webhook_url: str, title: str, message: str, color: int = 0x3498DB
) -> bool:
    """
    Send a notification embed to Discord.

    Args:
        webhook_url: Discord webhook URL
        title: Notification title
        message: Notification message
        color: Embed color (default blue)

    Returns:
        True if successful, False otherwise
    """
    embed = {
        "title": title,
        "description": message,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": "Project Automation Platform"},
    }

    async with AsyncDiscordWebhook(webhook_url) as webhook:
        return await webhook.send_message("", embeds=[embed])


async def post_pdf_to_discord(
    webhook_url: str, pdf_path: str, message: Optional[str] = None
) -> bool:
    """
    Convenience function to post a PDF to Discord.

    Args:
        webhook_url: Discord webhook URL
        pdf_path: Path to PDF file
        message: Optional message

    Returns:
        True if successful, False otherwise
    """
    async with AsyncDiscordWebhook(webhook_url) as webhook:
        return await webhook.send_pdf(pdf_path, message)


# Environment-aware helper functions
def get_webhook_url_from_env() -> Optional[str]:
    """Get Discord webhook URL from environment variables."""
    return os.getenv("DISCORD_WEBHOOK_URL")


async def send_pdf_if_webhook_configured(
    pdf_path: str, message: Optional[str] = None
) -> bool:
    """
    Send PDF to Discord if webhook URL is configured in environment.

    Args:
        pdf_path: Path to PDF file
        message: Optional message

    Returns:
        True if sent successfully or webhook not configured, False if failed
    """
    webhook_url = get_webhook_url_from_env()
    if not webhook_url:
        logger.info("DISCORD_WEBHOOK_URL not configured, skipping Discord notification")
        return True

    return await post_pdf_to_discord(webhook_url, pdf_path, message)


if __name__ == "__main__":
    # Demo usage
    async def demo():
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            print("Set DISCORD_WEBHOOK_URL environment variable to test")
            return

        async with AsyncDiscordWebhook(webhook_url) as webhook:
            # Test message
            await webhook.send_message("🤖 Testing async Discord webhook!")

            # Test notification
            await send_notification(
                webhook_url,
                "🧪 Test Notification",
                "This is a test of the async Discord webhook system.",
            )

    asyncio.run(demo())
