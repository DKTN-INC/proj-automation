```python name=bot/main.py
#!/usr/bin/env python3
"""
Discord Bot for Project Automation

Provides /ask and /summarize commands for team collaboration.
Full-featured bot with AI integration, file processing, and automation.
"""

import os
import asyncio
import logging
import signal
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Callable, Any, Dict, Tuple

import aiofiles
import discord
from discord.ext import commands
from discord import app_commands

# -----------------------------------------------------------------------------
# Imports from our package with fallbacks for direct execution
# -----------------------------------------------------------------------------
try:
    from .config import config  # config object with directories, tokens, validation, etc.
    from .utils import (
        memory, ai_helper, file_processor, code_analyzer,
        github_helper, web_search
    )
except ImportError:
    from config import config  # type: ignore
    from utils import (       # type: ignore
        memory, ai_helper, file_processor, code_analyzer,
        github_helper, web_search
    )

# Optional advanced modules (structured logging, cooldowns, OpenAI wrapper, thread pool)
try:
    from .logging_config import setup_logging, log_command_execution, log_bot_event  # type: ignore
except Exception:
    try:
        from logging_config import setup_logging, log_command_execution, log_bot_event  # type: ignore
    except Exception:
        # Fallbacks
        setup_logging = None  # type: ignore

        def log_command_execution(_logger: logging.Logger) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
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
        def cooldown(_seconds: int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
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
    from .thread_pool import thread_pool, parse_discord_messages, shutdown_thread_pool  # type: ignore
except Exception:
    try:
        from thread_pool import thread_pool, parse_discord_messages, shutdown_thread_pool  # type: ignore
    except Exception:
        thread_pool = None  # type: ignore

        async def parse_discord_messages(messages: List[Dict[str, Any]]) -> Dict[str, Any]:  # type: ignore
            # Minimal fallback analysis
            users: Dict[str, Dict[str, int]] = {}
            hours: Dict[int, int] = {}
            for m in messages:
                a = m.get('author', 'unknown')
                users.setdefault(a, {'message_count': 0, 'reactions_received': 0})
                users[a]['message_count'] += 1
                users[a]['reactions_received'] += int(m.get('reactions', 0))
                ts: datetime = m.get('timestamp') or datetime.utcnow()
                hours[ts.hour] = hours.get(ts.hour, 0) + 1
            most_active = sorted(hours.items(), key=lambda x: x[1], reverse=True)
            return {
                'total_messages': len(messages),
                'unique_users': len(users),
                'user_stats': users,
                'most_active_hours': most_active,
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
        service_name="proj-automation-bot"
    )
else:
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO"), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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

bot = commands.Bot(command_prefix='!', intents=intents)

# Global instances
try:
    # Prefer provided chunker if available
    from utils import MessageChunker  # type: ignore
except Exception:
    MessageChunker = None  # type: ignore

class _BasicChunker:
    MAX_EMBED = 4000
    def chunk_text(self, text: str, size: int = 1800) -> List[str]:
        return [text[i:i+size] for i in range(0, len(text), size)]
    def add_chunk_indicators(self, chunks: List[str]) -> List[str]:
        total = len(chunks)
        return [f"{c}\n\n({i+1}/{total})" for i, c in enumerate(chunks)]
    def truncate_with_ellipsis(self, text: str, max_len: int) -> str:
        return text if len(text) <= max_len else text[:max_len-1] + "…"
    def chunk_for_embed_description(self, text: str) -> List[str]:
        return self.chunk_text(text, size=self.MAX_EMBED - 100)

chunker = (MessageChunker() if MessageChunker else _BasicChunker())

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

    # Sync commands
    try:
        synced = await bot.tree.sync()
        log_bot_event(logger, "commands_synced", command_count=len(synced))
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}", exc_info=True)

@bot.event
async def on_message(message: discord.Message):
    """Handle incoming messages, including DMs."""
    if message.author == bot.user:
        return

    # Handle DM messages
    if isinstance(message.channel, discord.DMChannel):
        await handle_dm_message(message)

    # Handle mentions and code blocks in channels
    elif message.guild:
        await handle_guild_message(message)

    # Process commands
    await bot.process_commands(message)

# -----------------------------------------------------------------------------
# DM handling
# -----------------------------------------------------------------------------
async def handle_dm_message(message: discord.Message):
    """Handle direct messages for markdown intake and file uploads."""
    user = message.author
    content = (message.content or "").strip()

    # Admin uploads to helpdocs
    try:
        if hasattr(config, "is_admin") and config.is_admin(user.id) and message.attachments:
            await handle_admin_file_upload(message)
            return
    except Exception:
        pass

    # Attachments (OCR/transcription) or markdown intake
    if message.attachments:
        await handle_dm_attachments(message)
    elif content.startswith('```') or content.startswith('#') or len(content) > 100:
        await handle_markdown_intake(message)
    else:
        await handle_dm_conversation(message)

