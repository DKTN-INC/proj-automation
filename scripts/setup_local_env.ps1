<#
Quick local setup helper for Windows PowerShell.
Usage: Run from repo root in PowerShell (Admin not required for venv).
    .\scripts\setup_local_env.ps1

This will create a venv, install dependencies, copy .env.example -> .env if missing,
attempt to install ffmpeg via the existing installer, and optionally run tests.
#>

Write-Host "Starting local setup for proj-automation" -ForegroundColor Cyan

if (-not (Test-Path -Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
} else {
    Write-Host "Virtual environment already exists: .venv"
}

Write-Host "Activating virtual environment..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip and installing requirements..."
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path -Path ".env")) {
    if (Test-Path -Path ".env.example") {
        Copy-Item -Path .env.example -Destination .env
        Write-Host "Created .env from .env.example — please edit .env with your secrets before running the bot." -ForegroundColor Yellow
    } else {
        Write-Host ".env.example not found — create a .env file with required variables (DISCORD_BOT_TOKEN, etc.)." -ForegroundColor Yellow
    }
} else {
    Write-Host ".env already exists."
}

Write-Host "Attempting Windows ffmpeg helper (best-effort)..."
try {
    & .\scripts\install_ffmpeg.ps1
} catch {
    Write-Warning "install_ffmpeg.ps1 failed or was not permitted in this environment. You may need to install ffmpeg manually." 
}

Write-Host "Setup complete. To run tests: pytest -q" -ForegroundColor Green
Write-Host "To start the bot: python bot\main.py" -ForegroundColor Green
