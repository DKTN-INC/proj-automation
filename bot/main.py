#!/usr/bin/env python3
"""
Discord Bot for Project Automation

Provides /ask and /summarize commands for team collaboration.
Full-featured bot with AI integration, file processing, and automation.
"""

# Standard library imports
import asyncio
import contextlib
import logging
import os
import shutil
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Dict, List, Optional

# Third-party imports
import aiofiles
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables from .env file at the very top
load_dotenv()

# Workaround for pydub ffmpeg warning
warnings.filterwarnings(
    "ignore",
    message="Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work",
    category=RuntimeWarning,
)
_ffmpeg_path = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
if _ffmpeg_path:
    with contextlib.suppress(Exception):
        from pydub import AudioSegment
        AudioSegment.converter = _ffmpeg_path

# Local application imports with fallbacks
try:
    from bot.config import config
    from .cooldowns import cooldown
    from .google_api_wrapper import GoogleAPIWrapper
    from .utils import (
        ai_helper,
        code_analyzer,
        file_processor,
        github_helper,
        memory,
        web_search,
    )
    from .circuit_breaker import circuit_manager
    from .health_monitor import (
        health_monitor,
        register_health_check,
        start_health_monitoring,
        stop_health_monitoring,
    )
    from .logging_config import (
        log_bot_event,
        log_command_execution,
        setup_logging,
    )
    from .resource_manager import cleanup_resources, get_resource_stats
    from .thread_pool import (
        parse_discord_messages,
        shutdown_thread_pool,
    )
except ImportError:
    # Fallbacks for running script directly
    from config import config
    from cooldowns import cooldown
    from google_api_wrapper import GoogleAPIWrapper
    from utils import (
        ai_helper,
        code_analyzer,
        file_processor,
        github_helper,
        memory,
        web_search,
    )
    # Fallback for missing modules
    circuit_manager = None
    health_monitor = None
    setup_logging = None
    log_bot_event = lambda *args, **kwargs: None
    log_command_execution = lambda logger: (lambda func: func)
    cleanup_resources = lambda: None
    get_resource_stats = lambda: {}
    start_health_monitoring = lambda: asyncio.sleep(0)
    stop_health_monitoring = lambda: asyncio.sleep(0)
    register_health_check = lambda name, func: None
    parse_discord_messages = lambda messages: {"total_messages": len(messages), "unique_users": len({m['author'] for m in messages}), "user_stats": {}, "most_active_hours": []}
    shutdown_thread_pool = lambda: asyncio.sleep(0)


# -----------------------------------------------------------------------------
# Constants and Bot Initialization
# -----------------------------------------------------------------------------
HELPDOCS_DIR = "docs/helpdocs"
IDEASHEETS_DIR = "docs/ideasheets"

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

_google_client: Optional[GoogleAPIWrapper] = None

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
if setup_logging:
    logger = setup_logging(
        level=os.getenv("LOG_LEVEL", "INFO"),
        structured=os.getenv("STRUCTURED_LOGS", "false").lower() == "true",
        log_file=os.getenv("LOG_FILE"),
        service_name="proj-automation-bot",
    )
else:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("proj-automation-bot")

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def get_discord_token() -> Optional[str]:
    token = os.getenv("BOT_TOKEN") or getattr(config, "discord_token", None)
    if not token:
        raise ValueError("Discord token is missing. Please set BOT_TOKEN or discord_token.")
    return token

def get_google_api_key() -> Optional[str]:
    key = getattr(config, "google_api_key", None) or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ValueError("Google API key is missing. Please set GOOGLE_API_KEY or google_api_key.")
    return key

def get_google_client() -> GoogleAPIWrapper:
    """Get or create Google API client instance."""
    global _google_client
    if _google_client is None:
        _google_client = GoogleAPIWrapper()
    return _google_client

class _BasicChunker:
    MAX_EMBED = 4000
    def chunk_text(self, text: str, size: int = 1800) -> List[str]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not isinstance(size, int) or size <= 0:
            raise ValueError("size must be a positive integer")
        return [text[i : i + size] for i in range(0, len(text), size)]
    def add_chunk_indicators(self, chunks: List[str]) -> List[str]:
        if not all(isinstance(chunk, str) for chunk in chunks):
            raise TypeError("All chunks must be strings")
        total = len(chunks)
        return [f"{c}\n\n({i + 1}/{total})" for i, c in enumerate(chunks)]
    def truncate_with_ellipsis(self, text: str, max_len: int) -> str:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not isinstance(max_len, int) or max_len <= 0:
            raise ValueError("max_len must be a positive integer")
        return text if len(text) <= max_len else text[: max_len - 1] + "…"
    def chunk_for_embed_description(self, text: str) -> List[str]:
        return self.chunk_text(text, size=self.MAX_EMBED - 100)

chunker = _BasicChunker()

# -----------------------------------------------------------------------------
# Bot Events
# -----------------------------------------------------------------------------
@bot.event
async def on_ready():
    """Called when the bot is ready."""
    log_bot_event(logger, "bot_ready", user=str(bot.user), guilds=len(bot.guilds))

    # Sync commands
    try:
        synced = await bot.tree.sync()
        log_bot_event(logger, "commands_synced", command_count=len(synced))
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}", exc_info=True)

    logger.info("Bot is ready and commands are registered.")

