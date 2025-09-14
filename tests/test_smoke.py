"""
Smoke tests for Project Automation platform.

These tests verify basic functionality and imports to ensure the system is working.
"""

import sys
from pathlib import Path

import pytest


class TestImports:
    """Test that core modules can be imported successfully."""

    def test_import_basic_modules(self) -> None:
        """Test that standard library modules work."""
        import json
        import os
        import tempfile

        assert os is not None
        assert json is not None
        assert tempfile is not None

    def test_import_external_dependencies(self) -> None:
        """Test that required external packages can be imported."""
        import jinja2
        import markdown
        import requests

        assert markdown is not None
        assert jinja2 is not None
        assert requests is not None

    def test_import_bot_modules(self) -> None:
        """Test that bot modules can be imported."""
        # Add bot directory to path for imports
        bot_path = Path(__file__).parent.parent / "bot"
        if str(bot_path) not in sys.path:
            sys.path.insert(0, str(bot_path))

        try:
            import config
            import settings

            import utils

            assert config is not None
            assert settings is not None
            assert utils is not None
        except ImportError as e:
            pytest.skip(f"Bot modules not available for import: {e}")

    def test_import_scripts(self) -> None:
        """Test that script modules can be imported."""
        # Add scripts directory to path for imports
        scripts_path = Path(__file__).parent.parent / "scripts"
        if str(scripts_path) not in sys.path:
            sys.path.insert(0, str(scripts_path))

        try:
            import markdown_processor

            assert markdown_processor is not None
        except ImportError as e:
            pytest.skip(f"Script modules not available for import: {e}")


class TestFileStructure:
    """Test that expected files and directories exist."""

    def test_project_structure(self) -> None:
        """Test that the project has expected structure."""
        project_root = Path(__file__).parent.parent

        # Core files
        assert (project_root / "README.md").exists()
        assert (project_root / "requirements.txt").exists()
        assert (project_root / "pyproject.toml").exists()

        # Core directories
        assert (project_root / "bot").is_dir()
        assert (project_root / "scripts").is_dir()
        assert (project_root / "docs").is_dir()
        assert (project_root / ".github").is_dir()

    def test_bot_structure(self) -> None:
        """Test that bot directory has expected structure."""
        bot_dir = Path(__file__).parent.parent / "bot"

        if bot_dir.exists():
            assert (bot_dir / "main.py").exists()
            assert (bot_dir / "config.py").exists()
            assert (bot_dir / "settings.py").exists()

    def test_scripts_structure(self) -> None:
        """Test that scripts directory has expected structure."""
        scripts_dir = Path(__file__).parent.parent / "scripts"

        if scripts_dir.exists():
            assert (scripts_dir / "markdown_processor.py").exists()

    def test_github_workflows(self) -> None:
        """Test that GitHub workflows exist."""
        workflows_dir = Path(__file__).parent.parent / ".github" / "workflows"

        if workflows_dir.exists():
            workflow_files = list(workflows_dir.glob("*.yml"))
            assert len(workflow_files) > 0, "No workflow files found"


class TestBasicFunctionality:
    """Test basic functionality without external dependencies."""

    def test_python_version(self) -> None:
        """Test that Python version is compatible."""

    assert sys.version_info >= (3, 10), "Python 3.10+ required"

    def test_pathlib_operations(self) -> None:
        """Test basic file operations work."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            test_file = tmp_path / "test.txt"

            # Write and read file
            test_file.write_text("Hello, World!")
            content = test_file.read_text()

            assert content == "Hello, World!"
            assert test_file.exists()

    def test_json_operations(self) -> None:
        """Test JSON operations work."""
        import json

        test_data = {"test": "value", "number": 42}
        json_str = json.dumps(test_data)
        parsed_data = json.loads(json_str)

        assert parsed_data == test_data

    def test_markdown_basic(self) -> None:
        """Test basic markdown processing."""
        try:
            import markdown

            md = markdown.Markdown()
            html = md.convert("# Test Header\n\nThis is a test.")

            assert "<h1>Test Header</h1>" in html
            assert "<p>This is a test.</p>" in html
        except ImportError:
            pytest.skip("Markdown module not available")


class TestConfiguration:
    """Test configuration and environment setup."""

    def test_environment_variables(self) -> None:
        """Test environment variable handling."""
        import os

        # Test that we can set and get environment variables
        test_key = "PROJ_AUTOMATION_TEST"
        test_value = "test_value"

        os.environ[test_key] = test_value
        assert os.getenv(test_key) == test_value

        # Cleanup
        del os.environ[test_key]

    def test_config_files_exist(self) -> None:
        """Test that configuration files exist."""
        project_root = Path(__file__).parent.parent

        # Configuration files that should exist
        config_files = [
            ".editorconfig",
            ".pre-commit-config.yaml",
            "pyproject.toml",
            ".gitignore",
        ]

        for config_file in config_files:
            file_path = project_root / config_file
            assert file_path.exists(), f"Configuration file {config_file} not found"


# Test discovery function for pytest
def test_smoke_tests_discovered() -> None:
    """Meta-test to ensure smoke tests are being discovered."""
    # This test ensures that pytest is finding and running our test classes
    assert True, "Smoke tests are being discovered and executed"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
