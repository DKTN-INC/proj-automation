#!/usr/bin/env python3
"""
Configuration module for Discord Bot
Handles environment variables and bot settings
"""

import os
from pathlib import Path


class BotConfig:
    """Bot configuration class for managing environment variables and settings."""

    def __init__(self):
        # Load environment variables
        # Prefer BOT_TOKEN (Railway) but keep DISCORD_BOT_TOKEN for backward compatibility
        self.discord_token = os.getenv("BOT_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cx = os.getenv("GOOGLE_CX")
        self.guild_id = os.getenv("DISCORD_GUILD_ID")

        # Admin user IDs (can be comma-separated)
        admin_ids = os.getenv("DISCORD_ADMIN_IDS", os.getenv("DISCORD_ADMIN_ID", ""))
        self.admin_user_ids = [
            int(uid.strip()) for uid in admin_ids.split(",") if uid.strip().isdigit()
        ]

        # Repository paths
        self.repo_root = Path(__file__).parent.parent
        self.ideasheets_dir = self.repo_root / "docs" / "ideasheets"
        self.helpdocs_dir = self.repo_root / "docs" / "helpdocs"
        self.output_dir = self.repo_root / "output"
        self.temp_dir = self.repo_root / "temp"

        # Database path
        self.db_path = self.repo_root / "bot" / "conversation_memory.db"
        self.alt_db_path = self.repo_root / "bot_memory.db"  # For compatibility

        # File size limits (Discord limits)
        self.max_file_size = 25 * 1024 * 1024  # 25MB

        # AI settings
        self.ai_model = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
        self.whisper_model = os.getenv("WHISPER_MODEL", "whisper-1")

        # Team/Persona configuration
        self.team_name = os.getenv("TEAM_NAME", "Project Automation Team")
        self.team_purpose = os.getenv(
            "TEAM_PURPOSE",
            "Design, build, and deliver high-quality software efficiently and safely.",
        )
        self.team_bot_name = os.getenv("TEAM_BOT_NAME", "Probo")
        self.default_repo = os.getenv("DEFAULT_REPO", "dktn7/proj-automation")

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_config(self):
        """Validate configuration and return status."""
        messages = []
        is_valid = True

        if not self.discord_token:
            messages.append(
                "ERROR: BOT_TOKEN (or legacy DISCORD_BOT_TOKEN) is required"
            )
            is_valid = False
        else:
            messages.append("INFO: Discord token configured")

        if not self.google_api_key:
            messages.append("WARNING: GOOGLE_API_KEY not set - AI features disabled")
        else:
            messages.append("INFO: Google API key configured")

        if not self.github_token:
            messages.append("WARNING: GITHUB_TOKEN not set - GitHub features disabled")
        else:
            messages.append("INFO: GitHub token configured")

        if self.admin_user_ids:
            messages.append(
                f"INFO: {len(self.admin_user_ids)} admin user(s) configured"
            )
        else:
            messages.append("WARNING: No admin users configured")

        return is_valid, messages


# Create global config instance
config = BotConfig()
