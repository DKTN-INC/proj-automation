#!/usr/bin/env python3
"""
Discord Bot for Project Automation

Provides /ask and /summarize commands for team collaboration.
Full-featured bot with AI integration, file processing, and automation.
"""

import asyncio
import contextlib
import logging
import os
import signal
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import warnings
import shutil

import aiofiles
import discord
from discord import app_commands
from discord.ext import commands

# Load environment variables from .env file early
from dotenv import load_dotenv

# Workaround for pydub ffmpeg warning: suppress the specific RuntimeWarning that
# appears when ffmpeg/avconv isn't found on PATH, and try to locate ffmpeg and
# configure pydub to use it if present. This runs before importing modules that
# may import pydub to avoid noisy warnings during startup.


# Load environment variables
load_dotenv()

warnings.filterwarnings(
    "ignore",
    message="Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work",
    category=RuntimeWarning,
)

# If ffmpeg is available on PATH, set pydub's converter after import (we'll
# attempt a lazy import below where pydub is available). This prevents the
# warning and ensures audio processing works when ffmpeg is installed.
_ffmpeg_path = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
if _ffmpeg_path:
    # Use contextlib.suppress to quietly handle import/assignment failures
    # (keeps intent explicit and satisfies linters suggesting contextlib.suppress)
    with contextlib.suppress(Exception):
        # Delay import so we don't trigger pydub utils before filtering warnings
        from pydub import AudioSegment  # type: ignore

        AudioSegment.converter = _ffmpeg_path  # type: ignore

# -----------------------------------------------------------------------------
# Imports from our package with fallbacks for direct execution
# -----------------------------------------------------------------------------
try:
    from .config import (
        config,
    )  # config object with directories, tokens, validation, etc.
    from .utils import (
        ai_helper,
        code_analyzer,
        file_processor,
        github_helper,
        memory,
        web_search,
    )
except ImportError:
    from config import config  # type: ignore
    from utils import (  # type: ignore
        ai_helper,
        code_analyzer,
        file_processor,
        github_helper,
        memory,
        web_search,
    )

# Optional advanced modules (structured logging, cooldowns, OpenAI wrapper, thread pool)
try:
    from .circuit_breaker import circuit_manager
    from .health_monitor import (
        health_monitor,
        register_health_check,
        start_health_monitoring,
        stop_health_monitoring,
    )
    from .logging_config import (  # type: ignore
        log_bot_event,
        log_command_execution,
        setup_logging,
    )
    from .resource_manager import cleanup_resources, get_resource_stats
