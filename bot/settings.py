from __future__ import annotations

import os
from typing import Optional, Set

from pydantic import BaseModel, Field, ValidationError, field_validator


class Settings(BaseModel):
    # Tokens/keys
    discord_token: str = Field(..., description="Discord bot token")
    openai_api_key: str = Field(..., description="OpenAI API key")

    # Security limits
    max_attachment_bytes: int = Field(5_000_000, ge=1, le=50_000_000)
    allowed_mime_types: Set[str] = Field(
        default_factory=lambda: {
            "text/plain",
            "text/markdown",
            "application/json",
            "image/png",
            "image/jpeg",
            "application/pdf",
        }
    )

    # File system sandbox
    tempdir_base: Optional[str] = Field(
        default=None, description="Optional base directory for temp sandboxes"
    )

    # Logging
    redact_secrets: bool = True

    @field_validator("discord_token", "openai_api_key")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()

    def redacted_dict(self) -> dict:
        def redact(value: str) -> str:
            if not value:
                return value
            return value[:4] + "…" if len(value) > 8 else "****"

        data = self.model_dump()
        if self.redact_secrets:
            data["discord_token"] = redact(self.discord_token)
            data["openai_api_key"] = redact(self.openai_api_key)
        return data


def load_settings() -> Settings:
    env = os.environ
    try:
        return Settings(
            discord_token=env.get("DISCORD_TOKEN", ""),
            openai_api_key=env.get("OPENAI_API_KEY", ""),
            max_attachment_bytes=int(env.get("MAX_ATTACHMENT_BYTES", "5000000")),
            allowed_mime_types=(
                set(env.get("ALLOWED_MIME_TYPES").split(","))
                if env.get("ALLOWED_MIME_TYPES")
                and env.get("ALLOWED_MIME_TYPES").strip()
                else None
            ),
            tempdir_base=env.get("TEMPDIR_BASE") or None,
            redact_secrets=(env.get("REDACT_SECRETS", "true").lower() == "true"),
        )
    except (ValidationError, ValueError) as e:
        raise SystemExit(f"[settings] Invalid configuration: {e}") from e
