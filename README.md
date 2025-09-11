# Project Automation (Discord Bot + CI/CD)

A professional automation platform integrating Discord and GitHub for modern teams. Streamline collaboration, documentation, and publishing workflows with powerful bots and CI tools.

---

## Overview

Project Automation provides:
- **Advanced Discord bot** with AI-powered features for team collaboration
- **DM markdown intake** with automatic saving to docs/ideasheets/ and AI tagging
- **OCR and voice transcription** for image and audio processing
- **Code review automation** with flake8 integration and AI-generated test stubs
- **Automated PDF generation** from Markdown files with professional styling
- **GitHub integration** for PR creation and issue tracking
- **CI/CD pipeline** for converting docs to PDFs and publishing them to Discord

Perfect for technical teams, open source communities, and anyone looking to automate knowledge sharing between chat and code.

---

## Features

### 🤖 Discord Bot Commands

#### Slash Commands
- `/ask <question>`: Create threaded discussions for team questions with AI-powered response suggestions
- `/summarize [channel] [hours]`: Generate advanced summaries with participation metrics and insights
- `/submit-idea <title> <description> [tags]`: Submit ideas to the ideasheets collection
- `/get-doc <filename> [format]`: Retrieve documents in markdown/html/pdf format

#### Traditional Commands
- `!createpr <repo> <title> <body>`: Create GitHub pull requests
- `!google <query>`: Web search using DuckDuckGo
- `!github_issues <repo> [state] [limit]`: Fetch repository issues

#### Message Behavior & UX
- Per-user cooldowns: Rate limiting to prevent spam (e.g., 30s for /ask, 60s for /summarize)
- Thread management: Automatic thread creation for organized discussions
- Rich embeds: Professional message formatting with timestamps and metadata
- Smart message chunking: Safely splits long responses across multiple messages

### 🧠 AI & Advanced Features
- OpenAI integration for question answering, text summarization, and content generation
- DM Markdown intake: Send markdown via DM, automatically saved to `docs/ideasheets/` with AI tags
- Voice transcription: Convert voice messages to text (OpenAI Whisper)
- Image OCR: Extract text from images (pytesseract + preprocessing)
- Code review: Python linting with flake8 and AI-generated unit test stubs
- Conversation memory: Persistent per-user history (SQLite)
- Language detection for code snippets
- Thread pool processing for CPU-intensive tasks
- Structured JSON logging with contextual metadata
- Async architecture and robust error recovery

### 📁 File Processing & Management
- Admin file uploads to `docs/helpdocs/`
- Multi-format output: Automatic HTML and PDF generation from Markdown
- Smart handling for images, audio, and documents
- Syntax highlighting for enhanced code presentation

### 🔗 External Integrations
- GitHub API: Create PRs, fetch issues, and manage repositories
- OpenAI: GPT models for analysis and generation
- Web search: Built-in search utilities
- Discord webhooks: Professional notifications with rich embeds

### Automated PDF Generation
- Markdown processing to professionally styled PDFs
- Template system for consistent branding, metadata, and timestamps
- Syntax highlighting for code blocks
- Full table rendering support

### CI/CD Integration
- GitHub Actions workflow automatically triggered on Markdown changes
- Smart detection to process only changed files
- Discord publishing via webhooks
- Artifact storage with 30-day retention
- Automatic PR comments for status updates

### Discord Webhook Integration
- Professional notifications with file information and metadata
- Batch processing for multiple PDFs
- Robust error handling and detailed logging
- File size validation against Discord’s 25MB limit

---

## Setup

### 1. Clone and Install Dependencies

```sh
git clone https://github.com/dktn7/proj-automation.git
cd proj-automation
pip install -r requirements.txt
```

**System Requirements:**
- Python 3.8+
- wkhtmltopdf (for PDF generation)
- tesseract-ocr (for OCR functionality)

```sh
# Ubuntu/Debian
sudo apt-get install wkhtmltopdf tesseract-ocr

# macOS
brew install wkhtmltopdf tesseract

# Windows
# Download from: https://wkhtmltopdf.org/downloads.html
# Download tesseract from: https://github.com/UB-Mannheim/tesseract/wiki

### Optional: FFmpeg for audio processing (Windows)

If you use audio features locally or on Windows CI, ffmpeg must be available on PATH. A helper script is provided to install ffmpeg for developers or CI runners on Windows.

From the repository root run:

```powershell
./scripts/install_ffmpeg.ps1
```

This script will attempt a user-level install via Scoop, fall back to Chocolatey, and finally download a portable static build and add it to the user PATH.

CI integration: the GitHub Actions workflow includes a Windows runner step that runs this script before tests to ensure ffmpeg is present on Windows runners.

Note: if Chocolatey is used, it may require administrator privileges on the runner or machine. The installer script falls back to a portable download when admin rights are not available.
```

