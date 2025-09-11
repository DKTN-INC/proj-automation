#!/usr/bin/env bash
# Quick local setup helper for Unix-like systems
set -euo pipefail
echo "Starting local setup for proj-automation"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo ".env created from .env.example — edit it with your secrets before running the bot"
  else
    echo ".env.example not found — create a .env file with required variables (DISCORD_BOT_TOKEN, etc.)"
  fi
else
  echo ".env already exists"
fi

echo "Attempting to install native runtime (ffmpeg + weasyprint deps) on Debian/Ubuntu (best-effort)"
if [ "$(uname -s)" = "Linux" ]; then
  sudo apt-get update
  sudo apt-get install -y ffmpeg libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info fonts-dejavu-core || true
fi

echo "Setup complete. To run tests: pytest -q"
echo "To start the bot: python bot/main.py"
