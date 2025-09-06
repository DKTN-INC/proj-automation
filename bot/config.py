#!/usr/bin/env python3
"""
Configuration module for Discord Bot
Handles environment variables and bot settings
"""

import os
from pathlib import Path
from typing import Optional

class BotConfig:
    """Bot configuration class for managing environment variables and settings."""
    
    def __init__(self):
        # Load environment variables
        self.discord_token = os.getenv('DISCORD_BOT_TOKEN')
        self.discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.guild_id = os.getenv('DISCORD_GUILD_ID')
        
        # Repository paths
        self.repo_root = Path(__file__).parent.parent
        self.ideasheets_dir = self.repo_root / "docs" / "ideasheets"
        self.helpdocs_dir = self.repo_root / "docs" / "helpdocs"
        self.output_dir = self.repo_root / "output"
        
        # Database path
        self.db_path = self.repo_root / "bot" / "conversation_memory.db"
        
        # File size limits (Discord limits)
        self.max_file_size = 25 * 1024 * 1024  # 25MB
        
        # Admin user IDs (can be set via environment variable)
        admin_ids = os.getenv('DISCORD_ADMIN_IDS', '')
        self.admin_user_ids = [int(uid.strip()) for uid in admin_ids.split(',') if uid.strip().isdigit()]
        
        # AI settings
        self.ai_model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        self.whisper_model = os.getenv('WHISPER_MODEL', 'whisper-1')
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.ideasheets_dir.mkdir(parents=True, exist_ok=True)
        self.helpdocs_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def is_admin(self, user_id: int) -> bool:
        """Check if a user is an admin."""
        return user_id in self.admin_user_ids
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """Validate required configuration values."""
        errors = []
        
        if not self.discord_token:
            errors.append("DISCORD_BOT_TOKEN is required")
        
        # Optional but recommended
        warnings = []
        if not self.openai_api_key:
            warnings.append("OPENAI_API_KEY not set - AI features will be disabled")
        if not self.github_token:
            warnings.append("GITHUB_TOKEN not set - GitHub integration will be disabled")
        if not self.discord_webhook_url:
            warnings.append("DISCORD_WEBHOOK_URL not set - webhook features will be disabled")
        
        is_valid = len(errors) == 0
        return is_valid, errors + warnings

# Global config instance
config = BotConfig()