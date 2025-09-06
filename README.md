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
- **`/ask <question>`**: Create threaded discussions for team questions
- **`/summarize [channel] [hours]`**: Generate summaries with participation metrics
- **`/submit-idea <title> <description> [tags]`**: Submit ideas to ideasheets collection
- **`/get-doc <filename> [format]`**: Retrieve documents in markdown/html/pdf format

#### Traditional Commands  
- **`!createpr <repo> <title> <body>`**: Create GitHub pull requests
- **`!google <query>`**: Web search using DuckDuckGo
- **`!github_issues <repo> [state] [limit]`**: Fetch repository issues

### 🧠 AI-Powered Features
- **DM Markdown Intake**: Send markdown content via DM, automatically saved with AI tags
- **Voice Transcription**: Convert voice messages to text using OpenAI Whisper
- **Image OCR**: Extract text from images using pytesseract with preprocessing
- **Code Review**: Automatic Python linting with flake8 and AI-generated unit tests
- **Conversation Memory**: Persistent per-user conversation history with SQLite
- **Language Detection**: Auto-detect programming languages in code snippets

### 📁 File Processing & Management
- **Admin File Uploads**: Authorized users can upload files to docs/helpdocs/
- **Multi-format Output**: Automatic HTML and PDF generation from markdown
- **Smart File Handling**: Support for images, audio, and document files
- **Syntax Highlighting**: Enhanced code presentation in responses

### 🔗 External Integrations
- **GitHub API**: Create PRs, fetch issues, repository management
- **OpenAI Integration**: GPT models for content analysis and generation
- **Web Search**: Built-in search functionality
- **Discord Webhooks**: Professional notifications with rich embeds

### Automated PDF Generation
- **Markdown Processing**: Converts Markdown files to professionally styled PDFs
- **Template System**: Consistent styling with metadata, timestamps, and branding
- **Syntax Highlighting**: Code blocks with proper formatting
- **Table Support**: Full table rendering in PDF output

### CI/CD Integration
- **GitHub Actions Workflow**: Automatically triggered on Markdown file changes
- **Smart Detection**: Only processes changed files for efficiency
- **Discord Publishing**: Automatic PDF delivery to Discord channels via webhooks
- **Artifact Storage**: PDFs stored as GitHub Actions artifacts with 30-day retention
- **PR Comments**: Automatic status updates on pull requests

### Discord Webhook Integration
- **Professional Notifications**: Rich embeds with file information and metadata
- **Batch Processing**: Handle multiple PDFs efficiently
- **Error Handling**: Robust error handling with detailed logging
- **File Size Validation**: Automatic checking against Discord's 25MB limit

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
```

### 2. Configure Discord Bot

1. **Create Discord Application:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Go to "Bot" section and click "Add Bot"
   - Copy the bot token

2. **Set Bot Permissions:**
   - In Discord Developer Portal, go to "OAuth2" → "URL Generator"
   - Select "bot" and "applications.commands" scopes
   - Select these bot permissions:
     - Send Messages
     - Use Slash Commands
     - Create Public Threads
     - Send Messages in Threads
     - Embed Links
     - Attach Files

3. **Configure Environment:**
   ```sh
   cp bot/.env.template bot/.env
   # Edit bot/.env and add your tokens:
   # - Discord bot token (required)
   # - OpenAI API key (for AI features)
   # - GitHub token (for GitHub integration)
   # - Admin user IDs (for file upload permissions)
   ```

4. **Run the Bot:**
   ```sh
   cd bot
   python main.py
   ```

   The bot will automatically:
   - Initialize SQLite database for conversation memory
   - Validate configuration and show available features
   - Sync slash commands with Discord
   - Begin monitoring for DMs and code blocks

### 3. Configure GitHub Actions

1. **Set Repository Secrets:**
   - Go to your GitHub repository settings
   - Navigate to "Secrets and variables" → "Actions"
   - Add these secrets:
     - `DISCORD_WEBHOOK_URL`: Your Discord webhook URL for PDF notifications

2. **Create Discord Webhook:**
   - In your Discord server, go to channel settings
   - Go to "Integrations" → "Webhooks"
   - Click "New Webhook" and copy the URL

### 4. Test the Platform

1. **Test PDF Conversion:**
   ```sh
   python scripts/md_to_pdf.py docs/ideasheets/sample_idea.md -o output/
   ```

2. **Test Discord Integration (with valid webhook):**
   ```sh
   python scripts/send_pdf_to_discord.py output/sample_idea.pdf \
     --webhook "YOUR_WEBHOOK_URL" \
     --message "Test PDF from automation platform"
   ```

3. **Test Complete Workflow:**
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

**Ask a Question:**
```
/ask How should we implement user authentication?
```
This creates a threaded discussion where team members can collaborate.

**Summarize Channel Activity:**
```
/summarize #general 24
```
This generates a summary of the last 24 hours of activity in the #general channel.

### Creating Idea Sheets

1. Create a new Markdown file in `docs/ideasheets/`
2. Write your idea using standard Markdown syntax
3. Commit and push to GitHub
4. GitHub Actions will automatically:
   - Convert your Markdown to a styled PDF
   - Post the PDF to your Discord channel
   - Store the PDF as a workflow artifact

**Example Idea Sheet Structure:**
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

**Convert Markdown to PDF:**
```sh
# Single file
python scripts/md_to_pdf.py my_document.md

# Directory of files
python scripts/md_to_pdf.py docs/ideasheets/ -o output/

# With custom options
python scripts/md_to_pdf.py document.md -o output/ --verbose
```

**Send PDF to Discord:**
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

- **Push events** that modify files in `docs/ideasheets/*.md`
- **Pull requests** that modify idea sheet files
- **Manual workflow dispatch** with option to process all files

### Workflow Features:

- **Smart file detection**: Only processes changed Markdown files
- **PDF generation**: Converts Markdown to styled PDFs
- **Discord integration**: Automatically posts PDFs to Discord
- **Artifact storage**: Saves PDFs as downloadable artifacts
- **PR comments**: Updates pull requests with processing status
- **Error handling**: Comprehensive logging and error reporting

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

**PDF generation fails:**
- Ensure `wkhtmltopdf` is installed and in your PATH
- Check that the Markdown file is valid
- Verify you have write permissions to the output directory

**Discord bot not responding:**
- Check that the bot token is correct in your `.env` file
- Verify the bot has the required permissions in your Discord server
- Ensure the bot is online and connected

**GitHub Actions workflow fails:**
- Check that `DISCORD_WEBHOOK_URL` secret is set correctly
- Verify the webhook URL is valid and the channel exists
- Check the Actions logs for specific error messages

**PDF not sent to Discord:**
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
- Automated with [GitHub Actions](https://github.com/features/actions)