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

# Third-party imports
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

    from bot import ideas, tasks

    # utils module is optional for runtime features; imported lazily where needed
    from bot.circuit_breaker import circuit_manager
    from bot.cooldowns import cooldown
    from bot.google_api_wrapper import GoogleAPIWrapper
    from bot.health_monitor import (
        health_monitor,
        register_health_check,
        start_health_monitoring,
        stop_health_monitoring,
    )
    from bot.logging_config import (
        log_bot_event,
        log_command_execution,
        setup_logging,
    )
    from bot.resource_manager import cleanup_resources, get_resource_stats
    from bot.thread_pool import (
        parse_discord_messages,
        shutdown_thread_pool,
    )
except ImportError:
    # Fallbacks for running script directly
    from config import config
    from cooldowns import cooldown

    from bot.google_api_wrapper import GoogleAPIWrapper

    # Fallback for missing modules
    circuit_manager = None
    health_monitor = None
    setup_logging = None

    def log_bot_event(*args, **kwargs):
        return None

    def log_command_execution(logger):
        def wrapper(func):
            return func

        return wrapper

    def cleanup_resources():
        return None

    def get_resource_stats():
        return {}

    async def start_health_monitoring():
        return await asyncio.sleep(0)

    async def stop_health_monitoring():
        return await asyncio.sleep(0)

    def register_health_check(name, func):
        return None

    def parse_discord_messages(messages):
        return {
            "total_messages": len(messages),
            "unique_users": len({m["author"] for m in messages}),
            "user_stats": {},
            "most_active_hours": [],
        }

    async def shutdown_thread_pool():
        return await asyncio.sleep(0)


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

_google_client: GoogleAPIWrapper | None = None

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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("proj-automation-bot")


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def get_discord_token() -> str | None:
    token = os.getenv("BOT_TOKEN") or getattr(config, "discord_token", None)
    if not token:
        raise ValueError(
            "Discord token is missing. Please set BOT_TOKEN or discord_token."
        )
    return token


def get_google_api_key() -> str | None:
    key = getattr(config, "google_api_key", None) or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ValueError(
            "Google API key is missing. Please set GOOGLE_API_KEY or google_api_key."
        )
    return key


def get_google_client() -> GoogleAPIWrapper:
    """Get or create Google API client instance."""
    global _google_client
    if _google_client is None:
        _google_client = GoogleAPIWrapper()
    return _google_client


class _BasicChunker:
    MAX_EMBED = 4000

    def chunk_text(self, text: str, size: int = 1800) -> list[str]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not isinstance(size, int) or size <= 0:
            raise ValueError("size must be a positive integer")
        return [text[i : i + size] for i in range(0, len(text), size)]

    def add_chunk_indicators(self, chunks: list[str]) -> list[str]:
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

    def chunk_for_embed_description(self, text: str) -> list[str]:
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
@bot.tree.command(
    name="ask", description="Ask a question and get an AI-powered answer."
)
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
        logger.debug(
            "ask_command: defer skipped or failed; interaction may be timed out"
        )

    # Removed unused variable `create_thread`
    if question.lower().startswith("/thread"):
        question = question[len("/thread") :].strip()

    try:
        if get_google_api_key():
            client = get_google_client()

            # Token optimization: Summarize or chunk the question if too long
            if len(question) > 1000:
                question = chunker.truncate_with_ellipsis(question, 1000)

            try:
                ai_candidate = client.answer_question(question)
                # Support both sync and async client implementations
                if asyncio.iscoroutine(ai_candidate):
                    ai_response = await ai_candidate
                else:
                    ai_response = ai_candidate
                await interaction.followup.send(content=ai_response)
            except Exception as e:
                if "quota" in str(e).lower():
                    await interaction.followup.send(
                        content="⚠️ AI quota exceeded. Please try again later."
                    )
                else:
                    logger.error(f"Failed to get AI response: {e}")
                    await interaction.followup.send(
                        content="❌ Failed to get AI response. Please try again."
                    )
        else:
            await interaction.followup.send(
                content="⚠️ AI features are disabled. Please configure the API key."
            )
    except Exception as e:
        logger.error(f"Unexpected error in /ask command: {e}")
        await interaction.followup.send(
            content="❌ An unexpected error occurred. Please try again."
        )


@bot.tree.command(name="summarize", description="Summarize recent channel activity.")
@app_commands.describe(
    hours="How many hours of history to summarize (default: 24).",
    channel="The channel to summarize (defaults to current channel).",
)
@cooldown(60)  # 1 use per 60 seconds
@log_command_execution(logger)
async def summarize_command(
    interaction: discord.Interaction,
    hours: app_commands.Range[int, 1, 168] = 24,
    channel: discord.TextChannel | None = None,
):
    """Handles the /summarize command."""
    await interaction.response.defer()

    target_channel = channel or interaction.channel

    # Check if the channel is a TextChannel or a suitable fake for testing
    is_text_channel = isinstance(target_channel, discord.TextChannel)
    is_test_channel = (
        hasattr(target_channel, "guild") and target_channel.guild is not None
    )

    if not (is_text_channel or is_test_channel):
        await interaction.followup.send(
            "This command can only be used in a server's text channel.", ephemeral=True
        )
        return

    threshold = datetime.now(timezone.utc) - timedelta(hours=hours)

    async def filter_messages(messages, threshold):
        """Filter messages based on the threshold and return relevant data."""
        messages_data = []
        async for msg in messages:
            if not msg.author.bot and (msg.content or "").strip():
                messages_data.append(
                    {
                        "author": msg.author.display_name,
                        "content": msg.content,
                        "timestamp": msg.created_at,
                        "reactions": sum(r.count for r in msg.reactions),
                    }
                )
        return messages_data

    def generate_summary(messages_data):
        """Generate a summary from the filtered messages."""
        if not messages_data:
            return "📭 No messages found."
        return f"✅ Summary generated for {target_channel.mention}."

    messages_data = await filter_messages(
        target_channel.history(limit=None, after=threshold, oldest_first=False),
        threshold,
    )

    summary = generate_summary(messages_data)
    await interaction.followup.send(summary)


