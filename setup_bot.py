#!/usr/bin/env python3
"""
Bot setup helper script.
Helps configure environment variables and validate the setup.
"""

import os
import sys
from pathlib import Path


def main():
    """Main setup function."""
    print("🤖 Project Automation Bot Setup")
    print("=" * 40)

    # Check if we're in the right directory
    if not Path("bot/main.py").exists():
        print("❌ Please run this script from the repository root directory")
        sys.exit(1)

    print("✅ Found bot directory")

    # Check environment variables
    print("\n📋 Environment Configuration:")

    required_vars = {
        "DISCORD_BOT_TOKEN": "Discord bot token (required to run bot)",
    }

    optional_vars = {
        "OPENAI_API_KEY": "OpenAI API key (for AI features)",
        "LOG_LEVEL": "Logging level (DEBUG, INFO, WARNING, ERROR)",
        "STRUCTURED_LOGS": "Use structured JSON logging (true/false)",
        "LOG_FILE": "Path to log file (optional)",
    }

    print("\nRequired Environment Variables:")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {'*' * min(10, len(value))}...")
        else:
            print(f"  ❌ {var}: Not set - {description}")

    print("\nOptional Environment Variables:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚪ {var}: Not set - {description}")

    # Check dependencies
    print("\n📦 Checking Dependencies:")

    try:
        import discord

        print(f"  ✅ discord.py: {discord.__version__}")
    except ImportError:
        print("  ❌ discord.py not installed")

    try:
        import openai

        print(f"  ✅ openai: {openai.__version__}")
    except ImportError:
        print("  ❌ openai not installed")

    try:
        import aiohttp

        print(f"  ✅ aiohttp: {aiohttp.__version__}")
    except ImportError:
        print("  ❌ aiohttp not installed")

    # Test bot imports
    print("\n🔧 Testing Bot Modules:")

    sys.path.insert(0, "bot")

    try:
        print("  ✅ OpenAI wrapper")
    except Exception as e:
        print(f"  ❌ OpenAI wrapper: {e}")

    try:
        print("  ✅ Message chunker")
    except Exception as e:
        print(f"  ❌ Message chunker: {e}")

    try:
        print("  ✅ Cooldown manager")
    except Exception as e:
        print(f"  ❌ Cooldown manager: {e}")

    try:
        print("  ✅ Structured logging")
    except Exception as e:
        print(f"  ❌ Structured logging: {e}")

    try:
        print("  ✅ Thread pool manager")
    except Exception as e:
        print(f"  ❌ Thread pool manager: {e}")

    # Generate .env template
    print("\n📝 Environment Template:")
    print("Create a .env file with these variables:")
    print()
    print("# Required")
    print("DISCORD_BOT_TOKEN=your_discord_bot_token_here")
    print()
    print("# Optional - AI Features")
    print("OPENAI_API_KEY=your_openai_api_key_here")
    print()
    print("# Optional - Logging")
    print("LOG_LEVEL=INFO")
    print("STRUCTURED_LOGS=false")
    print("LOG_FILE=bot.log")
    print()

    # Show usage
    print("\n🚀 Usage:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Set environment variables (create .env file)")
    print("3. Run the bot: python bot/main.py")
    print()
    print("For development:")
    print("  export LOG_LEVEL=DEBUG")
    print("  export STRUCTURED_LOGS=false")
    print()
    print("For production:")
    print("  export LOG_LEVEL=INFO")
    print("  export STRUCTURED_LOGS=true")
    print("  export LOG_FILE=/var/log/discord-bot.log")

    # Final status
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")

    print("\n" + "=" * 40)
    if discord_token:
        print("🎉 Bot is ready to run!")
        if openai_key:
            print("✨ AI features enabled")
        else:
            print("⚪ AI features disabled (no OpenAI key)")
    else:
        print("⚠️  Set DISCORD_BOT_TOKEN to run the bot")


if __name__ == "__main__":
    main()
