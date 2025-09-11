from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Show help and common commands")
    async def help_cmd(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title="🤖 Bot Help & Commands", color=0x2B6CB0)

        embed.add_field(
            name="💬 AI Commands",
            value="\n".join(
                [
                    "/ask <question> – Get AI-powered answers",
                    "/summarize <content> – Summarize text or files",
                    "/capabilities – See all bot features",
                ]
            ),
            inline=False,
        )

        embed.add_field(
            name="💼 Business Tools",
            value="\n".join(
                [
                    "/budget <data> – Analyze budget/spending data",
                    "/campaign <product> – Generate marketing briefs",
                    "/health – Check system status",
                ]
            ),
            inline=False,
        )

        embed.add_field(
            name="📄 File & Document",
            value="\n".join(
                [
                    "DM files to bot – Process and store documents",
                    "!getdoc <filename> – Retrieve stored documents",
                    "Upload files – Admin users can upload help docs",
                ]
            ),
            inline=False,
        )

        embed.add_field(
            name="🛠️ Utility",
            value="\n".join(
                [
                    "!lint <file> – Run code linting",
                    "!ocr <image> – Extract text from images",
                    "!createpr <repo> <title> – Create GitHub PR",
                ]
            ),
            inline=False,
        )

        embed.set_footer(
            text="💡 Tip: Attach files with your commands when relevant | Use /capabilities for detailed feature list"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