## Native runtime notes & test coverage

Small but important runtime requirements and tests were added to validate PDF upload and CI resilience:

- WeasyPrint (Markdown -> PDF): WeasyPrint depends on native libraries (GTK/Cairo/Pango). These are typically available on Linux runners (installed in CI by apt in the workflow). On Windows the repository includes a best-effort helper, but the recommended runner for reliable PDF rendering is Ubuntu (or a runner with those libs installed).

- FFmpeg (audio features / Windows): FFmpeg must be on PATH for audio processing and some markdown/media workflows. Use the provided `scripts/install_ffmpeg.ps1` on Windows or install via your package manager on Linux/macOS.

- Tests added:
   - `tests/test_send_pdf_s3.py` — exercises the S3 presigned-upload helper (mocked boto3 + HTTP PUT).
   - `tests/test_send_pdf_retries.py` — verifies retry/backoff behavior for rate-limited (429) responses.
   - `tests/test_send_pdf_fallback_and_5xx.py` — tests external-upload fallback when attachments are too large, and retry/backoff for 5xx failures.

   ---

   ## Run All Checks workflows (CI)

   Two manual GitHub Actions workflows were added to help run the full local checks (setup, smoke tests, and pytest) on hosted runners:

   - `Run All Checks (Windows)` — runs `scripts/run_all_checks.ps1` on `windows-latest`. It requires the repository secret `DISCORD_BOT_TOKEN` to be set before running.
   - `Run All Checks (Unix)` — runs `scripts/run_all_checks.sh` on `ubuntu-latest` (or macOS) and can be used when you prefer a Unix runner.

   How to use:

   1. Add the required secret in GitHub: Repository Settings → Secrets and variables → Actions → New repository secret
      - Name: `DISCORD_BOT_TOKEN`
      - Value: (your Discord bot token)

   2. Open the repository Actions tab, select the desired workflow (`Run All Checks (Windows)` or `Run All Checks (Unix)`), and click "Run workflow".

   Notes:
   - These workflows run the same local helper scripts used for development and provide a quick way to validate the repo on CI images. They are manual-run (workflow_dispatch) by design to avoid leaking secrets on forked PRs.
   - Do not store or commit secrets in the repository. Use GitHub Secrets for CI and a local `.env` for development (which is already gitignored).

   Quick links

   Windows: https://github.com/dktn7/proj-automation/actions/workflows/run_all_checks.yml

   Unix: https://github.com/dktn7/proj-automation/actions/workflows/run_all_checks_unix.yml

   You can also add a status badge for a workflow file using the Actions badge URL format. For example (manual-run workflows may not show a meaningful 'passing' state until they have run on the default branch):

   ```
   ![Run All Checks (Windows)](https://github.com/dktn7/proj-automation/actions/workflows/run_all_checks.yml/badge.svg?branch=main)
   ```

   Replace `run_all_checks.yml` with `run_all_checks_unix.yml` to show the Unix workflow badge.

   CI note: `run_all_checks` input

   When running the main `CI` workflow manually you can toggle the `run_all_checks` input to `true` to have CI dispatch the two hosted-runner workflows (`Run All Checks (Windows)` and `Run All Checks (Unix)`) after the primary jobs succeed. This is useful when you want the CI pipeline to trigger the full local-checks run on hosted Windows or Ubuntu runners without manually starting the separate workflows.


CI guidance:
- The GitHub Actions workflow installs Python dependencies from `requirements.txt` (now includes `boto3`). The workflow also contains diagnostic steps and best-effort installers to help tests run on Windows runners; for reliable PDF rendering use an Ubuntu runner or pre-install WeasyPrint native dependencies on the runner image.

If you plan to run PDF generation or the Markdown->PDF tests locally, install WeasyPrint native libs (GTK/Cairo/Pango) or run the tests on an Ubuntu runner that includes them.

### 2. Configure Discord Bot

1. Create Discord Application:
   - Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a New Application, then add a Bot and copy the bot token