async def handle_admin_file_upload(message: discord.Message):
    """Handle admin file uploads to helpdocs directory."""
    user = message.author

    for attachment in message.attachments:
        try:
            file_path = Path(getattr(config, "helpdocs_dir", Path("docs/helpdocs"))) / attachment.filename
            async with aiofiles.open(file_path, 'wb') as f:
                data = await attachment.read()
                await f.write(data)

            await message.reply(f"✅ File `{attachment.filename}` uploaded to helpdocs/")
            logger.info(f"Admin {user.display_name} uploaded {attachment.filename} to helpdocs")
        except Exception as e:
            await message.reply(f"❌ Failed to upload {attachment.filename}: {str(e)}")
            logger.error(f"Admin upload failed: {e}")

async def handle_dm_attachments(message: discord.Message):
    """Handle attachments in DMs (images for OCR, audio for transcription)."""
    for attachment in message.attachments:
        try:
            max_size = getattr(config, "max_file_size", 25 * 1024 * 1024)
            if attachment.size > max_size:
                await message.reply(
                    f"❌ File too large: {attachment.filename} ({attachment.size/1024/1024:.1f}MB > 25MB)"
                )
                continue

            # Download to temp file (synchronous file write)
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(attachment.filename).suffix) as temp_file:
                data = await attachment.read()
                temp_file.write(data)
                temp_path = Path(temp_file.name)

            ctype = attachment.content_type or ""
            if ctype.startswith('image/'):
                # OCR processing
                extracted_text = await file_processor.extract_text_from_image(temp_path)
                if extracted_text:
                    embed = discord.Embed(
                        title="📷 OCR Results",
                        description=f"```\n{extracted_text[:1900]}\n```",
                        color=0x3498db
                    )
                    await message.reply(embed=embed)
                else:
                    await message.reply("❌ No text found in image")

            elif ctype.startswith('audio/'):
                # Audio transcription
                await message.reply("🎵 Processing audio... (this may take a moment)")

                wav_path = temp_path.with_suffix('.wav')
                if await file_processor.convert_audio_to_wav(temp_path, wav_path):
                    transcription = await ai_helper.transcribe_audio(wav_path)

                    embed = discord.Embed(
                        title="🎤 Audio Transcription",
                        description=f"```\n{transcription[:1900]}\n```",
                        color=0x9b59b6
                    )
                    await message.reply(embed=embed)

                    try:
                        wav_path.unlink(missing_ok=True)  # type: ignore
                    except TypeError:
                        # py<3.8 compatibility
                        if wav_path.exists():
                            wav_path.unlink()
                else:
                    await message.reply("❌ Failed to process audio file")

            else:
                await message.reply(f"❓ Unsupported file type: {attachment.filename}")

            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()

        except Exception as e:
            await message.reply(f"❌ Error processing {attachment.filename}: {str(e)}")
            logger.error(f"Attachment processing error: {e}")

