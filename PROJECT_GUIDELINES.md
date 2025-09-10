# Project Guidelines

This document establishes shared development standards for the Project Automation platform, aligned with our security configurations and recent bot enhancements.

## Table of Contents

- [Branching Workflow & Pull Request Process](#branching-workflow--pull-request-process)
- [Commit Conventions](#commit-conventions)
- [Lint, Format & Test Expectations](#lint-format--test-expectations)
- [Security & Secrets Handling](#security--secrets-handling)
- [Configuration & Environment Variables](#configuration--environment-variables)
- [Bot Commands & UX Guidelines](#bot-commands--ux-guidelines)
- [Local Development Setup](#local-development-setup)

---

## Branching Workflow & Pull Request Process

### Branch Naming Convention

Follow these patterns for branch names:

- **Feature branches**: `feature/description-of-feature`
- **Bug fixes**: `fix/description-of-fix`
- **Chores/maintenance**: `chore/description-of-task`
- **Documentation**: `docs/description-of-update`
- **AI-assisted changes**: `copilot/fix-*` (automatically generated)

**Examples:**
```
feature/add-voice-transcription
fix/webhook-error-handling
chore/update-dependencies
docs/bot-integration-guide
```

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make Changes and Test**
   - Follow the coding standards outlined below
   - Test your changes locally
   - Run linting and any existing tests

3. **Commit with Conventional Format**
   ```bash
   git commit -m "feat: add voice transcription support"
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/amazing-feature
   ```

5. **PR Requirements**
   - Descriptive title and clear description
   - Link related issues with `Fixes #123` or `Closes #123`
   - Ensure CI/CD workflows pass
   - Request review from maintainers

### Branch Protection

- **Main branch** is protected - all changes must go through PRs
- **Squash and merge** is preferred for clean history
- **Delete feature branches** after successful merge

---

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/) for clear, searchable history.

### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- **feat**: New feature for users
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring (no new features or bug fixes)
- **test**: Adding or updating tests
- **chore**: Maintenance tasks, dependency updates
- **ci**: Changes to CI/CD workflows
- **perf**: Performance improvements
- **security**: Security-related changes

### Examples

```bash
feat: add OCR support for image processing
fix: resolve webhook timeout issues
docs: update bot command reference
chore: bump discord.py to v2.3.2
security: implement rate limiting for API calls
ci: add automated PDF generation workflow
```

### Scope Examples

```bash
feat(bot): add /summarize command with AI integration
fix(webhook): handle Discord 25MB file limit properly
docs(api): update GitHub integration documentation
```

---

## Lint, Format & Test Expectations

### Python Code Standards

**Linting with flake8:**
```bash
# Run linting (already in requirements.txt)
flake8 bot/ scripts/ --max-line-length=88 --ignore=E203,W503
```

**Code Style:**
- **Line length**: 88 characters (Black compatible)
- **Imports**: Use absolute imports, sort with isort if available
- **Type hints**: Use for function signatures and complex variables
- **Docstrings**: Use for classes and public functions

**Example:**
```python
#!/usr/bin/env python3
"""
Module description here.
"""

from typing import Optional
import discord
from bot.config import BotConfig


class ExampleClass:
    """Example class with proper documentation."""
    
    def __init__(self, config: BotConfig) -> None:
        """Initialize with configuration."""
        self.config = config
    
    async def process_message(self, message: str) -> Optional[str]:
        """Process message and return response."""
        if not message.strip():
            return None
        return f"Processed: {message}"
```

### Testing

**Test Structure:**
```bash
# Run tests (when they exist)
python -m pytest tests/ -v

# Test your changes manually
python scripts/md_to_pdf.py docs/ideasheets/sample_idea.md -o test_output/
```

**Testing Guidelines:**
- Test new bot commands in a development Discord server
- Validate file processing with sample documents
- Check workflow changes don't break existing automation
- Use the reliability test script: `python test_reliability.py`

### Pre-commit Checklist

Before creating a PR:
- [ ] Code passes flake8 linting
- [ ] Manual testing completed
- [ ] Documentation updated if needed
- [ ] Environment variables documented
- [ ] No secrets committed to repository

---

## Security & Secrets Handling

### Environment Variables

**Never commit secrets to the repository.** Use environment variables and the `.env` file pattern.

**Required Setup:**
```bash
# Copy template and fill in values
cp .env.example .env
# Edit .env with your actual tokens (DO NOT COMMIT THIS FILE)
```

### Secret Types

| Secret Type | Environment Variable | Purpose |
|-------------|---------------------|---------|
| Discord Bot | `DISCORD_BOT_TOKEN` | Bot authentication |
| Discord Webhook | `DISCORD_WEBHOOK_URL` | PDF publishing |
| OpenAI API | `OPENAI_API_KEY` | AI-powered features |
| GitHub | `GITHUB_TOKEN` | Repository integration |
| Admin Users | `DISCORD_ADMIN_IDS` | Admin command access |

### Security Best Practices

1. **API Key Rotation**
   - Rotate tokens regularly
   - Use least-privilege tokens (read-only when possible)
   - Monitor usage in respective platforms

2. **File Upload Security**
   - 25MB Discord file size limit enforced
   - Admin-only access for helpdocs uploads
   - Temporary file cleanup after processing
   - File type validation for OCR/transcription

3. **Rate Limiting**
   - Per-user cooldowns on bot commands
   - API request throttling to prevent abuse
   - Error handling prevents token exposure

4. **Data Privacy**
   - Conversation memory stored locally only
   - No persistent storage of file contents
   - Audit logging for admin actions

### GitHub Secrets Configuration

For CI/CD workflows, configure these secrets in repository settings:

```
DISCORD_WEBHOOK_URL  # For PDF publishing
GITHUB_TOKEN         # For automated PR comments
```

---

## Configuration & Environment Variables

### Required Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Core Bot Configuration
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_WEBHOOK_URL=your_webhook_url_here
DISCORD_ADMIN_IDS=123456789012345678,987654321098765432

# AI Features (optional)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
WHISPER_MODEL=whisper-1

# GitHub Integration (optional)
GITHUB_TOKEN=your_github_token_here

# Team Customization
TEAM_NAME=Your Team Name
TEAM_BOT_NAME=YourBotName
DEFAULT_REPO=your-org/your-repo
```

### Optional Configuration

```bash
# Google Search (optional)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CX=your_custom_search_engine_id_here

# Logging
LOG_LEVEL=INFO
STRUCTURED_LOGS=false

# Currency (for financial processing)
CURRENCY_CODE=USD
CURRENCY_LOCALE=en_US
CURRENCY_SYMBOL=$
```

### Configuration Validation

The bot validates configuration on startup:
- Shows available features based on configured tokens
- Gracefully disables features when tokens are missing
- Provides clear error messages for misconfiguration

---

## Bot Commands & UX Guidelines

### Current Command Set

#### Slash Commands (Preferred)
- `/help` - Show help and common commands
- `/capabilities` - Display available bot features
- `/ask <question>` - Create threaded discussions with AI suggestions
- `/summarize [channel] [hours]` - Generate summaries with participation metrics
- `/submit-idea <title> <description> [tags]` - Submit ideas to ideasheets
- `/get-doc <filename> [format]` - Retrieve documents (markdown/html/pdf)

#### Traditional Commands (Legacy)
- `!createpr <repo> <title> <body>` - Create GitHub pull requests
- `!google <query>` - Web search using DuckDuckGo
- `!github_issues <repo> [state] [limit]` - Fetch repository issues
- `!lint <file>` - Run flake8 linting on attached Python files
- `!ocr <image>` - Extract text from attached images

### UX Guidelines

#### Rate Limiting
- **30-second cooldown** for `/ask` command
- **60-second cooldown** for `/summarize` command
- Per-user rate limiting to prevent spam

#### Message Behavior
- **Thread creation**: Automatic for discussions
- **Rich embeds**: Professional formatting with metadata
- **Message chunking**: Automatically splits long responses
- **Ephemeral responses**: Use for help and error messages

#### File Handling
- **25MB limit**: Discord's maximum file size
- **Type validation**: Check file types before processing
- **Temporary cleanup**: Remove processed files after use

#### Error Handling
- **Graceful degradation**: Features disable when services unavailable
- **Clear error messages**: User-friendly explanations
- **Fallback options**: Alternative methods when primary fails

### Adding New Commands

1. **Choose Command Type**
   - Prefer slash commands for new features
   - Use traditional commands only for legacy compatibility

2. **Implementation Pattern**
   ```python
   @bot.tree.command(name='newcommand', description='Description here')
   async def new_command(interaction: discord.Interaction, param: str):
       # Add cooldown if needed
       # Validate inputs
       # Process request
       # Respond appropriately
       await interaction.response.send_message("Response")
   ```

3. **Update Help System**
   - Add to `bot/commands/help.py`
   - Update documentation in `docs/bot-integration.md`

---

## Local Development Setup

### System Requirements

- **Python 3.8+** (recommended: 3.11)
- **Git** for version control
- **Text editor** with Python support

### External Dependencies

```bash
# Ubuntu/Debian
sudo apt-get install wkhtmltopdf tesseract-ocr

# macOS
brew install wkhtmltopdf tesseract

# Windows
# Download from: https://wkhtmltopdf.org/downloads.html
# Download tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Development Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/dktn7/proj-automation.git
   cd proj-automation
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your tokens and configuration
   ```

5. **Test Installation**
   ```bash
   # Test PDF generation
   python scripts/md_to_pdf.py docs/ideasheets/sample_idea.md -o test_output/
   
   # Test bot configuration (dry run)
   cd bot
   python -c "from config import BotConfig; print('Config loaded successfully')"
   ```

### Development Workflow

1. **Start Development**
   ```bash
   # Activate virtual environment
   source venv/bin/activate
   
   # Create feature branch
   git checkout -b feature/your-feature
   ```

2. **Run Bot Locally**
   ```bash
   cd bot
   python main.py
   ```

3. **Test Changes**
   ```bash
   # Run linting
   flake8 bot/ scripts/ --max-line-length=88
   
   # Test reliability
   python test_reliability.py
   
   # Test specific features
   python demo_bot_features.py
   ```

4. **Validate Workflows**
   ```bash
   # Test workflow scripts locally
   bash scripts/process_ideasheets.sh
   ```

### Development Tips

- **Use development Discord server** for testing bot commands
- **Check logs** in console for debugging information
- **Test with sample files** in `docs/ideasheets/` directory
- **Validate environment** with `setup_bot.py` before development
- **Run reliability tests** after significant changes

### IDE Configuration

**VS Code Recommended Extensions:**
- Python
- GitLens
- Markdown All in One
- YAML

**PyCharm Configuration:**
- Enable flake8 linting
- Set line length to 88 characters
- Configure Python interpreter to virtual environment

---

## Conclusion

These guidelines ensure consistent, secure, and maintainable development practices for the Project Automation platform. When in doubt, refer to existing patterns in the codebase and prioritize security and user experience.

For questions or suggestions about these guidelines, please open an issue or start a discussion in the repository.
=======
These guidelines describe how we collaborate, branch, commit, review, and ship changes in this repository.

## Contents
- Branching and workflow
- Commit messages
- Pull requests and reviews
- Code quality and style
- Security and secrets
- Configuration and environment
- Bot commands and UX
- Local development

---

## Branching and workflow

- Main branch: `main` is protected and must remain releasable.
- Feature branches: Use short, descriptive names, e.g.:
  - `feature/security-config`
  - `feature/ux-help-capabilities`
  - `feature/runtime-reliability`
  - `feature/ci-and-tests`
- One topic per branch. Keep diffs focused and small where possible.

Recommended flow:
1. Create a feature branch from `main`.
2. Commit and push changes early and often.
3. Open a Pull Request (PR) targeting `main`.
4. Request review and address feedback.
5. Squash-merge after approval and passing checks.

## Commit messages

- Use imperative mood and concise scope:
  - “Add Pydantic settings for security and configuration”
  - “Add help command UI”
- First line ≤ 72 chars; add context in the body if needed.
- Reference issues (e.g., “Fixes #123”) when applicable.

## Pull requests and reviews

- Include:
  - What changed and why (user impact, motivation).
  - Testing done (steps, screenshots/logs as appropriate).
  - Any follow-ups or known gaps.
- Keep PRs small and self-contained.
- Require at least one reviewer; prefer domain owners for sensitive areas (security, configuration).
- Resolve conversations or track them in follow-up tickets before merging.

## Code quality and style

- Python style:
  - Prefer type hints throughout.
  - Keep functions small; favor readability over cleverness.
- Linting/formatting:
  - Ruff + Black are recommended for lint/format.
  - Mypy for static typing.
  - Pre-commit hooks are encouraged for local consistency.
- Tests:
  - Add unit tests for new logic where feasible.
  - Keep tests fast and deterministic.

Note: If/when `.pre-commit-config.yaml` is introduced, run:
```
pre-commit install
pre-commit run --all-files
```

## Security and secrets

- Never commit secrets or tokens.
- Use environment variables for credentials.
- The settings module enforces basic validation and supports redaction in logs.

Limits and safeguards:
- Max attachment size defaults to 5 MB (configurable).
- Allowed MIME types (default): text/plain, text/markdown, application/json, image/png, image/jpeg, application/pdf.
- Use ephemeral temp directories; avoid writing outside sandbox paths.

## Configuration and environment

Environment variables recognized by the bot (from current settings):

- `DISCORD_TOKEN` (required): Discord bot token.
- `OPENAI_API_KEY` (required): OpenAI API key.
- `MAX_ATTACHMENT_BYTES` (optional, int; default 5000000): Max upload size.
- `ALLOWED_MIME_TYPES` (optional, comma-separated): Override allowed types.
- `TEMPDIR_BASE` (optional): Base path for temp sandboxes.
- `REDACT_SECRETS` (optional, “true”/“false”; default “true”): Redact secrets in logs.

Example `.env` (do not commit):
```
DISCORD_TOKEN=***
OPENAI_API_KEY=***
MAX_ATTACHMENT_BYTES=5000000
ALLOWED_MIME_TYPES=text/plain,text/markdown,application/json,image/png,image/jpeg,application/pdf
REDACT_SECRETS=true
```

## Bot commands and UX

Current application commands include:
- `/help` — Show help and common commands.
- `/capabilities` — Summarize bot capabilities.

Conventional message commands (examples that may be present or planned):
- `!lint <file>` — Run linting on a file.
- `!ocr <image>` — OCR an attached image.

Tips:
- Prefer ephemeral responses for help/diagnostics where appropriate.
- Encourage attaching relevant files with commands to reduce back-and-forth.

## Local development

- Python version: align with the project’s runtime (pin in `pyproject.toml`/`requirements.txt` when available).
- Recommended steps:
  1. Create and activate a virtualenv.
  2. Install dependencies.
  3. Set required environment variables.
  4. Run linters/tests locally before pushing.

Example:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# set env vars
# run your local checks
```

---

## Ownership and contact

- Security/Configuration: changes to token handling, limits, or settings.
- UX/Commands: changes to slash commands and user-facing responses.

Document ownership is shared. Propose edits via PR to keep this up to date.

