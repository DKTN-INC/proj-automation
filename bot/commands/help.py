from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Show help and common commands")
    async def help_cmd(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title="Help", color=0x2b6cb0)
        embed.add_field(
            name="Common",
            value="\n".join(
                [
                    "/help – Show this help",
                    "/capabilities – What I can do",
                    "!lint <file> – Run lint",
                    "!ocr <image> – OCR image",
                ]
            ),
            inline=False,
        )
        embed.set_footer(text="Tip: Attach files with your command when relevant.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))