except Exception:
    try:
        from circuit_breaker import circuit_manager
        from health_monitor import (
            health_monitor,
            register_health_check,
            start_health_monitoring,
            stop_health_monitoring,
        )
        from logging_config import (  # type: ignore
            log_bot_event,
            log_command_execution,
            setup_logging,
        )
        from resource_manager import cleanup_resources, get_resource_stats
    except Exception:
        # Fallbacks
        setup_logging = None  # type: ignore
        health_monitor = None  # type: ignore

        async def start_health_monitoring() -> None:
            pass

        async def stop_health_monitoring() -> None:
            pass

        def register_health_check(name: str, func: Callable) -> None:
            pass

        circuit_manager = None  # type: ignore

        async def cleanup_resources() -> None:
            pass

        async def get_resource_stats() -> Dict[str, Any]:
            return {}

        def log_command_execution(
            _logger: logging.Logger,
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def deco(func: Callable[..., Any]) -> Callable[..., Any]:
                return func

            return deco

        def log_bot_event(_logger: logging.Logger, event: str, **fields: Any) -> None:
            _logger.info(f"[event] {event} | {fields}")


try:
    from .cooldowns import cooldown, cooldown_manager  # type: ignore
except Exception:
    try:
        from cooldowns import cooldown, cooldown_manager  # type: ignore
    except Exception:

        def cooldown(
            _seconds: int,
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def deco(func: Callable[..., Any]) -> Callable[..., Any]:
                return func

            return deco

        cooldown_manager = None  # type: ignore

try:
    from .openai_wrapper import OpenAIWrapper  # type: ignore
except Exception:
    try:
        from openai_wrapper import OpenAIWrapper  # type: ignore
    except Exception:
        OpenAIWrapper = None  # type: ignore

try:
    from .thread_pool import (  # type: ignore
        parse_discord_messages,
        shutdown_thread_pool,
        thread_pool,
    )
except Exception:
    try:
        from thread_pool import (
            parse_discord_messages,
            shutdown_thread_pool,
            thread_pool,
        )  # type: ignore
    except Exception:
        thread_pool = None  # type: ignore

        async def parse_discord_messages(
            messages: List[Dict[str, Any]],
        ) -> Dict[str, Any]:  # type: ignore
            # Minimal fallback analysis
            users: Dict[str, Dict[str, int]] = {}
            hours: Dict[int, int] = {}
            for m in messages:
                a = m.get("author", "unknown")
                users.setdefault(a, {"message_count": 0, "reactions_received": 0})
                users[a]["message_count"] += 1
                users[a]["reactions_received"] += int(m.get("reactions", 0))
                ts: datetime = m.get("timestamp") or datetime.utcnow()
                hours[ts.hour] = hours.get(ts.hour, 0) + 1
            most_active = sorted(hours.items(), key=lambda x: x[1], reverse=True)
            return {
                "total_messages": len(messages),
                "unique_users": len(users),
                "user_stats": users,
                "most_active_hours": most_active,
            }

        async def shutdown_thread_pool() -> None:  # type: ignore
            return


# -----------------------------------------------------------------------------
# Logging setup
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
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO"), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("proj-automation-bot")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def get_openai_api_key() -> Optional[str]:
    # Prefer config if present, then env var
    key = getattr(config, "openai_api_key", None)
    if not key:
        key = getattr(config, "OPENAI_API_KEY", None)
    return key or os.getenv("OPENAI_API_KEY")


def get_discord_token() -> Optional[str]:
    token = getattr(config, "discord_token", None)
    if not token:
        token = os.getenv("DISCORD_BOT_TOKEN")
    return token


# -----------------------------------------------------------------------------
# Bot configuration
# -----------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Global instances
try:
    # Prefer provided chunker if available
    from utils import MessageChunker  # type: ignore
except Exception:
    MessageChunker = None  # type: ignore


class _BasicChunker:
    MAX_EMBED = 4000

    def chunk_text(self, text: str, size: int = 1800) -> List[str]:
        return [text[i : i + size] for i in range(0, len(text), size)]

    def add_chunk_indicators(self, chunks: List[str]) -> List[str]:
        total = len(chunks)
        return [f"{c}\n\n({i + 1}/{total})" for i, c in enumerate(chunks)]

    def truncate_with_ellipsis(self, text: str, max_len: int) -> str:
        return text if len(text) <= max_len else text[: max_len - 1] + "…"

    def chunk_for_embed_description(self, text: str) -> List[str]:
        return self.chunk_text(text, size=self.MAX_EMBED - 100)


chunker = MessageChunker() if MessageChunker else _BasicChunker()

_openai_client = None  # type: ignore


async def get_openai_client():
    """Get or create OpenAI client instance."""
    global _openai_client
    if _openai_client is None:
        key = get_openai_api_key()
        if not key:
            raise ValueError("OpenAI API key not configured")
        if not OpenAIWrapper:
            raise RuntimeError("OpenAI client not available")
        _openai_client = OpenAIWrapper(key)  # type: ignore
    return _openai_client


# -----------------------------------------------------------------------------
# Events
# -----------------------------------------------------------------------------
@bot.event
async def on_ready():
    """Called when the bot is ready."""
    log_bot_event(logger, "bot_ready", user=str(bot.user), guilds=len(bot.guilds))

    # Initialize database (best effort)
    try:
        await memory.init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database init skipped/failed: {e}")

    # Validate configuration
    try:
        is_valid, messages = config.validate_config()
        for message in messages:
            logger.info(f"Config: {message}")
        if not is_valid:
            logger.error("Bot configuration is invalid!")
            # Don't return here; allow limited functionality if desired
    except Exception as e:
        logger.warning(f"Config validation failed: {e}")

    # Start health monitoring
    with contextlib.suppress(Exception):
        if health_monitor:
            # Register custom health checks
            register_health_check("discord_connection", check_discord_health)
            register_health_check("openai_service", check_openai_health)
            register_health_check("database_connection", check_database_health)

            await start_health_monitoring()
            logger.info("Health monitoring started")

    # Sync commands
    try:
        synced = await bot.tree.sync()
        log_bot_event(logger, "commands_synced", command_count=len(synced))
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}", exc_info=True)

    async def handle_dm_message(message: discord.Message):
        """Handle direct messages for markdown intake and file uploads."""
        user = message.author
        content = (message.content or "").strip()

        # Admin uploads to helpdocs
        # Use contextlib.suppress to ignore expected transient errors
        import contextlib

        with contextlib.suppress(Exception):
            if (
                hasattr(config, "is_admin")
                and config.is_admin(user.id)
                and message.attachments
            ):
                await handle_admin_file_upload(message)
                return

        # Attachments (OCR/transcription) or markdown intake
        if message.attachments:
            await handle_dm_attachments(message)
        elif content.startswith("```") or content.startswith("#") or len(content) > 100:
            await handle_markdown_intake(message)
        else:
            await handle_dm_conversation(message)


async def handle_admin_file_upload(message: discord.Message):
    """Handle admin file uploads to helpdocs directory."""
    user = message.author

    for attachment in message.attachments:
        # Best-effort: suppress expected transient errors during admin uploads
        with contextlib.suppress(Exception):
            # Sanitize filename to prevent path traversal and unsafe characters
            raw_name = Path(attachment.filename).name
            # allow basic filename chars, replace others with underscore
            safe_name = __import__("re").sub(r"[^A-Za-z0-9._\-]", "_", raw_name)[:100]

            file_path = (
                Path(getattr(config, "helpdocs_dir", Path("docs/helpdocs")))
                / safe_name
            )
            async with aiofiles.open(file_path, "wb") as f:
                data = await attachment.read()
                await f.write(data)

            await message.reply(f"[OK] File `{safe_name}` uploaded to helpdocs/")
            logger.info(
                f"Admin {user.display_name} uploaded {safe_name} to helpdocs"
            )


async def handle_dm_attachments(message: discord.Message):
    """Handle attachments in DMs (images for OCR, audio for transcription)."""
    for attachment in message.attachments:
        try:
            max_size = getattr(config, "max_file_size", 25 * 1024 * 1024)
            if attachment.size > max_size:
                await message.reply(
                    f"[ERROR] File too large: {attachment.filename} ({attachment.size / 1024 / 1024:.1f}MB > 25MB)"
                )
                continue

            # Download to temp file (synchronous file write)
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=Path(attachment.filename).suffix
            ) as temp_file:
                data = await attachment.read()
                temp_file.write(data)
                temp_path = Path(temp_file.name)

            ctype = attachment.content_type or ""
            if ctype.startswith("image/"):
                # OCR processing
                extracted_text = await file_processor.extract_text_from_image(temp_path)
                if extracted_text:
                    embed = discord.Embed(
                        title="📷 OCR Results",
                        description=f"```\n{extracted_text[:1900]}\n```",
                        color=0x3498DB,
                    )
                    await message.reply(embed=embed)
                else:
                    await message.reply("[ERROR] No text found in image")

            elif ctype.startswith("audio/"):
                # Audio transcription
                await message.reply("🎵 Processing audio... (this may take a moment)")

                wav_path = temp_path.with_suffix(".wav")
                if await file_processor.convert_audio_to_wav(temp_path, wav_path):
                    transcription = await ai_helper.transcribe_audio(wav_path)

                    embed = discord.Embed(
                        title="🎤 Audio Transcription",
                        description=f"```\n{transcription[:1900]}\n```",
                        color=0x9B59B6,
                    )
                    await message.reply(embed=embed)

                    # Best-effort cleanup of temp wav file; suppress known errors
                    with contextlib.suppress(TypeError, FileNotFoundError):
                        wav_path.unlink(missing_ok=True)  # type: ignore
                else:
                    await message.reply("[ERROR] Failed to process audio file")

            else:
                await message.reply(f"❓ Unsupported file type: {attachment.filename}")

            # Clean up temp file (best-effort)
            with contextlib.suppress(Exception):
                if temp_path.exists():
                    temp_path.unlink()

        except Exception as e:
            await message.reply(
                f"[ERROR] Error processing {attachment.filename}: {str(e)}"
            )
            logger.error(f"Attachment processing error: {e}")


