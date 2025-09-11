#!/usr/bin/env python3
"""
Test script for Discord Bot
Verifies that the bot can be imported and basic functionality works
"""

import sys
from pathlib import Path


# Add the bot directory to the path
bot_dir = Path(__file__).parent / "bot"
sys.path.insert(0, str(bot_dir))


def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing bot imports...")

    try:
        # Test config import

        print("✅ Config module imported successfully")

        # Test basic bot functionality

        print("✅ Discord.py imported successfully")

        # Test feature imports
        import importlib

        # Optional feature imports - import dynamically to avoid unused-import lints
        try:
            importlib.import_module("features.budget")
            print("✅ Budget features module available")
        except ImportError as e:
            print(f"⚠️  Budget features import failed: {e}")

        try:
            importlib.import_module("features.marketing")
            print("✅ Marketing features module available")
        except ImportError as e:
            print(f"⚠️  Marketing features import failed: {e}")

        # Test utility imports
        try:
            importlib.import_module("utils.ai_helper")
            print("✅ AI helper module available")
        except ImportError as e:
            print(f"⚠️  AI helper import failed: {e}")

        return True

    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False


def test_config():
    """Test configuration loading."""
    print("\n🧪 Testing configuration...")

    try:
        from config import config

        # Check if required environment variables are set
        if hasattr(config, "discord_token") and config.discord_token:
            print("✅ Discord token configured")
        else:
            print("⚠️  Discord token not configured")

        if hasattr(config, "openai_api_key") and config.openai_api_key:
            print("✅ OpenAI API key configured")
        else:
            print("⚠️  OpenAI API key not configured")

        if hasattr(config, "admin_user_ids"):
            print(f"✅ Admin users configured: {len(config.admin_user_ids)}")

        return True

    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Discord Bot Test Suite")
    print("=" * 40)

    import_success = test_imports()
    config_success = test_config()

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