async def handle_markdown_intake(message: discord.Message):
    """Handle markdown content intake and save to ideasheets."""
    user = message.author
    content = (message.content or "").strip()

    try:
        # Generate filename from first line or timestamp
        title = None
        first_line = content.split('\n', 1)[0].strip() if content else ""
        if first_line.startswith('#'):
            title = first_line.lstrip('#').strip()
            filename_base = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename_base = filename_base.replace(' ', '-').lower()[:50]
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
**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Tags:** {', '.join(tags)}

---

{content}
"""

        ideasheets_dir = Path(getattr(config, "ideasheets_dir", Path("docs/ideasheets")))
        output_dir = Path(getattr(config, "output_dir", Path("output")))
        ideasheets_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = ideasheets_dir / filename
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(markdown_content)

        # Create HTML and PDF versions
        html_title = (title.replace('-', ' ').title() if title else 'Untitled Idea')
        html_content = await file_processor.markdown_to_html(markdown_content, html_title)

        html_path = output_dir / f"{filename_base}.html"
        pdf_path = output_dir / f"{filename_base}.pdf"

        async with aiofiles.open(html_path, 'w', encoding='utf-8') as f:
            await f.write(html_content)

        pdf_success = await file_processor.html_to_pdf(html_content, pdf_path)

        # Confirmation
        embed = discord.Embed(
            title="✅ Idea Sheet Saved",
            description=f"**File:** `{filename}`\n**Tags:** {', '.join(tags)}",
            color=0x2ecc71,
            timestamp=datetime.utcnow()
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

        # Store in conversation memory
        try:
            await memory.store_conversation(
                user.id,
                f"Submitted idea sheet: {filename}",
                f"Saved with tags: {', '.join(tags)}"
            )
        except Exception:
            pass

        logger.info(f"Idea sheet saved: {filename} by {user.display_name}")

    except Exception as e:
        await message.reply(f"❌ Failed to save idea sheet: {str(e)}")
        logger.error(f"Markdown intake error: {e}")

async def handle_dm_conversation(message: discord.Message):
    """Handle regular DM conversation with memory."""
    user = message.author
    content = message.content or ""

    try:
        history = []
        try:
            history = await memory.get_conversation_history(user.id, limit=5)
        except Exception:
            pass

        response = "Thanks for your message! I've noted it down. You can use `/submit-idea` to submit ideas, or send markdown directly."
        if history:
            response += f"\n\nWe've had {len(history)} previous conversations."

        await message.reply(response)

        try:
            await memory.store_conversation(user.id, content, response)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"DM conversation error: {e}")

# -----------------------------------------------------------------------------
# Guild message handling (code analysis)
# -----------------------------------------------------------------------------
async def handle_guild_message(message: discord.Message):
    """Handle guild messages for code analysis and monitoring."""
    if '```' in (message.content or ""):
        await analyze_code_in_message(message)

async def analyze_code_in_message(message: discord.Message):
    """Analyze code blocks in messages and suggest improvements."""
    content = message.content or ""
    code_blocks: List[Tuple[str, str]] = []

    # Extract simple code blocks
    parts = content.split('```')
    for i in range(1, len(parts), 2):
        block = parts[i].strip()
        lines = block.split('\n')
        if lines and not any(c.isspace() for c in lines[0]) and len(lines[0]) < 20:
            language = lines[0]
            code = '\n'.join(lines[1:])
        else:
            try:
                language = await file_processor.detect_language(block)
            except Exception:
                language = "text"
            code = block
        code_blocks.append((language, code))

    for language, code in code_blocks:
        if language.lower() == 'python' and len(code.strip()) > 50:
            issues = await code_analyzer.lint_python_code(code)
            if len(issues) > 1 or (len(issues) == 1 and not issues[0].startswith('✅')):
                try:
                    thread = await message.create_thread(
                        name=f"Code Review - {message.author.display_name}",
                        auto_archive_duration=1440
                    )

                    embed = discord.Embed(
                        title="🔍 Code Analysis Results",
                        description="\n".join(issues[:10]),
                        color=0xe74c3c if any('❌' in issue for issue in issues) else 0xf39c12
                    )

                    if getattr(ai_helper, "available", False):
                        unit_tests = await ai_helper.generate_unit_tests(code, language)
                        if unit_tests and len(unit_tests) > 100:
                            trunc = unit_tests[:800]
                            embed.add_field(
                                name="🧪 Suggested Unit Tests",
                                value=f"```python\n{trunc}\n```",
                                inline=False
                            )

                    await thread.send(embed=embed)

                except Exception as e:
                    logger.error(f"Code analysis thread creation failed: {e}")

# -----------------------------------------------------------------------------
# Slash Commands
# -----------------------------------------------------------------------------
@bot.tree.command(name='submit-idea', description='Submit a new idea to the ideasheets collection')
@app_commands.describe(
    title='Title of your idea',
    description='Detailed description of your idea',
    tags='Comma-separated tags (optional)'
)
async def submit_idea_command(
    interaction: discord.Interaction,
    title: str,
    description: str,
    tags: Optional[str] = None
):
    await interaction.response.defer()

    try:
        user = interaction.user

        filename_base = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename_base = filename_base.replace(' ', '-').lower()[:50]
        filename = f"{filename_base}.md"

        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        else:
            try:
                tag_list = await ai_helper.generate_tags(f"{title}\n{description}")
            except Exception:
                tag_list = ["idea"]

        markdown_content = f"""# {title}