2. Set Bot Permissions:
   - In "OAuth2" → "URL Generator", select scopes: `bot`, `applications.commands`
   - Recommended bot permissions:
     - Send Messages
     - Use Slash Commands
     - Create Public Threads
     - Send Messages in Threads
     - Embed Links
     - Attach Files

3. Configure Environment:
   ```sh
   cp bot/.env.template bot/.env
   ```

   Example `.env` values:
   ```
   DISCORD_BOT_TOKEN=your_discord_bot_token
   OPENAI_API_KEY=your_openai_api_key            # optional for AI features
   GITHUB_TOKEN=your_github_token                # required for GitHub integration
   ADMIN_USER_IDS=123456789012345678,987654321098765432  # comma-separated Discord user IDs
   LOG_LEVEL=INFO
   STRUCTURED_LOGS=false
   ```

4. Run the Bot:
   ```sh
   cd bot
   python main.py
   ```

   The bot will:
   - Initialize SQLite database for conversation memory
   - Validate configuration and show available features
   - Sync slash commands with Discord
   - Begin monitoring for DMs and code blocks

### 3. Configure GitHub Actions

1. Set Repository Secrets:
   - Repository Settings → "Secrets and variables" → "Actions"
   - Add:
     - `DISCORD_WEBHOOK_URL` — webhook for PDF notifications

2. Create Discord Webhook:
   - Discord channel settings → Integrations → Webhooks → New Webhook
   - Copy the Webhook URL

### 4. Test the Platform

1. Test PDF Conversion:
   ```sh
   python scripts/md_to_pdf.py docs/ideasheets/sample_idea.md -o output/
   ```

2. Test Discord Integration (with valid webhook):
   ```sh
   python scripts/send_pdf_to_discord.py output/sample_idea.pdf \
     --webhook "YOUR_WEBHOOK_URL" \
     --message "Test PDF from automation platform"
   ```

3. Test Complete Workflow:
   - Create a new Markdown file in `docs/ideasheets/`
   - Commit and push to GitHub
   - Watch GitHub Actions run the automation workflow
   - Check Discord for the generated PDF

### 5. Directory Structure

```
proj-automation/
├── .github/
│   └── workflows/
│       ├── automation.yml      # Main PDF generation workflow
│       ├── daily-standup.yml   # Daily standup workflow
│       └── standup-multi-channel.yml
├── bot/
│   ├── main.py                 # Enhanced Discord bot with AI features
│   ├── config.py               # Configuration management
│   ├── utils.py                # AI, OCR, file processing utilities
│   ├── requirements.txt        # Bot-specific dependencies
│   ├── .env.template           # Environment template
│   └── conversation_memory.db  # SQLite database (auto-created)
├── docs/
│   ├── ideasheets/            # Auto-generated from DM submissions
│   ├── helpdocs/              # Admin-uploaded documentation
│   ├── bot-integration.md     # Comprehensive bot documentation
│   └── PROCESSING_DOCUMENTATION.md
├── output/                    # Generated HTML/PDF files
├── scripts/
│   ├── md_to_pdf.py           # Markdown to PDF converter
│   └── send_pdf_to_discord.py # Discord webhook sender
├── requirements.txt            # All Python dependencies
├── .gitignore
└── README.md
```

---

## Usage

### Discord Bot Commands

Ask a question:
```
/ask How should we implement user authentication?
```
Creates a threaded discussion with AI response suggestions.

Summarize channel activity:
```
/summarize #general 24
```
Generates a summary of the last 24 hours of activity.

### Creating Idea Sheets

1. Create a new Markdown file in `docs/ideasheets/`
2. Write your idea using standard Markdown syntax
3. Commit and push to GitHub
4. GitHub Actions will automatically:
   - Convert your Markdown to a styled PDF
   - Post the PDF to your Discord channel
   - Store the PDF as a workflow artifact

Example idea sheet:
```markdown
# My Great Idea

## Overview
Brief description of the idea...

## Problem Statement
What problem does this solve?

## Proposed Solution
How will you solve it?

## Implementation
Technical details...

---
*Tags: #innovation #productivity #automation*
```

### Manual Script Usage

Convert Markdown to PDF:
```sh
# Single file
python scripts/md_to_pdf.py my_document.md

# Directory of files
python scripts/md_to_pdf.py docs/ideasheets/ -o output/

# With custom options
python scripts/md_to_pdf.py document.md -o output/ --verbose
```