async def handle_markdown_intake(message: discord.Message):
    """Handle markdown content intake and save to ideasheets."""
    user = message.author
    content = (message.content or "").strip()

    try:
        # Generate filename from first line or timestamp
        title = None
        first_line = content.split("\n", 1)[0].strip() if content else ""
        if first_line.startswith("#"):
            title = first_line.lstrip("#").strip()
            filename_base = "".join(
                c for c in title if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            filename_base = filename_base.replace(" ", "-").lower()[:50]
        else:
            filename_base = f"idea-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        filename = f"{filename_base}.md"

        # Generate AI tags
        try:
            tags = await ai_helper.generate_tags(content)
        except Exception:
            tags = ["idea", "user-submitted"]

        md_title = title if title else "Untitled Idea"
        markdown_content = f"""# {md_title}

**Author:** {user.display_name}
**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Tags:** {", ".join(tags)}


{content}
"""

        ideasheets_dir = Path(
            getattr(config, "ideasheets_dir", Path("docs/ideasheets"))
        )
        output_dir = Path(getattr(config, "output_dir", Path("output")))
        ideasheets_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = ideasheets_dir / filename
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(markdown_content)

        # Create HTML and PDF versions
        html_title = title.replace("-", " ").title() if title else "Untitled Idea"
        html_content = await file_processor.markdown_to_html(
            markdown_content, html_title
        )

        html_path = output_dir / f"{filename_base}.html"
        pdf_path = output_dir / f"{filename_base}.pdf"

        async with aiofiles.open(html_path, "w", encoding="utf-8") as f:
            await f.write(html_content)

        pdf_success = await file_processor.html_to_pdf(html_content, pdf_path)

        # Confirmation
        embed = discord.Embed(
            title="[SUCCESS] Idea Sheet Saved",
            description=f"**File:** `{filename}`\n**Tags:** {', '.join(tags)}",
            color=0x2ECC71,
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text=f"Saved by {user.display_name}")

        files_to_send = []
        if html_path.exists():
            files_to_send.append(discord.File(str(html_path)))
        if pdf_success and pdf_path.exists():
            files_to_send.append(discord.File(str(pdf_path)))

        if files_to_send:
            await message.reply(embed=embed, files=files_to_send)
        else:
            await message.reply(embed=embed)

        # Store in conversation memory (best-effort)
        with contextlib.suppress(Exception):
            await memory.store_conversation(
                user.id,
                f"Submitted idea sheet: {filename}",
                f"Saved with tags: {', '.join(tags)}",
            )

        logger.info(f"Idea sheet saved: {filename} by {user.display_name}")

    except Exception as e:
        await message.reply(f"[ERROR] Failed to save idea sheet: {str(e)}")
        logger.error(f"Markdown intake error: {e}")


async def handle_dm_conversation(message: discord.Message):
    """Handle regular DM conversation with memory."""
    user = message.author
    content = message.content or ""

    # Attempt to load recent history; ignore failures
    history = []
    import contextlib

    with contextlib.suppress(Exception):
        history = await memory.get_conversation_history(user.id, limit=5)

    response = "Thanks for your message! I've noted it down. You can use `/submit-idea` to submit ideas, or send markdown directly."
    if history:
        response += f"\n\nWe've had {len(history)} previous conversations."

    await message.reply(response)

    # Best-effort store; ignore storage errors
    with contextlib.suppress(Exception):
        await memory.store_conversation(user.id, content, response)


# -----------------------------------------------------------------------------
# Guild message handling (code analysis)
# -----------------------------------------------------------------------------
async def handle_guild_message(message: discord.Message):
    """Handle guild messages for code analysis and monitoring."""
    if "```" in (message.content or ""):
        await analyze_code_in_message(message)


async def analyze_code_in_message(message: discord.Message):
    """Analyze code blocks in messages and suggest improvements."""
    content = message.content or ""
    code_blocks: List[Tuple[str, str]] = []

    # Extract simple code blocks
    parts = content.split("```")
    for i in range(1, len(parts), 2):
        block = parts[i].strip()
        lines = block.split("\n")
        if lines and not any(c.isspace() for c in lines[0]) and len(lines[0]) < 20:
            language = lines[0]
            code = "\n".join(lines[1:])
        else:
            try:
                language = await file_processor.detect_language(block)
            except Exception:
                language = "text"
            code = block
        code_blocks.append((language, code))

    for language, code in code_blocks:
        if language.lower() == "python" and len(code.strip()) > 50:
            issues = await code_analyzer.lint_python_code(code)
            if len(issues) > 1 or (
                len(issues) == 1 and not issues[0].startswith("[SUCCESS]")
            ):
                try:
                    thread = await message.create_thread(
                        name=f"Code Review - {message.author.display_name}",
                        auto_archive_duration=1440,
                    )

                    embed = discord.Embed(
                        title="🔍 Code Analysis Results",
                        description="\n".join(issues[:10]),
                        color=0xE74C3C
                        if any("[ERROR]" in issue for issue in issues)
                        else 0xF39C12,
                    )

                    if getattr(ai_helper, "available", False):
                        unit_tests = await ai_helper.generate_unit_tests(code, language)
                        if unit_tests and len(unit_tests) > 100:
                            trunc = unit_tests[:800]
                            embed.add_field(
                                name="🧪 Suggested Unit Tests",
                                value=f"```python\n{trunc}\n```",
                                inline=False,
                            )

                    await thread.send(embed=embed)

                except Exception as e:
                    logger.error(f"Code analysis thread creation failed: {e}")


# -----------------------------------------------------------------------------
# Slash Commands
# -----------------------------------------------------------------------------
@bot.tree.command(
    name="submit-idea", description="Submit a new idea to the ideasheets collection"
)
@app_commands.describe(
    title="Title of your idea",
    description="Detailed description of your idea",
    tags="Comma-separated tags (optional)",
)
async def submit_idea_command(
    interaction: discord.Interaction,
    title: str,
    description: str,
    tags: Optional[str] = None,
):
    await interaction.response.defer()

    try:
        user = interaction.user

        filename_base = "".join(
            c for c in title if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        filename_base = filename_base.replace(" ", "-").lower()[:50]
        filename = f"{filename_base}.md"

        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        else:
            try:
                tag_list = await ai_helper.generate_tags(f"{title}\n{description}")
            except Exception:
                tag_list = ["idea"]

        markdown_content = f"""# {title}

**Author:** {user.display_name}
**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Tags:** {", ".join(tag_list)}

---

{description}
"""

        ideasheets_dir = Path(
            getattr(config, "ideasheets_dir", Path("docs/ideasheets"))
        )
        output_dir = Path(getattr(config, "output_dir", Path("output")))
        ideasheets_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = ideasheets_dir / filename
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(markdown_content)

        html_content = await file_processor.markdown_to_html(markdown_content, title)
        html_path = output_dir / f"{filename_base}.html"
        pdf_path = output_dir / f"{filename_base}.pdf"

        async with aiofiles.open(html_path, "w", encoding="utf-8") as f:
            await f.write(html_content)

        pdf_success = await file_processor.html_to_pdf(html_content, pdf_path)

        embed = discord.Embed(
            title="[SUCCESS] Idea Submitted Successfully",
            description=f"**Title:** {title}\n**File:** `{filename}`\n**Tags:** {', '.join(tag_list)}",
            color=0x2ECC71,
            timestamp=datetime.utcnow(),
        )

        files_to_send = []
        if html_path.exists():
            files_to_send.append(discord.File(str(html_path)))
        if pdf_success and pdf_path.exists():
            files_to_send.append(discord.File(str(pdf_path)))

        if files_to_send:
            await interaction.followup.send(embed=embed, files=files_to_send)
        else:
            await interaction.followup.send(embed=embed)

        # Best-effort store; suppress expected storage errors
        with contextlib.suppress(Exception):
            await memory.store_conversation(
                user.id,
                f"Submitted idea: {title}",
                f"Saved as {filename} with tags: {', '.join(tag_list)}",
            )

        logger.info(
            f"Idea submitted via slash command: {filename} by {user.display_name}"
        )

    except Exception as e:
        await interaction.followup.send(f"[ERROR] Failed to submit idea: {str(e)}")
        logger.error(f"Submit idea error: {e}")


@bot.tree.command(
    name="get-doc", description="Retrieve a document from ideasheets or helpdocs"
)
@app_commands.describe(
    filename="Name of the file to retrieve", format="Output format (markdown/html/pdf)"
)
@app_commands.choices(
    format=[
        app_commands.Choice(name="Markdown", value="markdown"),
        app_commands.Choice(name="HTML", value="html"),
        app_commands.Choice(name="PDF", value="pdf"),
    ]
)
async def get_doc_command(
    interaction: discord.Interaction, filename: str, format: str = "markdown"
):
    await interaction.response.defer()

    try:
        search_paths = [
            Path(getattr(config, "ideasheets_dir", Path("docs/ideasheets"))) / filename,
            Path(getattr(config, "ideasheets_dir", Path("docs/ideasheets")))
            / f"{filename}.md",
            Path(getattr(config, "helpdocs_dir", Path("docs/helpdocs"))) / filename,
            Path(getattr(config, "output_dir", Path("output"))) / filename,
        ]

        found_file: Optional[Path] = None
        for path in search_paths:
            if path.exists():
                found_file = path
                break

        if not found_file:
            all_files = list(
                Path(getattr(config, "ideasheets_dir", Path("docs/ideasheets"))).glob(
                    "*.md"
                )
            ) + list(
                Path(getattr(config, "helpdocs_dir", Path("docs/helpdocs"))).glob("*")
            )
            matches = [f for f in all_files if filename.lower() in f.name.lower()]

            if matches:
                match_list = "\n".join([f"• `{f.name}`" for f in matches[:10]])
                await interaction.followup.send(
                    f"❓ File not found. Did you mean one of these?\n{match_list}"
                )
            else:
                await interaction.followup.send(
                    f"[ERROR] Document '{filename}' not found."
                )
            return

        # Security: ensure the resolved file is within allowed directories
        allowed_dirs = [
            Path(getattr(config, "ideasheets_dir", Path("docs/ideasheets"))).resolve(),
            Path(getattr(config, "helpdocs_dir", Path("docs/helpdocs"))).resolve(),
            Path(getattr(config, "output_dir", Path("output"))).resolve(),
        ]
        try:
            resolved = found_file.resolve()
            if not any(str(resolved).startswith(str(d)) for d in allowed_dirs):
                await interaction.followup.send("❌ Access to the requested file is not allowed.")
                return
        except Exception:
            await interaction.followup.send("❌ Unable to resolve requested file path.")
            return

        output_dir = Path(getattr(config, "output_dir", Path("output")))
        output_dir.mkdir(parents=True, exist_ok=True)

        if format == "markdown" or found_file.suffix == ".md":
            async with aiofiles.open(found_file, encoding="utf-8") as f:
                content = await f.read()

            if len(content) > 1900:
                await interaction.followup.send(
                    f"📄 Document: `{found_file.name}`",
                    file=discord.File(str(found_file)),
                )
            else:
                embed = discord.Embed(
                    title=f"📄 {found_file.name}",
                    description=f"```markdown\n{content}\n```",
                    color=0x3498DB,
                )
                await interaction.followup.send(embed=embed)

        elif format == "html":
            if found_file.suffix == ".md":
                async with aiofiles.open(found_file, encoding="utf-8") as f:
                    md_content = await f.read()

                html_content = await file_processor.markdown_to_html(
                    md_content, found_file.stem
                )
                html_path = output_dir / f"{found_file.stem}.html"

                async with aiofiles.open(html_path, "w", encoding="utf-8") as f:
                    await f.write(html_content)

                await interaction.followup.send(
                    f"🌐 HTML version of `{found_file.name}`",
                    file=discord.File(str(html_path)),
                )
            else:
                await interaction.followup.send(
                    f"[ERROR] Cannot convert {found_file.suffix} to HTML"
                )

        elif format == "pdf":
            if found_file.suffix == ".md":
                async with aiofiles.open(found_file, encoding="utf-8") as f:
                    md_content = await f.read()

                html_content = await file_processor.markdown_to_html(
                    md_content, found_file.stem
                )
                pdf_path = output_dir / f"{found_file.stem}.pdf"

                pdf_success = await file_processor.html_to_pdf(html_content, pdf_path)

                if pdf_success:
                    await interaction.followup.send(
                        f"📕 PDF version of `{found_file.name}`",
                        file=discord.File(str(pdf_path)),
                    )
                else:
                    await interaction.followup.send("[ERROR] Failed to generate PDF")
            else:
                await interaction.followup.send(
                    f"[ERROR] Cannot convert {found_file.suffix} to PDF"
                )

    except Exception as e:
        await interaction.followup.send(f"[ERROR] Error retrieving document: {str(e)}")
        logger.error(f"Get doc error: {e}")


@bot.tree.command(name="ask", description="Ask a quick question to the team")
@app_commands.describe(question="The question you want to ask")
@cooldown(30)  # 30 second cooldown
@log_command_execution(logger)
async def ask_command(interaction: discord.Interaction, question: str):
    embed = discord.Embed(
        title="❓ Team Question",
        description=question,
        color=0x3498DB,
        timestamp=datetime.utcnow(),
    )
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.avatar.url
        if getattr(interaction.user, "avatar", None)
        else None,
    )
    embed.set_footer(text="Use this thread to discuss the question")

    await interaction.response.send_message(embed=embed)

    try:
        message = await interaction.original_response()
        thread = await message.create_thread(
            name=f"Q: {question[:50]}{'...' if len(question) > 50 else ''}",
            auto_archive_duration=1440,
        )
        await thread.send(
            "💬 Discussion thread created! Reply here to discuss this question."
        )

        # If OpenAI is available, try to provide a helpful response
        if get_openai_api_key():
            try:
                client = await get_openai_client()
                response = await client.answer_question(question)
                if response:
                    chunks = chunker.chunk_text(response)
                    if len(chunks) > 1:
                        chunks = chunker.add_chunk_indicators(chunks)
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            await thread.send(f"[AI] **AI Suggestion:**\n{chunk}")
                        else:
                            await thread.send(chunk)
            except Exception as e:
                logger.warning(f"Could not generate AI response: {e}")

    except Exception as e:
        logger.error(f"Failed to create thread: {e}")


@bot.tree.command(
    name="summarize", description="Request a summary of recent discussions"
)
@app_commands.describe(
    channel="Channel to summarize (default: current channel)",
    hours="Hours to look back (default: 24)",
)
@cooldown(60)  # 60 second cooldown
@log_command_execution(logger)
async def summarize_command(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
    hours: int = 24,
):
    target_channel = channel or interaction.channel  # type: ignore

    await interaction.response.defer()

    try:
        threshold = datetime.utcnow() - timedelta(hours=hours)

        messages: List[Dict[str, Any]] = []
        async for msg in target_channel.history(  # type: ignore
            limit=100, after=threshold, oldest_first=False
        ):
            if not msg.author.bot and (msg.content or "").strip():
                messages.append(
                    {
                        "author": msg.author.display_name,
                        "content": msg.content,
                        "timestamp": msg.created_at,
                        "reactions": sum(r.count for r in msg.reactions)
                        if msg.reactions
                        else 0,
                    }
                )

        if not messages:
            await interaction.followup.send(
                f"📭 No messages found in {target_channel.mention} from the last {hours} hours."
            )
            return

        analysis = await parse_discord_messages(messages)

        summary_text = (
            f"**📊 Summary of {target_channel.mention} - Last {hours} hours**\n\n"
            f"**Messages analyzed:** {analysis['total_messages']}\n"
            f"**Unique users:** {analysis['unique_users']}\n"
            f"**Time period:** {threshold.strftime('%Y-%m-%d %H:%M')} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n\n"
            "**👥 Participation:**\n"
        )

        user_stats = analysis.get("user_stats", {})
        sorted_users = sorted(
            user_stats.items(), key=lambda x: x[1].get("message_count", 0), reverse=True
        )

        for author, stats in sorted_users[:10]:
            summary_text += f"• {author}: {stats.get('message_count', 0)} messages, {stats.get('reactions_received', 0)} reactions\n"

        if analysis.get("most_active_hours"):
            summary_text += "\n**⏰ Most Active Hours:**\n"
            for hour, count in analysis["most_active_hours"][:3]:
                summary_text += f"• {int(hour):02d}:00 - {count} messages\n"

        highlights = [m for m in messages if int(m.get("reactions", 0)) > 0]
        if highlights:
            summary_text += "\n**⭐ Highlighted Messages:**\n"
            for m in sorted(highlights, key=lambda x: x["reactions"], reverse=True)[:3]:
                content = chunker.truncate_with_ellipsis(m["content"], 100)
                summary_text += (
                    f"• **{m['author']}** ({m['reactions']} 👍): {content}\n"
                )

        ai_summary = None
        if get_openai_api_key() and len(messages) >= 5:
            try:
                context = "\n".join(
                    [f"{m['author']}: {m['content'][:200]}" for m in messages[:20]]
                )
                client = await get_openai_client()
                ai_summary = await client.summarize_text(context, max_length=300)
            except Exception as e:
                logger.warning(f"Could not generate AI summary: {e}")

        embed = discord.Embed(
            title="📈 Channel Summary", color=0x2ECC71, timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")

        summary_chunks = chunker.chunk_for_embed_description(summary_text)
        embed.description = summary_chunks[0]
        await interaction.followup.send(embed=embed)

        if len(summary_chunks) > 1:
            for chunk in summary_chunks[1:]:
                continuation_embed = discord.Embed(description=chunk, color=0x2ECC71)
                await interaction.followup.send(embed=continuation_embed)

        if ai_summary:
            ai_embed = discord.Embed(
                title="[AI] AI Summary", description=ai_summary, color=0x9B59B6
            )
            await interaction.followup.send(embed=ai_embed)

    except Exception as e:
        logger.error(f"Error in summarize command: {e}", exc_info=True)
        await interaction.followup.send(
            f"[ERROR] Sorry, I encountered an error while generating the summary: {str(e)}"
        )


@app_commands.command(name="health", description="Show system health status")
@app_commands.describe(detailed="Show detailed health information")
@cooldown(30)  # 30 second cooldown
@log_command_execution(logger)
async def health_command(interaction: discord.Interaction, detailed: bool = False):
    """Show system health status."""
    await interaction.response.defer()

    try:
        if health_monitor:
            health_status = await health_monitor.check_all_health()

            # Create embed
            status_colors = {
                "healthy": 0x2ECC71,  # Green
                "warning": 0xF39C12,  # Orange
                "critical": 0xE74C3C,  # Red
                "unknown": 0x95A5A6,  # Gray
            }

            embed = discord.Embed(
                title="🏥 System Health Status",
                color=status_colors.get(health_status.overall_status, 0x95A5A6),
                timestamp=datetime.utcnow(),
            )

            # Overall status
            status_emoji = {
                "healthy": "[OK]",
                "warning": "[WARN]",
                "critical": "[CRIT]",
                "unknown": "❓",
            }

            embed.add_field(
                name="Overall Status",
                value=f"{status_emoji.get(health_status.overall_status, '❓')} {health_status.overall_status.title()}",
                inline=False,
            )

            # Add key metrics
            if detailed:
                for name, metric in health_status.metrics.items():
                    emoji = status_emoji.get(metric.status, "❓")
                    value = f"{emoji} {metric.message}"
                    if metric.value is not None and metric.threshold is not None:
                        value += f"\nValue: {metric.value:.1f} (threshold: {metric.threshold})"

                    embed.add_field(
                        name=name.replace("_", " ").title(), value=value, inline=True
                    )
            else:
                # Summary view
                healthy_count = sum(
                    1 for m in health_status.metrics.values() if m.status == "healthy"
                )
                warning_count = sum(
                    1 for m in health_status.metrics.values() if m.status == "warning"
                )
                critical_count = sum(
                    1 for m in health_status.metrics.values() if m.status == "critical"
                )

                embed.add_field(
                    name="Health Summary",
                    value=f"[OK] Healthy: {healthy_count}\n[WARN] Warning: {warning_count}\n[CRIT] Critical: {critical_count}",
                    inline=False,
                )

            # Add resource stats
            try:
                resource_stats = await get_resource_stats()
                if resource_stats:
                    stats_text = ""
                    if "memory" in resource_stats:
                        stats_text += f"Memory: {resource_stats['memory'].get('gc_counts', [0])[0]} objects\n"
                    if "http_sessions" in resource_stats:
                        stats_text += f"HTTP Sessions: {resource_stats['http_sessions'].get('active_sessions', 0)}\n"
                    if "files" in resource_stats:
                        stats_text += f"Temp Files: {resource_stats['files'].get('active_files', 0)}\n"

                    if stats_text:
                        embed.add_field(
                            name="Resource Usage", value=stats_text, inline=True
                        )
            except Exception as e:
                logger.warning(f"Failed to get resource stats: {e}")

            # Add circuit breaker status
            try:
                if circuit_manager:
                    cb_stats = circuit_manager.get_health_status()
                    cb_text = f"Breakers: {cb_stats['total_breakers']}\n"
                    cb_text += f"Open: {cb_stats['open_breakers']}\n"
                    cb_text += f"Half-Open: {cb_stats['half_open_breakers']}"

                    embed.add_field(name="Circuit Breakers", value=cb_text, inline=True)
            except Exception as e:
                logger.warning(f"Failed to get circuit breaker stats: {e}")

            embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)

        else:
            await interaction.followup.send(
                "[ERROR] Health monitoring is not available. Basic features only.",
                ephemeral=True,
            )

    except Exception as e:
        logger.error(f"Error in health command: {e}", exc_info=True)
        await interaction.followup.send(
            f"[ERROR] Error checking system health: {str(e)}", ephemeral=True
        )


bot.tree.add_command(health_command)


# -----------------------------------------------------------------------------
# Traditional Commands
# -----------------------------------------------------------------------------
@bot.command(name="createpr")
async def create_pr_command(
    ctx: commands.Context, repo_name: str, title: str, *, body: str = ""
):
    """Create a GitHub pull request."""
    if not getattr(github_helper, "available", False):
        await ctx.send("[ERROR] GitHub integration not available (token required)")
        return

    try:
        result = await github_helper.create_pr(
            repo_name=repo_name,
            title=title,
            body=body
            or f"Pull request created by {ctx.author.display_name} via Discord bot",
            head_branch="feature-branch",  # TODO: make dynamic
            base_branch="main",
        )
        await ctx.send(result)
    except Exception as e:
        await ctx.send(f"[ERROR] Error creating PR: {str(e)}")


@bot.command(name="google")
async def google_command(ctx: commands.Context, *, query: str):
    """Search the web using DuckDuckGo."""
    await ctx.send("🔍 Searching...")

    try:
        results = await web_search.google_search(query, limit=3)

        if results and results[0].get("title") != "Search unavailable":
            embed = discord.Embed(
                title=f"🔍 Search Results: {query}",
                color=0x3498DB,
                timestamp=datetime.utcnow(),
            )

            for i, result in enumerate(results, 1):
                title = (result.get("title") or "")[:100]
                url = result.get("url") or ""
                snippet = (result.get("snippet") or "")[:100]
                embed.add_field(
                    name=f"{i}. {title}",
                    value=f"[Link]({url})\n{snippet}...",
                    inline=False,
                )

            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)
        else:
            await ctx.send("[ERROR] Search results unavailable at the moment")

    except Exception as e:
        await ctx.send(f"[ERROR] Search error: {str(e)}")