**Author:** {user.display_name}  
**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Tags:** {', '.join(tag_list)}

---

{description}
"""

        ideasheets_dir = Path(getattr(config, "ideasheets_dir", Path("docs/ideasheets")))
        output_dir = Path(getattr(config, "output_dir", Path("output")))
        ideasheets_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = ideasheets_dir / filename
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(markdown_content)

        html_content = await file_processor.markdown_to_html(markdown_content, title)
        html_path = output_dir / f"{filename_base}.html"
        pdf_path = output_dir / f"{filename_base}.pdf"

        async with aiofiles.open(html_path, 'w', encoding='utf-8') as f:
            await f.write(html_content)

        pdf_success = await file_processor.html_to_pdf(html_content, pdf_path)

        embed = discord.Embed(
            title="✅ Idea Submitted Successfully",
            description=f"**Title:** {title}\n**File:** `{filename}`\n**Tags:** {', '.join(tag_list)}",
            color=0x2ecc71,
            timestamp=datetime.utcnow()
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

        try:
            await memory.store_conversation(
                user.id,
                f"Submitted idea: {title}",
                f"Saved as {filename} with tags: {', '.join(tag_list)}"
            )
        except Exception:
            pass

        logger.info(f"Idea submitted via slash command: {filename} by {user.display_name}")

    except Exception as e:
        await interaction.followup.send(f"❌ Failed to submit idea: {str(e)}")
        logger.error(f"Submit idea error: {e}")

@bot.tree.command(name='get-doc', description='Retrieve a document from ideasheets or helpdocs')
@app_commands.describe(
    filename='Name of the file to retrieve',
    format='Output format (markdown/html/pdf)'
)
@app_commands.choices(format=[
    app_commands.Choice(name='Markdown', value='markdown'),
    app_commands.Choice(name='HTML', value='html'),
    app_commands.Choice(name='PDF', value='pdf')
])
async def get_doc_command(
    interaction: discord.Interaction,
    filename: str,
    format: str = 'markdown'
):
    await interaction.response.defer()

    try:
        search_paths = [
            Path(getattr(config, "ideasheets_dir", Path("docs/ideasheets"))) / filename,
            Path(getattr(config, "ideasheets_dir", Path("docs/ideasheets"))) / f"{filename}.md",
            Path(getattr(config, "helpdocs_dir", Path("docs/helpdocs"))) / filename,
            Path(getattr(config, "output_dir", Path("output"))) / filename
        ]

        found_file: Optional[Path] = None
        for path in search_paths:
            if path.exists():
                found_file = path
                break

        if not found_file:
            all_files = list(Path(getattr(config, "ideasheets_dir", Path("docs/ideasheets"))).glob('*.md')) + \
                        list(Path(getattr(config, "helpdocs_dir", Path("docs/helpdocs"))).glob('*'))
            matches = [f for f in all_files if filename.lower() in f.name.lower()]

            if matches:
                match_list = '\n'.join([f"• `{f.name}`" for f in matches[:10]])
                await interaction.followup.send(f"❓ File not found. Did you mean one of these?\n{match_list}")
            else:
                await interaction.followup.send(f"❌ Document '{filename}' not found.")
            return

        output_dir = Path(getattr(config, "output_dir", Path("output")))
        output_dir.mkdir(parents=True, exist_ok=True)

        if format == 'markdown' or found_file.suffix == '.md':
            async with aiofiles.open(found_file, 'r', encoding='utf-8') as f:
                content = await f.read()

            if len(content) > 1900:
                await interaction.followup.send(
                    f"📄 Document: `{found_file.name}`",
                    file=discord.File(str(found_file))
                )
            else:
                embed = discord.Embed(
                    title=f"📄 {found_file.name}",
                    description=f"```markdown\n{content}\n```",
                    color=0x3498db
                )
                await interaction.followup.send(embed=embed)

        elif format == 'html':
            if found_file.suffix == '.md':
                async with aiofiles.open(found_file, 'r', encoding='utf-8') as f:
                    md_content = await f.read()

                html_content = await file_processor.markdown_to_html(md_content, found_file.stem)
                html_path = output_dir / f"{found_file.stem}.html"

                async with aiofiles.open(html_path, 'w', encoding='utf-8') as f:
                    await f.write(html_content)

                await interaction.followup.send(
                    f"🌐 HTML version of `{found_file.name}`",
                    file=discord.File(str(html_path))
                )
            else:
                await interaction.followup.send(f"❌ Cannot convert {found_file.suffix} to HTML")

        elif format == 'pdf':
            if found_file.suffix == '.md':
                async with aiofiles.open(found_file, 'r', encoding='utf-8') as f:
                    md_content = await f.read()

                html_content = await file_processor.markdown_to_html(md_content, found_file.stem)
                pdf_path = output_dir / f"{found_file.stem}.pdf"

                pdf_success = await file_processor.html_to_pdf(html_content, pdf_path)

                if pdf_success:
                    await interaction.followup.send(
                        f"📕 PDF version of `{found_file.name}`",
                        file=discord.File(str(pdf_path))
                    )
                else:
                    await interaction.followup.send("❌ Failed to generate PDF")
            else:
                await interaction.followup.send(f"❌ Cannot convert {found_file.suffix} to PDF")

    except Exception as e:
        await interaction.followup.send(f"❌ Error retrieving document: {str(e)}")
        logger.error(f"Get doc error: {e}")

@bot.tree.command(name='ask', description='Ask a quick question to the team')
@app_commands.describe(question='The question you want to ask')
@cooldown(30)  # 30 second cooldown
@log_command_execution(logger)
async def ask_command(interaction: discord.Interaction, question: str):
    embed = discord.Embed(
        title="❓ Team Question",
        description=question,
        color=0x3498db,
        timestamp=datetime.utcnow()
    )
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.avatar.url if getattr(interaction.user, "avatar", None) else None
    )
    embed.set_footer(text="Use this thread to discuss the question")

    await interaction.response.send_message(embed=embed)

    try:
        message = await interaction.original_response()
        thread = await message.create_thread(
            name=f"Q: {question[:50]}{'...' if len(question) > 50 else ''}",
            auto_archive_duration=1440
        )
        await thread.send("💬 Discussion thread created! Reply here to discuss this question.")

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
                            await thread.send(f"🤖 **AI Suggestion:**\n{chunk}")
                        else:
                            await thread.send(chunk)
            except Exception as e:
                logger.warning(f"Could not generate AI response: {e}")

    except Exception as e:
        logger.error(f"Failed to create thread: {e}")

@bot.tree.command(name='summarize', description='Request a summary of recent discussions')
@app_commands.describe(
    channel='Channel to summarize (default: current channel)',
    hours='Hours to look back (default: 24)'
)
@cooldown(60)  # 60 second cooldown
@log_command_execution(logger)
async def summarize_command(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
    hours: int = 24
):
    target_channel = channel or interaction.channel  # type: ignore

    await interaction.response.defer()

    try:
        threshold = datetime.utcnow() - timedelta(hours=hours)

        messages: List[Dict[str, Any]] = []
        async for msg in target_channel.history(  # type: ignore
            limit=100,
            after=threshold,
            oldest_first=False
        ):
            if not msg.author.bot and (msg.content or "").strip():
                messages.append({
                    'author': msg.author.display_name,
                    'content': msg.content,
                    'timestamp': msg.created_at,
                    'reactions': sum(r.count for r in msg.reactions) if msg.reactions else 0
                })

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

        user_stats = analysis.get('user_stats', {})
        sorted_users = sorted(user_stats.items(), key=lambda x: x[1].get('message_count', 0), reverse=True)

        for author, stats in sorted_users[:10]:
            summary_text += f"• {author}: {stats.get('message_count', 0)} messages, {stats.get('reactions_received', 0)} reactions\n"

        if analysis.get('most_active_hours'):
            summary_text += "\n**⏰ Most Active Hours:**\n"
            for hour, count in analysis['most_active_hours'][:3]:
                summary_text += f"• {int(hour):02d}:00 - {count} messages\n"

        highlights = [m for m in messages if int(m.get('reactions', 0)) > 0]
        if highlights:
            summary_text += "\n**⭐ Highlighted Messages:**\n"
            for m in sorted(highlights, key=lambda x: x['reactions'], reverse=True)[:3]:
                content = chunker.truncate_with_ellipsis(m['content'], 100)
                summary_text += f"• **{m['author']}** ({m['reactions']} 👍): {content}\n"

        ai_summary = None
        if get_openai_api_key() and len(messages) >= 5:
            try:
                context = "\n".join([f"{m['author']}: {m['content'][:200]}" for m in messages[:20]])
                client = await get_openai_client()
                ai_summary = await client.summarize_text(context, max_length=300)
            except Exception as e:
                logger.warning(f"Could not generate AI summary: {e}")

        embed = discord.Embed(
            title="📈 Channel Summary",
            color=0x2ecc71,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")

        summary_chunks = chunker.chunk_for_embed_description(summary_text)
        embed.description = summary_chunks[0]
        await interaction.followup.send(embed=embed)

        if len(summary_chunks) > 1:
            for chunk in summary_chunks[1:]:
                continuation_embed = discord.Embed(
                    description=chunk,
                    color=0x2ecc71
                )
                await interaction.followup.send(embed=continuation_embed)

        if ai_summary:
            ai_embed = discord.Embed(
                title="🤖 AI Summary",
                description=ai_summary,
                color=0x9b59b6
            )
            await interaction.followup.send(embed=ai_embed)

    except Exception as e:
        logger.error(f"Error in summarize command: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Sorry, I encountered an error while generating the summary: {str(e)}"
        )

# -----------------------------------------------------------------------------
# Traditional Commands
# -----------------------------------------------------------------------------
@bot.command(name='createpr')
async def create_pr_command(ctx: commands.Context, repo_name: str, title: str, *, body: str = ""):
    """Create a GitHub pull request."""
    if not getattr(github_helper, "available", False):
        await ctx.send("❌ GitHub integration not available (token required)")
        return

    try:
        result = await github_helper.create_pr(
            repo_name=repo_name,
            title=title,
            body=body or f"Pull request created by {ctx.author.display_name} via Discord bot",
            head_branch="feature-branch",  # TODO: make dynamic
            base_branch="main"
        )
        await ctx.send(result)
    except Exception as e:
        await ctx.send(f"❌ Error creating PR: {str(e)}")

@bot.command(name='google')
async def google_command(ctx: commands.Context, *, query: str):
    """Search the web using DuckDuckGo."""
    await ctx.send("🔍 Searching...")

    try:
        results = await web_search.google_search(query, limit=3)

        if results and results[0].get('title') != "Search unavailable":
            embed = discord.Embed(
                title=f"🔍 Search Results: {query}",
                color=0x3498db,
                timestamp=datetime.utcnow()
            )

            for i, result in enumerate(results, 1):
                title = (result.get('title') or '')[:100]
                url = result.get('url') or ''
                snippet = (result.get('snippet') or '')[:100]
                embed.add_field(
                    name=f"{i}. {title}",
                    value=f"[Link]({url})\n{snippet}...",
                    inline=False
                )

            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Search results unavailable at the moment")

    except Exception as e:
        await ctx.send(f"❌ Search error: {str(e)}")

@bot.command(name='github_issues')
async def github_issues_command(ctx: commands.Context, repo_name: str, state: str = "open", limit: int = 5):
    """Get GitHub issues for a repository."""
    if not getattr(github_helper, "available", False):
        await ctx.send("❌ GitHub integration not available (token required)")
        return

    try:
        issues = await github_helper.get_issues(repo_name, state, limit)

        if issues:
            embed = discord.Embed(
                title=f"📋 GitHub Issues: {repo_name}",
                description=f"Showing {len(issues)} {state} issues",
                color=0xe74c3c if state == "open" else 0x2ecc71,
                timestamp=datetime.utcnow()
            )

            for issue in issues:
                embed.add_field(
                    name=f"#{issue['number']} - {issue['title'][:50]}",
                    value=f"[View Issue]({issue['url']})\nCreated: {issue['created_at'][:10]}",
                    inline=True
                )

            await ctx.send(embed=embed)
        else:
            await ctx.send(f"📭 No {state} issues found for {repo_name}")

    except Exception as e:
        await ctx.send(f"❌ Error fetching issues: {str(e)}")

# -----------------------------------------------------------------------------
# Error handling and lifecycle
# -----------------------------------------------------------------------------
@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    """Handle command errors."""
    logger.error(f'Command error in {getattr(ctx, "command", None)}: {error}', exc_info=True)
    try:
        await ctx.send(f"❌ Command error: {str(error)}")
    except Exception:
        pass

@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle slash command errors."""
    logger.error(f'Slash command error: {error}', exc_info=True)
    if not interaction.response.is_done():
        try:
            await interaction.response.send_message(
                f"❌ An error occurred: {str(error)}",
                ephemeral=True
            )
        except Exception:
            pass

