#!/usr/bin/env python3

"""
Discord Bot for Project Automation
Provides /ask and /summarize commands for team collaboration
"""

import os
import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    logger.info(f"{bot.user} has connected to Discord!")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")


@bot.tree.command(name="ask", description="Ask a quick question to the team")
@app_commands.describe(question="The question you want to ask")
async def ask_command(interaction: discord.Interaction, question: str):
    """Handle /ask slash command for quick questions."""
    embed = discord.Embed(
        title="❓ Team Question",
        description=question,
        color=0x3498DB,
        timestamp=datetime.utcnow(),
    )
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.avatar.url if interaction.user.avatar else None,
    )
    embed.set_footer(text="Use this thread to discuss the question")

    await interaction.response.send_message(embed=embed)

    # Create a thread for discussion
    try:
        message = await interaction.original_response()
        thread = await message.create_thread(
            name=f"Q: {question[:50]}{'...' if len(question) > 50 else ''}",
            auto_archive_duration=1440,  # 24 hours
        )
        await thread.send(
            "💬 Discussion thread created! Reply here to discuss this question."
        )
    except Exception as e:
        logger.error(f"Failed to create thread: {e}")


@bot.tree.command(
    name="summarize", description="Request a summary of recent discussions"
)
@app_commands.describe(
    channel="Channel to summarize (default: current channel)",
    hours="Hours to look back (default: 24)",
)
async def summarize_command(
    interaction: discord.Interaction,
    channel: discord.TextChannel = None,
    hours: int = 24,
):
    """Handle /summarize slash command for generating summaries."""
    target_channel = channel or interaction.channel

    # Defer response as this might take a while
    await interaction.response.defer()

    try:
        # Calculate time threshold
        from datetime import timedelta

        threshold = datetime.utcnow() - timedelta(hours=hours)

        # Collect messages
        messages = []
        async for message in target_channel.history(
            limit=100, after=threshold, oldest_first=False
        ):
            if not message.author.bot and message.content.strip():
                messages.append(
                    {
                        "author": message.author.display_name,
                        "content": message.content,
                        "timestamp": message.created_at,
                        "reactions": len(message.reactions),
                    }
                )

        if not messages:
            await interaction.followup.send(
                f"📭 No messages found in {target_channel.mention} from the last {hours} hours."
            )
            return

        # Create summary
        summary_text = (
            f"**📊 Summary of {target_channel.mention} - Last {hours} hours**\n\n"
        )
        summary_text += f"**Messages analyzed:** {len(messages)}\n"
        summary_text += f"**Time period:** {threshold.strftime('%Y-%m-%d %H:%M')} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n\n"

        # Group by author
        author_stats = {}
        for msg in messages:
            author = msg["author"]
            if author not in author_stats:
                author_stats[author] = {"count": 0, "reactions": 0}
            author_stats[author]["count"] += 1
            author_stats[author]["reactions"] += msg["reactions"]

        summary_text += "**👥 Participation:**\n"
        for author, stats in sorted(
            author_stats.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            summary_text += f"• {author}: {stats['count']} messages, {stats['reactions']} reactions\n"

        # Recent highlights (messages with reactions)
        highlights = [msg for msg in messages if msg["reactions"] > 0]
        if highlights:
            summary_text += "\n**⭐ Highlighted Messages:**\n"
            for msg in sorted(highlights, key=lambda x: x["reactions"], reverse=True)[
                :3
            ]:
                content = (
                    msg["content"][:100] + "..."
                    if len(msg["content"]) > 100
                    else msg["content"]
                )
                summary_text += (
                    f"• **{msg['author']}** ({msg['reactions']} 👍): {content}\n"
                )

        # Create embed
        embed = discord.Embed(
            title="📈 Channel Summary",
            description=summary_text,
            color=0x2ECC71,
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Error in summarize command: {e}")
        await interaction.followup.send(
            f"❌ Sorry, I encountered an error while generating the summary: {str(e)}"
        )


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    logger.error(f"Command error: {error}")


@bot.event
async def on_application_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    """Handle slash command errors."""
    logger.error(f"Slash command error: {error}")
    if not interaction.response.is_done():
        await interaction.response.send_message(
            f"❌ An error occurred: {str(error)}", ephemeral=True
        )


def main():
    """Main function to run the bot."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable not set!")
        return

    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid bot token!")
    except Exception as e:
        logger.error(f"Bot error: {e}")


if __name__ == "__main__":
    main()