@bot.command(name="github_issues")
async def github_issues_command(
    ctx: commands.Context, repo_name: str, state: str = "open", limit: int = 5
):
    """Get GitHub issues for a repository."""
    if not getattr(github_helper, "available", False):
        await ctx.send("[ERROR] GitHub integration not available (token required)")
        return

    try:
        issues = await github_helper.get_issues(repo_name, state, limit)

        if issues:
            embed = discord.Embed(
                title=f"[ISSUES] GitHub Issues: {repo_name}",
                description=f"Showing {len(issues)} {state} issues",
                color=0xE74C3C if state == "open" else 0x2ECC71,
                timestamp=datetime.utcnow(),
            )

            for issue in issues:
                embed.add_field(
                    name=f"#{issue['number']} - {issue['title'][:50]}",
                    value=f"[View Issue]({issue['url']})\nCreated: {issue['created_at'][:10]}",
                    inline=True,
                )

            await ctx.send(embed=embed)
        else:
            await ctx.send(f"[INFO] No {state} issues found for {repo_name}")

    except Exception as e:
        await ctx.send(f"[ERROR] Error fetching issues: {str(e)}")


# -----------------------------------------------------------------------------
# Error handling and lifecycle
# -----------------------------------------------------------------------------
@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    """Handle command errors."""
    logger.error(
        f"Command error in {getattr(ctx, 'command', None)}: {error}", exc_info=True
    )
    with contextlib.suppress(Exception):
        await ctx.send(f"[ERROR] Command error: {str(error)}")


