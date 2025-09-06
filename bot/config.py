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
        self.discord_token = os.getenv("DISCORD_BOT_TOKEN")
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
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

        # Database path
        self.db_path = self.repo_root / "bot" / "conversation_memory.db"
        self.alt_db_path = self.repo_root / "bot_memory.db"  # For compatibility

        # File size limits (Discord limits)
        self.max_file_size = 25 * 1024 * 1024  # 25MB

        # AI settings
        self.ai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
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
