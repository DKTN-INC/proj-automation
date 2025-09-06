#!/usr/bin/env python3
"""
Discord Bot for Project Automation
Full-featured bot with AI integration, file processing, and automation
"""

import os
import asyncio
import logging
import tempfile
import aiofiles
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

import discord
from discord.ext import commands
from discord import app_commands

# Bot modules
try:
    from .config import config
    from .utils import (
        memory, ai_helper, file_processor, code_analyzer, 
        github_helper, web_search
    )
except ImportError:
    # Fallback for direct execution
    from config import config
    from utils import (
        memory, ai_helper, file_processor, code_analyzer, 
        github_helper, web_search
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Called when the bot is ready."""
    logger.info(f'{bot.user} has connected to Discord!')
    
    # Initialize database
    await memory.init_db()
    logger.info("Database initialized")
    
    # Validate configuration
    is_valid, messages = config.validate_config()
    for message in messages:
        logger.info(f"Config: {message}")
    
    if not is_valid:
        logger.error("Bot configuration is invalid!")
        return
    
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} command(s)')
    except Exception as e:
        logger.error(f'Failed to sync commands: {e}')

@bot.event
async def on_message(message):
    """Handle incoming messages, including DMs."""
    # Don't respond to self
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

async def handle_dm_message(message):
    """Handle direct messages for markdown intake and file uploads."""
    user = message.author
    content = message.content.strip()
    
    # Handle admin file uploads to helpdocs
    if config.is_admin(user.id) and message.attachments:
        await handle_admin_file_upload(message)
        return
    
    # Handle markdown content or file uploads
    if message.attachments:
        await handle_dm_attachments(message)
    elif content.startswith('```') or content.startswith('#') or len(content) > 100:
        await handle_markdown_intake(message)
    else:
        # Regular conversation
        await handle_dm_conversation(message)

async def handle_admin_file_upload(message):
    """Handle admin file uploads to helpdocs directory."""
    user = message.author
    
    for attachment in message.attachments:
        try:
            # Download file to helpdocs
            file_path = config.helpdocs_dir / attachment.filename
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(await attachment.read())
            
            await message.reply(f"✅ File `{attachment.filename}` uploaded to helpdocs/")
            logger.info(f"Admin {user.display_name} uploaded {attachment.filename} to helpdocs")
            
        except Exception as e:
            await message.reply(f"❌ Failed to upload {attachment.filename}: {str(e)}")
            logger.error(f"Admin upload failed: {e}")

async def handle_dm_attachments(message):
    """Handle attachments in DMs (images for OCR, audio for transcription)."""
    user = message.author
    
    for attachment in message.attachments:
        try:
            # Check file size
            if attachment.size > config.max_file_size:
                await message.reply(f"❌ File too large: {attachment.filename} ({attachment.size/1024/1024:.1f}MB > 25MB)")
                continue
            
            # Download to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(attachment.filename).suffix) as temp_file:
                await temp_file.write(await attachment.read())
                temp_path = Path(temp_file.name)
            
            # Process based on file type
            if attachment.content_type and attachment.content_type.startswith('image/'):
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
            
            elif attachment.content_type and attachment.content_type.startswith('audio/'):
                # Audio transcription
                await message.reply("🎵 Processing audio... (this may take a moment)")
                
                # Convert to WAV if needed
                wav_path = temp_path.with_suffix('.wav')
                if await file_processor.convert_audio_to_wav(temp_path, wav_path):
                    transcription = await ai_helper.transcribe_audio(wav_path)
                    
                    embed = discord.Embed(
                        title="🎤 Audio Transcription",
                        description=f"```\n{transcription[:1900]}\n```",
                        color=0x9b59b6
                    )
                    await message.reply(embed=embed)
                    
                    # Clean up WAV file
                    wav_path.unlink(missing_ok=True)
                else:
                    await message.reply("❌ Failed to process audio file")
            
            else:
                await message.reply(f"❓ Unsupported file type: {attachment.filename}")
            
            # Clean up temp file
            temp_path.unlink(missing_ok=True)
            
        except Exception as e:
            await message.reply(f"❌ Error processing {attachment.filename}: {str(e)}")
            logger.error(f"Attachment processing error: {e}")

async def handle_markdown_intake(message):
    """Handle markdown content intake and save to ideasheets."""
    user = message.author
    content = message.content.strip()
    
    try:
        # Generate filename from first line or timestamp
        first_line = content.split('\n')[0].strip()
        if first_line.startswith('#'):
            title = first_line.lstrip('#').strip()
            filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = filename.replace(' ', '-').lower()[:50]
        else:
            filename = f"idea-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        filename = f"{filename}.md"
        
        # Generate AI tags
        tags = await ai_helper.generate_tags(content)
        
        # Create markdown content with metadata
        markdown_content = f"""# {title if 'title' in locals() else 'Untitled Idea'}

**Author:** {user.display_name}  
**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Tags:** {', '.join(tags)}

---

{content}
"""
        
        # Save to ideasheets directory
        file_path = config.ideasheets_dir / filename
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(markdown_content)
        
        # Create HTML and PDF versions
        html_content = await file_processor.markdown_to_html(
            markdown_content, 
            title.replace('-', ' ').title() if 'title' in locals() else 'Untitled Idea'
        )
        
        html_path = config.output_dir / f"{filename.replace('.md', '.html')}"
        pdf_path = config.output_dir / f"{filename.replace('.md', '.pdf')}"
        
        async with aiofiles.open(html_path, 'w', encoding='utf-8') as f:
            await f.write(html_content)
        
        # Generate PDF
        pdf_success = await file_processor.html_to_pdf(html_content, pdf_path)
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Idea Sheet Saved",
            description=f"**File:** `{filename}`\n**Tags:** {', '.join(tags)}",
            color=0x2ecc71,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Saved by {user.display_name}")
        
        # Add file attachments if available
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
        await memory.store_conversation(
            user.id, 
            f"Submitted idea sheet: {filename}", 
            f"Saved with tags: {', '.join(tags)}"
        )
        
        logger.info(f"Idea sheet saved: {filename} by {user.display_name}")
        
    except Exception as e:
        await message.reply(f"❌ Failed to save idea sheet: {str(e)}")
        logger.error(f"Markdown intake error: {e}")

async def handle_dm_conversation(message):
    """Handle regular DM conversation with memory."""
    user = message.author
    content = message.content
    
    try:
        # Get conversation history
        history = await memory.get_conversation_history(user.id, limit=5)
        
        # Simple response (can be enhanced with AI)
        response = f"Thanks for your message! I've noted it down. You can use `/submit-idea` to formally submit ideas, or send markdown content directly."
        
        if history:
            response += f"\n\nWe've had {len(history)} previous conversations."
        
        await message.reply(response)
        
        # Store conversation
        await memory.store_conversation(user.id, content, response)
        
    except Exception as e:
        logger.error(f"DM conversation error: {e}")

async def handle_guild_message(message):
    """Handle guild messages for code analysis and monitoring."""
    # Check for code blocks
    if '```' in message.content:
        await analyze_code_in_message(message)

async def analyze_code_in_message(message):
    """Analyze code blocks in messages and suggest improvements."""
    content = message.content
    code_blocks = []
    
    # Extract code blocks
    parts = content.split('```')
    for i in range(1, len(parts), 2):
        if i < len(parts):
            code_block = parts[i].strip()
            # Remove language identifier if present
            lines = code_block.split('\n')
            if lines and not any(c.isspace() for c in lines[0]) and len(lines[0]) < 20:
                # First line is likely language identifier
                language = lines[0]
                code = '\n'.join(lines[1:])
            else:
                language = await file_processor.detect_language(code_block)
                code = code_block
            
            code_blocks.append((language, code))
    
    # Analyze Python code blocks
    for language, code in code_blocks:
        if language.lower() == 'python' and len(code.strip()) > 50:
            # Only analyze substantial code blocks
            issues = await code_analyzer.lint_python_code(code)
            
            if len(issues) > 1 or (len(issues) == 1 and not issues[0].startswith('✅')):
                # Create thread for code review
                try:
                    thread = await message.create_thread(
                        name=f"Code Review - {message.author.display_name}",
                        auto_archive_duration=1440
                    )
                    
                    embed = discord.Embed(
                        title="🔍 Code Analysis Results",
                        description="\n".join(issues[:10]),  # Limit to 10 issues
                        color=0xe74c3c if any('❌' in issue for issue in issues) else 0xf39c12
                    )
                    
                    # Generate unit test suggestions
                    if ai_helper.available:
                        unit_tests = await ai_helper.generate_unit_tests(code, language)
                        if len(unit_tests) > 100:  # Only add if substantial
                            embed.add_field(
                                name="🧪 Suggested Unit Tests",
                                value=f"```python\n{unit_tests[:800]}...\n```",
                                inline=False
                            )
                    
                    await thread.send(embed=embed)
                    
                except Exception as e:
                    logger.error(f"Code analysis thread creation failed: {e}")

# =============================================================================
# SLASH COMMANDS
# =============================================================================

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
    tags: str = None
):
    """Handle /submit-idea slash command."""
    await interaction.response.defer()
    
    try:
        user = interaction.user
        
        # Generate filename
        filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = filename.replace(' ', '-').lower()[:50]
        filename = f"{filename}.md"
        
        # Process tags
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        else:
            tag_list = await ai_helper.generate_tags(f"{title}\n{description}")
        
        # Create markdown content
        markdown_content = f"""# {title}

**Author:** {user.display_name}  
**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Tags:** {', '.join(tag_list)}

---

{description}
"""
        
        # Save to ideasheets
        file_path = config.ideasheets_dir / filename
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(markdown_content)
        
        # Generate HTML and PDF
        html_content = await file_processor.markdown_to_html(markdown_content, title)
        html_path = config.output_dir / f"{filename.replace('.md', '.html')}"
        pdf_path = config.output_dir / f"{filename.replace('.md', '.pdf')}"
        
        async with aiofiles.open(html_path, 'w', encoding='utf-8') as f:
            await f.write(html_content)
        
        pdf_success = await file_processor.html_to_pdf(html_content, pdf_path)
        
        # Send response
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
        
        # Store in memory
        await memory.store_conversation(
            user.id,
            f"Submitted idea: {title}",
            f"Saved as {filename} with tags: {', '.join(tag_list)}"
        )
        
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
    """Handle /get-doc slash command."""
    await interaction.response.defer()
    
    try:
        # Search in ideasheets and helpdocs
        search_paths = [
            config.ideasheets_dir / filename,
            config.ideasheets_dir / f"{filename}.md",
            config.helpdocs_dir / filename,
            config.output_dir / filename
        ]
        
        found_file = None
        for path in search_paths:
            if path.exists():
                found_file = path
                break
        
        if not found_file:
            # Search for partial matches
            all_files = list(config.ideasheets_dir.glob('*.md')) + list(config.helpdocs_dir.glob('*'))
            matches = [f for f in all_files if filename.lower() in f.name.lower()]
            
            if matches:
                match_list = '\n'.join([f"• `{f.name}`" for f in matches[:10]])
                await interaction.followup.send(f"❓ File not found. Did you mean one of these?\n{match_list}")
            else:
                await interaction.followup.send(f"❌ Document '{filename}' not found.")
            return
        
        # Read and process the file
        if format == 'markdown' or found_file.suffix == '.md':
            async with aiofiles.open(found_file, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            if len(content) > 1900:
                # Send as file attachment
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
                # Convert markdown to HTML
                async with aiofiles.open(found_file, 'r', encoding='utf-8') as f:
                    md_content = await f.read()
                
                html_content = await file_processor.markdown_to_html(md_content, found_file.stem)
                html_path = config.output_dir / f"{found_file.stem}.html"
                
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
                # Convert markdown to PDF
                async with aiofiles.open(found_file, 'r', encoding='utf-8') as f:
                    md_content = await f.read()
                
                html_content = await file_processor.markdown_to_html(md_content, found_file.stem)
                pdf_path = config.output_dir / f"{found_file.stem}.pdf"
                
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
async def ask_command(interaction: discord.Interaction, question: str):
    """Handle /ask slash command for quick questions."""
    embed = discord.Embed(
        title="❓ Team Question",
        description=question,
        color=0x3498db,
        timestamp=datetime.utcnow()
    )
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.avatar.url if interaction.user.avatar else None
    )
    embed.set_footer(text="Use this thread to discuss the question")
    
    await interaction.response.send_message(embed=embed)
    
    # Create a thread for discussion
    try:
        message = await interaction.original_response()
        thread = await message.create_thread(
            name=f"Q: {question[:50]}{'...' if len(question) > 50 else ''}",
            auto_archive_duration=1440  # 24 hours
        )
        await thread.send("💬 Discussion thread created! Reply here to discuss this question.")
    except Exception as e:
        logger.error(f"Failed to create thread: {e}")

@bot.tree.command(name='summarize', description='Request a summary of recent discussions')
@app_commands.describe(
    channel='Channel to summarize (default: current channel)',
    hours='Hours to look back (default: 24)'
)
async def summarize_command(
    interaction: discord.Interaction, 
    channel: discord.TextChannel = None, 
    hours: int = 24
):
    """Handle /summarize slash command for generating summaries."""
    target_channel = channel or interaction.channel
    
    # Defer response as this might take a while
    await interaction.response.defer()
    
    try:
        # Calculate time threshold
        threshold = datetime.utcnow() - timedelta(hours=hours)
        
        # Collect messages
        messages = []
        async for message in target_channel.history(
            limit=100, 
            after=threshold,
            oldest_first=False
        ):
            if not message.author.bot and message.content.strip():
                messages.append({
                    'author': message.author.display_name,
                    'content': message.content,
                    'timestamp': message.created_at,
                    'reactions': len(message.reactions)
                })
        
        if not messages:
            await interaction.followup.send(
                f"📭 No messages found in {target_channel.mention} from the last {hours} hours."
            )
            return
        
        # Create summary
        summary_text = f"**📊 Summary of {target_channel.mention} - Last {hours} hours**\n\n"
        summary_text += f"**Messages analyzed:** {len(messages)}\n"
        summary_text += f"**Time period:** {threshold.strftime('%Y-%m-%d %H:%M')} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        
        # Group by author
        author_stats = {}
        for msg in messages:
            author = msg['author']
            if author not in author_stats:
                author_stats[author] = {'count': 0, 'reactions': 0}
            author_stats[author]['count'] += 1
            author_stats[author]['reactions'] += msg['reactions']
        
        summary_text += "**👥 Participation:**\n"
        for author, stats in sorted(author_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            summary_text += f"• {author}: {stats['count']} messages, {stats['reactions']} reactions\n"
        
        # Recent highlights (messages with reactions)
        highlights = [msg for msg in messages if msg['reactions'] > 0]
        if highlights:
            summary_text += "\n**⭐ Highlighted Messages:**\n"
            for msg in sorted(highlights, key=lambda x: x['reactions'], reverse=True)[:3]:
                content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                summary_text += f"• **{msg['author']}** ({msg['reactions']} 👍): {content}\n"
        
        # Create embed
        embed = discord.Embed(
            title=f"📈 Channel Summary",
            description=summary_text,
            color=0x2ecc71,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in summarize command: {e}")
        await interaction.followup.send(
            f"❌ Sorry, I encountered an error while generating the summary: {str(e)}"
        )

# =============================================================================
# TRADITIONAL COMMANDS (with ! prefix)
# =============================================================================

@bot.command(name='createpr')
async def create_pr_command(ctx, repo_name: str, title: str, *, body: str = ""):
    """Create a GitHub pull request."""
    if not github_helper.available:
        await ctx.send("❌ GitHub integration not available (token required)")
        return
    
    try:
        # Default to current branch vs main
        result = await github_helper.create_pr(
            repo_name=repo_name,
            title=title,
            body=body or f"Pull request created by {ctx.author.display_name} via Discord bot",
            head_branch="feature-branch",  # This would need to be dynamic
            base_branch="main"
        )
        await ctx.send(result)
    except Exception as e:
        await ctx.send(f"❌ Error creating PR: {str(e)}")

@bot.command(name='google')
async def google_command(ctx, *, query: str):
    """Search the web using DuckDuckGo."""
    await ctx.send("🔍 Searching...")
    
    try:
        results = await web_search.google_search(query, limit=3)
        
        if results and results[0]['title'] != "Search unavailable":
            embed = discord.Embed(
                title=f"🔍 Search Results: {query}",
                color=0x3498db,
                timestamp=datetime.utcnow()
            )
            
            for i, result in enumerate(results, 1):
                embed.add_field(
                    name=f"{i}. {result['title'][:100]}",
                    value=f"[Link]({result['url']})\n{result['snippet'][:100]}...",
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Search results unavailable at the moment")
    
    except Exception as e:
        await ctx.send(f"❌ Search error: {str(e)}")

@bot.command(name='github_issues')
async def github_issues_command(ctx, repo_name: str, state: str = "open", limit: int = 5):
    """Get GitHub issues for a repository."""
    if not github_helper.available:
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

# =============================================================================
# ERROR HANDLING AND STARTUP
# =============================================================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    logger.error(f'Command error in {ctx.command}: {error}')
    await ctx.send(f"❌ Command error: {str(error)}")

@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle slash command errors."""
    logger.error(f'Slash command error: {error}')
    if not interaction.response.is_done():
        await interaction.response.send_message(
            f"❌ An error occurred: {str(error)}", 
            ephemeral=True
        )

def main():
    """Main function to run the bot."""
    # Validate configuration
    is_valid, messages = config.validate_config()
    
    for message in messages:
        if "required" in message:
            logger.error(message)
        else:
            logger.warning(message)
    
    if not is_valid:
        logger.error("Bot configuration is invalid! Please check your environment variables.")
        return
    
    try:
        logger.info("Starting Discord bot...")
        logger.info(f"Features available:")
        logger.info(f"  - AI Integration: {'✅' if ai_helper.available else '❌'}")
        logger.info(f"  - GitHub Integration: {'✅' if github_helper.available else '❌'}")
        logger.info(f"  - Admin Users: {len(config.admin_user_ids)}")
        
        bot.run(config.discord_token)
    except discord.LoginFailure:
        logger.error("Invalid Discord bot token!")
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == '__main__':
    main()