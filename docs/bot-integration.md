# Discord Bot Integration Documentation

## Overview

The Project Automation Discord Bot is a comprehensive AI-powered assistant that enhances team collaboration through intelligent document processing, code analysis, and workflow automation. The bot seamlessly integrates with your existing Discord server to provide advanced features including DM-based idea submission, OCR, voice transcription, and automated code review.

## Features

### 🤖 AI-Powered Features
- **Automatic Tagging**: AI generates relevant tags for submitted content
- **Voice Transcription**: Convert voice messages to text (placeholder)
- **Unit Test Generation**: AI-generated unit test stubs for Python code
- **Conversation Memory**: Persistent per-user conversation history using SQLite
- **Content Analysis**: Intelligent content categorization and processing

### 📝 Document Management
- **DM Markdown Intake**: Send markdown content via DM to automatically save to `docs/ideasheets/`
- **Multi-format Output**: Automatic HTML and PDF generation from markdown
- **Document Retrieval**: Access documents via slash commands with format conversion
- **Admin File Uploads**: Authorized users can upload files to `docs/helpdocs/`

### 🔍 Code Analysis & Review
- **Automatic Code Review**: Monitors channels for code blocks and provides flake8 lint results
- **Language Detection**: Auto-detects programming language in code snippets
- **Syntax Highlighting**: Enhanced code presentation in bot responses
- **Thread-based Reviews**: Creates discussion threads for code analysis

### 🖼️ Image & Audio Processing
- **OCR Text Extraction**: Extract text from images using pytesseract
- **Voice Message Support**: Transcribe audio messages to text
- **File Type Detection**: Intelligent handling of different file formats
- **Image Preprocessing**: Enhanced OCR accuracy through image optimization

### 🔗 External Integrations
- **GitHub Integration**: Create pull requests and fetch issues via bot commands
- **Web Search**: Built-in search functionality using DuckDuckGo
- **Webhook Support**: Discord webhook integration for notifications

## Installation & Setup

### Prerequisites

Before setting up the bot, ensure you have the following system dependencies installed:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install wkhtmltopdf tesseract-ocr python3-dev

# macOS (using Homebrew)
brew install wkhtmltopdf tesseract

# Windows
# Download wkhtmltopdf from: https://wkhtmltopdf.org/downloads.html
# Download tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
```

### 1. Install Python Dependencies

```bash
cd bot/
pip install -r requirements.txt
```

### 2. Discord Bot Setup

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
     - Read Message History

3. **Invite Bot to Server:**
   - Use the generated URL to invite the bot to your Discord server
   - Ensure the bot has the necessary permissions in target channels

### 3. Environment Configuration

1. **Copy Template:**
   ```bash
   cp .env.template .env
   ```

2. **Configure Environment Variables:**
  ```bash
  # Required (prefer BOT_TOKEN; DISCORD_BOT_TOKEN accepted for backward compatibility)
  BOT_TOKEN=your_discord_bot_token_here
   
  # Optional but recommended
  GOOGLE_API_KEY=your_google_api_key_here
  GITHUB_TOKEN=your_github_personal_access_token_here
  DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
   
  # Admin configuration
  DISCORD_ADMIN_IDS=123456789012345678,987654321098765432
  ```

### 4. Optional Services Setup

#### Google AI API (for AI features)
1. Go to [Google AI Studio](https://aistudio.google.com/) and create an API key.
2. Add to `.env` file as `GOOGLE_API_KEY`

#### GitHub Integration
1. Generate Personal Access Token with repo permissions
2. Add to `.env` file as `GITHUB_TOKEN`

### 5. Running the Bot

```bash
cd bot/
python main.py
```

Or using python-dotenv:
```bash
cd bot/
python -c "from dotenv import load_dotenv; load_dotenv(); exec(open('main.py').read())"
```

## Commands Reference

### Slash Commands

#### `/ask <question>`
Creates a threaded discussion for team questions.
- **Parameters:** `question` (required) - The question to ask
- **Example:** `/ask How should we implement user authentication?`

#### `/summarize [channel] [hours]`
Generates summaries of channel activity with participation metrics.
- **Parameters:** 
  - `channel` (optional) - Channel to summarize (defaults to current)
  - `hours` (optional) - Hours to look back (default: 24)
- **Example:** `/summarize #development 48`

#### `/submit-idea <title> <description> [tags]`
Submit a new idea to the ideasheets collection.
- **Parameters:**
  - `title` (required) - Title of the idea
  - `description` (required) - Detailed description
  - `tags` (optional) - Comma-separated tags
- **Example:** `/submit-idea "API Gateway" "Implement centralized API gateway for microservices" "api,architecture,microservices"`

#### `/get-doc <filename> [format]`
Retrieve documents from ideasheets or helpdocs.
- **Parameters:**
  - `filename` (required) - Name of file to retrieve
  - `format` (optional) - Output format: markdown/html/pdf
- **Example:** `/get-doc sample_idea.md pdf`

### Traditional Commands (with ! prefix)

#### `!createpr <repo_name> <title> <body>`
Create a GitHub pull request.
- **Example:** `!createpr myorg/myrepo "Add new feature" "This PR adds authentication support"`

#### `!google <query>`
Search the web using DuckDuckGo.
- **Example:** `!google Python async best practices`

#### `!github_issues <repo_name> [state] [limit]`
Get GitHub issues for a repository.
- **Parameters:**
  - `repo_name` (required) - Repository in format "owner/repo"
  - `state` (optional) - "open" or "closed" (default: open)
  - `limit` (optional) - Number of issues to show (default: 5)
- **Example:** `!github_issues microsoft/vscode open 10`

## Workflow Examples

### 1. Idea Submission via DM