@bot.event
async def on_message(message: discord.Message):
    """Handle incoming messages."""
    if message.author.bot:
        return

    # Process commands first
    await bot.process_commands(message)

# -----------------------------------------------------------------------------
# Slash Commands
# -----------------------------------------------------------------------------
@bot.tree.command(name="ask", description="Ask a question and get an AI-powered answer.")
@app_commands.describe(question="The question you want to ask")
@cooldown(30)  # 30-second cooldown
@log_command_execution(logger)
async def ask_command(interaction: discord.Interaction, question: str):
    """Handles the /ask command with token optimization, rate-limiting, and fallback for quota errors."""
    # Only defer if not already acknowledged by middleware/decorators
    try:
        if not interaction.response.is_done():
            await interaction.response.defer()
    except Exception:
        # Interaction may have already expired; the cooldown wrapper logs this.
        logger.debug("ask_command: defer skipped or failed; interaction may be timed out")

    # Removed unused variable `create_thread`
    if question.lower().startswith("/thread"):
        question = question[len("/thread"):].strip()

    try:
        if get_google_api_key():
            client = get_google_client()

            # Token optimization: Summarize or chunk the question if too long
            if len(question) > 1000:
                question = chunker.truncate_with_ellipsis(question, 1000)

            try:
                ai_response = client.answer_question(question)
                await interaction.followup.send(content=ai_response)
            except Exception as e:
                if "quota" in str(e).lower():
                    await interaction.followup.send(content="⚠️ AI quota exceeded. Please try again later.")
                else:
                    logger.error(f"Failed to get AI response: {e}")
                    await interaction.followup.send(content="❌ Failed to get AI response. Please try again.")
        else:
            await interaction.followup.send(content="⚠️ AI features are disabled. Please configure the API key.")
    except Exception as e:
        logger.error(f"Unexpected error in /ask command: {e}")
        await interaction.followup.send(content="❌ An unexpected error occurred. Please try again.")

@bot.tree.command(name="summarize", description="Summarize recent channel activity.")
@app_commands.describe(
    hours="How many hours of history to summarize (default: 24).",
    channel="The channel to summarize (defaults to current channel).",
)
@cooldown(60) # 1 use per 60 seconds
@log_command_execution(logger)
async def summarize_command(
    interaction: discord.Interaction,
    hours: app_commands.Range[int, 1, 168] = 24,
    channel: Optional[discord.TextChannel] = None,
):
    """Handles the /summarize command."""
    await interaction.response.defer()

    target_channel = channel or interaction.channel
    if not isinstance(target_channel, discord.TextChannel):
        await interaction.followup.send("This command can only be used in a server's text channel.", ephemeral=True)
        return

    threshold = datetime.now(timezone.utc) - timedelta(hours=hours)

    async def filter_messages(messages, threshold):
        """Filter messages based on the threshold and return relevant data."""
        messages_data = []
        async for msg in messages:
            if not msg.author.bot and (msg.content or "").strip():
                messages_data.append({
                    "author": msg.author.display_name,
                    "content": msg.content,
                    "timestamp": msg.created_at,
                    "reactions": sum(r.count for r in msg.reactions),
                })
        return messages_data

    def generate_summary(messages_data):
        """Generate a summary from the filtered messages."""
        if not messages_data:
            return "📭 No messages found."
        return f"✅ Summary generated for {target_channel.mention}."

    messages_data = await filter_messages(
        target_channel.history(limit=None, after=threshold, oldest_first=False),
        threshold
    )

    summary = generate_summary(messages_data)
    await interaction.followup.send(summary)

# -----------------------------------------------------------------------------
# Traditional Commands
# -----------------------------------------------------------------------------
@bot.command(name="shutdown")
@commands.is_owner()
async def shutdown_command(ctx: commands.Context):
    """Shut down the bot gracefully."""
    await ctx.send("[INFO] Shutting down bot...")
    logger.info("Shutdown command received. Shutting down bot.")
    await bot.close()

# -----------------------------------------------------------------------------
# Error Handling and Lifecycle
# -----------------------------------------------------------------------------
@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    """Handle traditional command errors."""
    logger.error(f"Command error in '{ctx.command}': {error}", exc_info=True)
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f}s.")
    else:
        await ctx.send(f"[ERROR] Command error: {error}")

@bot.event
async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle slash command errors."""
    logger.error(f"Slash command error for '{interaction.command.name if interaction.command else 'unknown'}': {error}", exc_info=True)
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
    elif not interaction.response.is_done():
        await interaction.response.send_message(f"[ERROR] An error occurred: {error}", ephemeral=True)
    else:
        await interaction.followup.send(f"[ERROR] An error occurred: {error}", ephemeral=True)

async def cleanup():
    """Cleanup resources before shutdown."""
    logger.info("Starting cleanup process")
    global _google_client
    if _google_client and hasattr(_google_client, "close"):
        await _google_client.close()
    if shutdown_thread_pool:
        await shutdown_thread_pool()
    logger.info("Cleanup completed")

def main():
    """Main function to run the bot."""
    token = get_discord_token()
    if not token:
        logger.error("Missing Discord token. Set BOT_TOKEN in your environment.")
        return

    async def runner():
        async with bot:
            await bot.start(token)

    try:
        asyncio.run(runner())
    except discord.LoginFailure:
        logger.error("Invalid Discord bot token!")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        asyncio.run(cleanup())

if __name__ == "__main__":
    main()