@bot.event
async def on_application_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    """Handle slash command errors."""
    logger.error(f"Slash command error: {error}", exc_info=True)
    if not interaction.response.is_done():
        with contextlib.suppress(Exception):
            await interaction.response.send_message(
                f"[ERROR] An error occurred: {str(error)}", ephemeral=True
            )


@bot.event
async def on_disconnect():
    """Handle bot disconnect."""
    log_bot_event(logger, "bot_disconnect")


@bot.event
async def on_resumed():
    """Handle bot resume."""
    log_bot_event(logger, "bot_resumed")


# -----------------------------------------------------------------------------
# Health Check Functions
# -----------------------------------------------------------------------------
async def check_discord_health() -> Dict[str, Any]:
    """Check Discord connection health."""
    try:
        if bot.is_ready() and not bot.is_closed():
            latency_ms = bot.latency * 1000
            status = "healthy"
            if latency_ms > 1000:
                status = "critical"
            elif latency_ms > 500:
                status = "warning"

            return {
                "status": status,
                "value": latency_ms,
                "threshold": 500,
                "message": f"Latency: {latency_ms:.1f}ms, Guilds: {len(bot.guilds)}",
            }
        else:
            return {
                "status": "critical",
                "value": None,
                "message": "Bot is not ready or connection is closed",
            }
    except Exception as e:
        return {
            "status": "critical",
            "value": None,
            "message": f"Health check failed: {e}",
        }


