import os

# Load secrets from environment variables or .env file
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")
DISCORD_ADMIN_ID = os.getenv("DISCORD_ADMIN_ID")  # Discord user ID string

# Repo-relative content paths
IDEA_SHEET_DIR = "../docs/ideasheets/"
HELP_DOCS_DIR = "../docs/helpdocs/"
DB_PATH = "bot_memory.db"

# Team/Persona configuration
TEAM_NAME = os.getenv("TEAM_NAME", "Project Automation Team")
TEAM_PURPOSE = os.getenv(
    "TEAM_PURPOSE",
    "Design, build, and deliver high-quality software efficiently and safely."
)
TEAM_BOT_NAME = os.getenv("TEAM_BOT_NAME", "Probo")
DEFAULT_REPO = os.getenv("DEFAULT_REPO", "dktn7/proj-automation")  # owner/repo
