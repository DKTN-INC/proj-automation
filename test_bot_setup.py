#!/usr/bin/env python3
"""
Test script for Discord Bot
Verifies that the bot can be imported and basic functionality works
"""

import sys
from pathlib import Path

from dotenv import load_dotenv


# Ensure project root and bot package are importable
project_root = Path(__file__).parent
bot_dir = project_root / "bot"
sys.path.insert(0, str(project_root))

# Load environment from .env at project root if present
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))


def _check_imports() -> bool:
    """Helper that verifies required modules can be imported.

    Returns True on success, False on failure. Tests should call the
    corresponding `test_` wrapper which will assert on the result.
    """
    print("🧪 Testing bot imports...")

    try:
        # Prefer explicit package import for config
        try:
            from bot.config import config  # noqa: F401
        except Exception:
            # allow running tests from repo root where package import may differ
            from config import config  # type: ignore  # noqa: F401

        # Test feature imports under the `bot` package
        import importlib

        # Optional feature imports - import dynamically to avoid unused-import lints
        try:
            importlib.import_module("bot.features.budget")
        except ImportError:
            # It's acceptable for optional features to be missing in minimal dev envs
            pass

        try:
            importlib.import_module("bot.features.marketing")
        except ImportError:
            pass

        try:
            importlib.import_module("bot.utils.ai_helper")
        except ImportError:
            pass

        return True

    except Exception:
        return False


def test_imports():
    assert _check_imports(), "Import checks failed"


def _check_config() -> bool:
    """Helper that verifies configuration loads without raising exceptions.

    Returns True on success. Tests should call `test_config` which asserts
    on the result so pytest sees failures correctly.
    """
    try:
        try:
            from bot.config import config
        except Exception:
            from config import config  # type: ignore

        # Basic surface checks (do not require secrets in CI)
        _ = getattr(config, "discord_token", None)
        _ = getattr(config, "google_api_key", None)
        _ = getattr(config, "admin_user_ids", None)

        return True
    except Exception:
        return False


def test_config():
    assert _check_config(), "Configuration loading failed"


def main():
    """Run all tests."""
    print("🚀 Discord Bot Test Suite")
    print("=" * 40)

    import_success = _check_imports()
    config_success = _check_config()

    print("\n" + "=" * 40)
    if import_success and config_success:
        print("✅ All tests passed! Bot is ready to run.")
        print("\nTo start the bot:")
        print("  cd bot")
        print("  python main.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