**User Action:**
```
[Direct Message to Bot]
# Mobile App Redesign

## Problem
Current mobile app has poor user engagement and high bounce rate.

## Solution
Redesign with modern UI/UX principles:
- Simplified navigation
- Dark mode support
- Offline functionality
- Push notifications

## Expected Outcome
- 30% increase in user retention
- Improved app store ratings
```

**Bot Response:**
- Saves markdown to `docs/ideasheets/mobile-app-redesign.md`
- Generates AI tags: "mobile, design, ux, engagement"
- Creates HTML and PDF versions
- Sends confirmation with file attachments

### 2. Code Review Automation

**User Posts Code:**
```python
def authenticate_user(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.password == password:
        return user
    return None
```

**Bot Response:**
- Creates analysis thread
- Provides flake8 lint results
- Suggests security improvements
- Generates unit test stubs

### 3. Voice Message Transcription

**User Action:**
- Sends voice message in DM

**Bot Response:**
- Downloads and processes audio
- Uses a placeholder for transcription as the current AI provider does not support it.
- Returns formatted text transcript
- Optionally saves to conversation memory

### 4. OCR Document Processing

**User Action:**
- Sends image with text content via DM

**Bot Response:**
- Preprocesses image for better OCR
- Extracts text using pytesseract
- Returns formatted text results
- Handles multiple languages

## Configuration Options

### Bot Configuration (config.py)

```python
# File size limits
max_file_size = 25 * 1024 * 1024  # 25MB Discord limit

# AI model settings
ai_model = "gpt-3.5-turbo"  # or "gpt-4"
whisper_model = "whisper-1"

# Admin user management
admin_user_ids = [123456789012345678]

# Directory paths
ideasheets_dir = "docs/ideasheets"
helpdocs_dir = "docs/helpdocs"
output_dir = "output"
```

### Feature Toggles

Features automatically disable if required services are unavailable:

- **AI Features:** Disabled if `GOOGLE_API_KEY` not provided
- **GitHub Integration:** Disabled if `GITHUB_TOKEN` not provided
- **Webhook Features:** Disabled if `DISCORD_WEBHOOK_URL` not provided

### Database Configuration

SQLite database for conversation memory:
- **Location:** `bot/conversation_memory.db`
- **Tables:** `conversations`, `user_preferences`
- **Auto-initialization:** Creates tables on first run

## Security Considerations

### File Upload Security
- File size validation (25MB Discord limit)
- Admin-only access to helpdocs uploads
- Temporary file cleanup after processing
- File type validation for OCR/transcription

### API Security
- Environment variable storage for tokens
- Rate limiting on external API calls
- Error handling prevents token exposure
- Secure temporary file handling

### User Privacy
- Conversation memory stored locally
- No persistent storage of file contents
- Audit logging for admin actions
- Optional data retention policies

## Troubleshooting

### Common Issues

#### Bot Not Responding
1. Check Discord token validity
2. Verify bot permissions in server
3. Ensure bot is online in Discord
4. Check logs for error messages

#### AI Features Not Working
1. Verify `GOOGLE_API_KEY` is set correctly
2. Check Google AI API quota/billing
3. Ensure network connectivity
4. Review API model availability

#### OCR/Voice Processing Failing
1. Install system dependencies:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr
   
   # Check installation
   tesseract --version
   ```
2. Verify file format support
3. Check file size limits
4. Review error logs

#### GitHub Integration Issues
1. Verify GitHub token permissions
2. Check repository access rights
3. Ensure token hasn't expired
4. Review rate limiting

### Logging

The bot provides comprehensive logging:

```python
# Log levels
logging.INFO    # General operations
logging.WARNING # Configuration issues
logging.ERROR   # Operation failures
logging.DEBUG   # Detailed debugging (set via environment)
```

**Log Locations:**
- Console output for immediate feedback
- Optional file logging (configure in `main.py`)
- Discord error messages for user feedback

### Performance Optimization

#### Memory Usage
- Temporary file cleanup after processing
- Database connection pooling
- Large file streaming for uploads
- Garbage collection for AI processing

#### Response Times
- Async processing for heavy operations
- Deferred responses for slow commands
- Caching for repeated operations
- Background processing for file conversion

## Development & Customization

### Adding New Commands

1. **Slash Command Example:**
```python
@bot.tree.command(name='custom', description='Custom command')
async def custom_command(interaction: discord.Interaction, param: str):
    await interaction.response.send_message(f"Custom: {param}")
```

2. **Traditional Command Example:**
```python
@bot.command(name='custom')
async def custom_command(ctx, *, args):
    await ctx.send(f"Custom: {args}")
```

### Adding New File Processors

```python
class CustomProcessor:
    @staticmethod
    async def process_file(file_path: Path) -> str:
        # Custom processing logic
        return processed_content

# Register in utils.py
custom_processor = CustomProcessor()
```

### Extending AI Features

```python
async def custom_ai_feature(content: str) -> str:
    if not ai_helper.available:
        return "AI not available"
    
    response = await model.generate_content_async(content)
    return response.text
```

## Support & Contributing

### Getting Help
- Open GitHub issues for bugs and feature requests
- Check existing documentation and troubleshooting guides
- Review logs for detailed error information
- Contact maintainers via Discord

### Contributing
- Fork the repository
- Create feature branches
- Add tests for new functionality
- Update documentation
- Submit pull requests

### Feature Requests
Priority features for future development:
- Multi-language OCR support
- Advanced AI conversation features
- Custom webhook integrations
- Plugin system for extensions
- Team analytics dashboard

## License

This Discord bot integration is part of the Project Automation platform and follows the same MIT license terms. See the main repository LICENSE file for details.