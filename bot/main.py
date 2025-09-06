#!/usr/bin/env python3
"""
Discord Bot for Project Automation
Provides /ask and /summarize commands for team collaboration
Enhanced with async OpenAI integration, cooldowns, structured logging, and thread pools.
"""

import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta

# Import our custom modules
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from config import OPENAI_API_KEY
from logging_config import setup_logging, log_command_execution, log_bot_event
from cooldowns import cooldown, cooldown_manager
from utils import MessageChunker
from openai_wrapper import OpenAIWrapper
from thread_pool import thread_pool, parse_discord_messages, shutdown_thread_pool

# Configure structured logging
logger = setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    structured=os.getenv("STRUCTURED_LOGS", "false").lower() == "true",
    log_file=os.getenv("LOG_FILE"),
    service_name="proj-automation-bot"
)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Global instances
chunker = MessageChunker()
openai_client = None  # Will be initialized when needed

async def get_openai_client() -> OpenAIWrapper:
    """Get or create OpenAI client instance."""
    global openai_client
    
    if openai_client is None:
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        openai_client = OpenAIWrapper(OPENAI_API_KEY)
    
    return openai_client


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    log_bot_event(logger, "bot_ready", user=str(bot.user), guilds=len(bot.guilds))
    
    try:
        synced = await bot.tree.sync()
        log_bot_event(logger, "commands_synced", command_count=len(synced))
    except Exception as e:
        logger.error(f'Failed to sync commands: {e}', exc_info=True)

@bot.tree.command(name='ask', description='Ask a quick question to the team')
@app_commands.describe(question='The question you want to ask')
@cooldown(30)  # 30 second cooldown
@log_command_execution(logger)
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
        
        # If OpenAI is available, try to provide a helpful response
        if OPENAI_API_KEY:
            try:
                client = await get_openai_client()
                response = await client.answer_question(question)
                if response:
                    # Chunk the response if it's too long
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
@cooldown(60)  # 60 second cooldown for more intensive operation
@log_command_execution(logger)
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
        
        # Process messages in thread pool for better performance
        analysis = await parse_discord_messages(messages)
        
        # Create basic summary
        summary_text = f"**📊 Summary of {target_channel.mention} - Last {hours} hours**\n\n"
        summary_text += f"**Messages analyzed:** {analysis['total_messages']}\n"
        summary_text += f"**Unique users:** {analysis['unique_users']}\n"
        summary_text += f"**Time period:** {threshold.strftime('%Y-%m-%d %H:%M')} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        
        # Add user participation stats
        summary_text += "**👥 Participation:**\n"
        user_stats = analysis['user_stats']
        sorted_users = sorted(user_stats.items(), key=lambda x: x[1]['message_count'], reverse=True)
        
        for author, stats in sorted_users[:10]:  # Top 10 users
            summary_text += f"• {author}: {stats['message_count']} messages, {stats['reactions_received']} reactions\n"
        
        # Add activity insights
        if analysis['most_active_hours']:
            summary_text += "\n**⏰ Most Active Hours:**\n"
            for hour, count in analysis['most_active_hours'][:3]:
                summary_text += f"• {hour:02d}:00 - {count} messages\n"
        
        # Recent highlights (messages with reactions)
        highlights = [msg for msg in messages if msg['reactions'] > 0]
        if highlights:
            summary_text += "\n**⭐ Highlighted Messages:**\n"
            for msg in sorted(highlights, key=lambda x: x['reactions'], reverse=True)[:3]:
                content = chunker.truncate_with_ellipsis(msg['content'], 100)
                summary_text += f"• **{msg['author']}** ({msg['reactions']} 👍): {content}\n"
        
        # Try to generate AI summary if available
        ai_summary = None
        if OPENAI_API_KEY and len(messages) >= 5:
            try:
                # Prepare context for AI summarization
                context = "\n".join([f"{msg['author']}: {msg['content'][:200]}" for msg in messages[:20]])
                client = await get_openai_client()
                ai_summary = await client.summarize_text(context, max_length=300)
            except Exception as e:
                logger.warning(f"Could not generate AI summary: {e}")
        
        # Create and send embed
        embed = discord.Embed(
            title=f"📈 Channel Summary",
            color=0x2ecc71,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        
        # Split summary into chunks if needed
        summary_chunks = chunker.chunk_for_embed_description(summary_text)
        
        # Send main summary
        embed.description = summary_chunks[0]
        await interaction.followup.send(embed=embed)
        
        # Send additional chunks if needed
        if len(summary_chunks) > 1:
            for chunk in summary_chunks[1:]:
                continuation_embed = discord.Embed(
                    description=chunk,
                    color=0x2ecc71
                )
                await interaction.followup.send(embed=continuation_embed)
        
        # Send AI summary separately if available
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

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    logger.error(f'Command error: {error}', exc_info=True)

@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle slash command errors."""
    logger.error(f'Slash command error: {error}', exc_info=True)
    if not interaction.response.is_done():
        await interaction.response.send_message(
            f"❌ An error occurred: {str(error)}", 
            ephemeral=True
        )

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
    
    # Close OpenAI client
    global openai_client
    if openai_client:
        await openai_client.close()
    
    # Shutdown thread pool
    await shutdown_thread_pool()
    
    logger.info("Cleanup completed")


def main():
    """Main function to run the bot."""
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable not set!")
        return
    
    try:
        # Set up shutdown handler
        import signal
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            asyncio.create_task(cleanup())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run the bot
        bot.run(token)
        
    except discord.LoginFailure:
        logger.error("Invalid bot token!")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        # Ensure cleanup runs
        try:
            asyncio.run(cleanup())
        except:
            pass

if __name__ == '__main__':
    main()