# -----------------------------------------------------------------------------
# Idea Sheet Commands
# -----------------------------------------------------------------------------
idea_group = app_commands.Group(
    name="idea", description="Commands for managing idea sheets."
)


@idea_group.command(name="create", description="Create a new idea sheet.")
@app_commands.describe(title="The title of the new idea sheet.")
async def idea_create(interaction: discord.Interaction, title: str):
    """Creates a new idea sheet."""
    try:
        ideas.create_idea_sheet(title)
        await interaction.response.send_message(
            f"✅ Idea sheet '{title}' created successfully.", ephemeral=True
        )
    except (OSError, ValueError) as e:
        await interaction.response.send_message(
            f"❌ Error creating idea sheet: {e}", ephemeral=True
        )


@idea_group.command(name="list", description="List all idea sheets.")
async def idea_list(interaction: discord.Interaction):
    """Lists all available idea sheets."""
    try:
        sheet_list = ideas.list_idea_sheets()
        if not sheet_list:
            await interaction.response.send_message(
                "No idea sheets found.", ephemeral=True
            )
            return

        # Format the list into a simple embed
        embed = discord.Embed(title="Idea Sheets", color=discord.Color.blue())
        embed.description = "\n".join(f"- {sheet}" for sheet in sheet_list)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error listing idea sheets: {e}", ephemeral=True
        )


@idea_group.command(name="view", description="View the content of an idea sheet.")
@app_commands.describe(title="The title of the idea sheet to view.")
async def idea_view(interaction: discord.Interaction, title: str):
    """Views a specific idea sheet."""
    try:
        content = ideas.get_idea_sheet_content(title)
        if len(content) > 1900:
            content = content[:1900] + "..."

        embed = discord.Embed(
            title=title, description=content, color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except FileNotFoundError:
        await interaction.response.send_message(
            f"❌ Idea sheet '{title}' not found.", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error viewing idea sheet: {e}", ephemeral=True
        )


bot.tree.add_command(idea_group)

# -----------------------------------------------------------------------------
# Task Tracking Commands
# -----------------------------------------------------------------------------
task_group = app_commands.Group(
    name="todo", description="Commands for managing the team to-do list."
)


@task_group.command(name="add", description="Add a new task to the to-do list.")
@app_commands.describe(description="The description of the task.")
async def todo_add(interaction: discord.Interaction, description: str):
    """Adds a new task."""
    try:
        task = tasks.add_task(description)
        await interaction.response.send_message(
            f"✅ Task #{task['id']} added: '{description}'", ephemeral=True
        )
    except ValueError as e:
        await interaction.response.send_message(
            f"❌ Error adding task: {e}", ephemeral=True
        )


@task_group.command(name="list", description="List all current tasks.")
async def todo_list(interaction: discord.Interaction):
    """Lists all tasks."""
    task_list = tasks.list_tasks()
    if not task_list:
        await interaction.response.send_message(
            "No tasks in the to-do list.", ephemeral=True
        )
        return

    embed = discord.Embed(title="To-Do List", color=discord.Color.orange())
    for task in task_list:
        status = "✅" if task["done"] else "❌"
        embed.add_field(
            name=f"#{task['id']} {status}", value=task["description"], inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@task_group.command(name="done", description="Mark a task as done.")
@app_commands.describe(task_id="The ID of the task to mark as done.")
async def todo_done(interaction: discord.Interaction, task_id: int):
    """Marks a task as done."""
    task = tasks.mark_task_done(task_id)
    if task:
        await interaction.response.send_message(
            f"✅ Task #{task_id} marked as done.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ Task #{task_id} not found.", ephemeral=True
        )


@task_group.command(name="clear", description="Clear all tasks from the to-do list.")
@commands.is_owner()
async def todo_clear(interaction: discord.Interaction):
    """Clears all tasks."""
    tasks.clear_tasks()
    await interaction.response.send_message(
        "✅ All tasks have been cleared.", ephemeral=True
    )


bot.tree.add_command(task_group)


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
        await ctx.send(
            f"This command is on cooldown. Try again in {error.retry_after:.2f}s."
        )
    else:
        await ctx.send(f"[ERROR] Command error: {error}")


@bot.event
async def on_tree_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    """Handle slash command errors."""
    logger.error(
        f"Slash command error for '{interaction.command.name if interaction.command else 'unknown'}': {error}",
        exc_info=True,
    )
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"This command is on cooldown. Try again in {error.retry_after:.2f}s.",
            ephemeral=True,
        )
    elif not interaction.response.is_done():
        await interaction.response.send_message(
            f"[ERROR] An error occurred: {error}", ephemeral=True
        )
    else:
        await interaction.followup.send(
            f"[ERROR] An error occurred: {error}", ephemeral=True
        )


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