async def check_openai_health() -> Dict[str, Any]:
    """Check OpenAI service health."""
    try:
        if OpenAIWrapper and _openai_client:
            health_status = await _openai_client.get_health_status()
            return {
                "status": health_status["status"],
                "value": health_status["stats"]["success_rate"],
                "threshold": 0.8,
                "message": health_status["message"],
            }
        else:
            return {
                "status": "warning",
                "value": None,
                "message": "OpenAI service not configured",
            }
    except Exception as e:
        return {
            "status": "warning",
            "value": None,
            "message": f"OpenAI health check failed: {e}",
        }


async def check_database_health() -> Dict[str, Any]:
    """Check database connection health."""
    try:
        # Simple database health check
        if hasattr(memory, "db_path") and memory.db_path:
            # Try a simple query
            await memory.get_conversation_history(0, limit=1)
            return {
                "status": "healthy",
                "value": 1,
                "message": "Database connection active",
            }
        else:
            return {
                "status": "warning",
                "value": 0,
                "message": "Database not configured",
            }
    except Exception as e:
        return {
            "status": "warning",
            "value": None,
            "message": f"Database health check failed: {e}",
        }


async def cleanup():
    """Cleanup resources before shutdown."""
    logger.info("Starting cleanup process")

    # Stop health monitoring
    try:
        await stop_health_monitoring()
        logger.info("Health monitoring stopped")
    except Exception as e:
        logger.warning(f"Failed to stop health monitoring: {e}")

    # Cleanup managed resources
    try:
        await cleanup_resources()
        logger.info("Managed resources cleaned up")
    except Exception as e:
        logger.warning(f"Failed to cleanup managed resources: {e}")

    global _openai_client
    # Best-effort cleanup of client and thread pool; suppress expected errors
    with contextlib.suppress(Exception):
        if _openai_client and hasattr(_openai_client, "close"):
            await _openai_client.close()

    with contextlib.suppress(Exception):
        await shutdown_thread_pool()

    logger.info("Cleanup completed")