Send PDF to Discord:
```sh
# Single PDF
python scripts/send_pdf_to_discord.py document.pdf \
  --webhook "https://discord.com/api/webhooks/..." \
  --message "New document ready!"

# Multiple PDFs
python scripts/send_pdf_to_discord.py output/*.pdf \
  --webhook "https://discord.com/api/webhooks/..." \
  --message "Batch upload complete"
```

---

## GitHub Actions Workflow

The automation workflow (`.github/workflows/automation.yml`) is triggered by:
- Push events that modify files in `docs/ideasheets/*.md`
- Pull requests that modify idea sheet files
- Manual workflow dispatch with an option to process all files

### Workflow Features
- Smart file detection: Only processes changed Markdown files
- PDF generation: Converts Markdown to styled PDFs
- Discord integration: Posts PDFs to Discord
- Artifact storage: Saves PDFs as downloadable artifacts
- PR comments: Updates pull requests with processing status
- Error handling: Comprehensive logging and error reporting

---

## Contributing

We welcome contributions! Please follow these steps:
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test them
4. Commit your changes: `git commit -m 'Add amazing feature'`
5. Push to the branch: `git push origin feature/amazing-feature`
6. Submit a pull request

### Development Setup
1. Install development dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Run tests (if you create any):
   ```sh
   python -m pytest tests/
   ```
3. Test your changes with the sample idea sheet:
   ```sh
   python scripts/md_to_pdf.py docs/ideasheets/sample_idea.md -o test_output/
   ```

---

## Troubleshooting

### Common Issues

PDF generation fails:
- Ensure `wkhtmltopdf` is installed and in your PATH
- Check that the Markdown file is valid
- Verify you have write permissions to the output directory

Discord bot not responding:
- Check that the bot token is correct in your `.env` file
- Verify the bot has the required permissions in your Discord server
- Ensure the bot is online and connected

GitHub Actions workflow fails:
- Check that `DISCORD_WEBHOOK_URL` secret is set correctly
- Verify the webhook URL is valid and the channel exists
- Check the Actions logs for specific error messages

PDF not sent to Discord:
- Verify the webhook URL is correct and active
- Check that the PDF file size is under 25MB
- Ensure your Discord server allows webhook messages

---

## License

MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact

For questions or support:
- Open a GitHub issue
- Contact the maintainer via Discord
- Submit a pull request with improvements

---

## Acknowledgments

- Built with [discord.py](https://discordpy.readthedocs.io/) for Discord integration
- PDF generation powered by [wkhtmltopdf](https://wkhtmltopdf.org/)
- Markdown processing with [Python-Markdown](https://python-markdown.github.io/)

---

## CI requirements for PDF / audio features

Some features (Markdown→PDF generation and audio processing) require native
libraries that are not always present on GitHub-hosted runners, especially on
Windows. The repository contains helper scripts and CI diagnostics to make
these requirements explicit.

What the CI does today
- The `test` job runs a diagnostic script `scripts/check_native_deps.py` that
   prints whether `ffmpeg` and the WeasyPrint Python package/native libs are
   available. This step is non-failing and is intended to provide clear logs
   for maintainers.
- On Windows runners the workflow also attempts to run `scripts/install_ffmpeg.ps1`.
   This script tries Scoop, Chocolatey, and finally downloads a portable ffmpeg
   build to the user profile. Installing WeasyPrint native libs on Windows is
   best-effort and may require admin rights.

Recommended options
- If you need reliable PDF rendering in CI, prefer an Ubuntu runner where the
   native packages can be installed via apt (`libcairo2`, `libpango-1.0-0`,
   `libpangocairo-1.0-0`, `libgdk-pixbuf2.0-0`, `libffi-dev`, `shared-mime-info`).
- For Windows-specific pipelines, consider using a self-hosted runner that has
   the required native libraries preinstalled, or enable Chocolatey and install
   the native runtimes there.
- If PDF/audio features are not required for every PR, keep the diagnostic
   script non-failing (the default) and run full PDF/audio integration tests on
   an explicit job or a scheduled workflow that uses an appropriate runner.

How to opt-in to failing CI on missing deps
- You can change the diagnostic step to fail CI if dependencies are missing by
   running `python scripts/check_native_deps.py --fail-on-missing` in the job.
   This was intentionally left as an opt-in change because GitHub-hosted
   Windows runners may not permit installing the required native libraries.

If you want, I can add a short Troubleshooting snippet with exact apt / choco
commands in this README or create a dedicated `docs/CI.md` with step-by-step
instructions for setting up self-hosted runners.
- Automated with [GitHub Actions](https://github.com/features/actions)