@bot.event
async def on_disconnect():
    """Handle bot disconnect."""
    log_bot_event(logger, "bot_disconnect")

@bot.event
async def on_resumed():
    """Handle bot resume."""
    log_bot_event(logger, "bot_resumed")

async def cleanup():
    """Cleanup resources before shutdown."""
    logger.info("Starting cleanup process")

    global _openai_client
    try:
        if _openai_client and hasattr(_openai_client, "close"):
            await _openai_client.close()
    except Exception:
        pass

    try:
        await shutdown_thread_pool()
    except Exception:
        pass

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
            logger.error("Bot configuration is invalid! Please check your environment variables.")
    except Exception as e:
        logger.warning(f"Config validation failed/skipped: {e}")

    # Startup info
    try:
        logger.info("Starting Discord bot...")
        logger.info(f"Features available:")
        logger.info(f"  - AI Integration: {'✅' if getattr(ai_helper, 'available', False) else '❌'}")
        logger.info(f"  - GitHub Integration: {'✅' if getattr(github_helper, 'available', False) else '❌'}")
        admin_ids = getattr(config, "admin_user_ids", []) or []
        logger.info(f"  - Admin Users: {len(admin_ids)}")
    except Exception:
        pass

    token = get_discord_token()
    if not token:
        logger.error("Missing Discord token. Set DISCORD_BOT_TOKEN or config.discord_token.")
        return

    # Graceful shutdown signals (best-effort; may not work on Windows)
    try:
        def _signal_handler(signum, _frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(cleanup())
            except RuntimeError:
                pass

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
    except Exception:
        pass

    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid Discord bot token!")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        try:
            asyncio.run(cleanup())
        except Exception:
            pass

if __name__ == '__main__':
    main()
```