def main():
    """Main function to run the bot."""
    # Validate configuration
    try:
        is_valid, messages = config.validate_config()
        for message in messages:
            if "required" in message.lower():
                logger.error(message)
            else:
                logger.warning(message)
        if not is_valid:
            logger.error(
                "Bot configuration is invalid! Please check your environment variables."
            )
    except Exception as e:
        logger.warning(f"Config validation failed/skipped: {e}")

    # Startup info
    with contextlib.suppress(Exception):
        logger.info("Starting Discord bot...")
        logger.info("Features available:")
        logger.info(
            f"  - AI Integration: {'[OK]' if getattr(ai_helper, 'available', False) else '[ERROR]'}"
        )
        logger.info(
            f"  - GitHub Integration: {'[OK]' if getattr(github_helper, 'available', False) else '[ERROR]'}"
        )
        admin_ids = getattr(config, "admin_user_ids", []) or []
        logger.info(f"  - Admin Users: {len(admin_ids)}")

    token = get_discord_token()
    if not token:
        logger.error(
            "Missing Discord token. Set DISCORD_BOT_TOKEN or config.discord_token."
        )
        return

    # Graceful shutdown signals (best-effort; may not work on Windows)
    with contextlib.suppress(Exception):

        def _signal_handler(signum, _frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            with contextlib.suppress(RuntimeError):
                loop = asyncio.get_event_loop()
                loop.create_task(cleanup())

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid Discord bot token!")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        with contextlib.suppress(Exception):
            asyncio.run(cleanup())


if __name__ == "__main__":
    main()
