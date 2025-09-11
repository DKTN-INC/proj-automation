<#
Run all local checks: setup venv, install deps, run smoke-tests and pytest.
Usage: Open PowerShell in repo root and run:
    .\scripts\run_all_checks.ps1
#>

Write-Host "=== Run all checks for proj-automation ===" -ForegroundColor Cyan

try {
    # Run setup helper (creates venv, installs requirements)
    Write-Host "Running setup_local_env.ps1..."
    & .\scripts\setup_local_env.ps1
} catch {
    Write-Warning "setup_local_env.ps1 failed: $_"
}

# Activate venv if present
if (Test-Path -Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment"
    . .\.venv\Scripts\Activate.ps1
} else {
    Write-Warning "Virtual environment not found; continuing with system Python"
}

# Load .env into environment for the remainder of the script if present
if (Test-Path -Path ".env") {
    Write-Host "Loading .env into environment for checks"
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*#") { return }
        if ($_ -match "^\s*$") { return }
        $parts = $_ -split "=", 2
        if ($parts.Count -eq 2) {
            $name = $parts[0].Trim()
            $value = $parts[1].Trim()
            if (-not [string]::IsNullOrEmpty($name)) {
                # Use Set-Item to assign to an environment variable when the name is dynamic
                Set-Item -Path ("env:" + $name) -Value $value -Force
            }
        }
    }
}

# Optional enforcement: if ENFORCE_REQUIRED_SECRETS=true, fail when required secrets are missing
$enforce = $env:ENFORCE_REQUIRED_SECRETS -eq 'true'
if ($enforce) {
    Write-Host "ENFORCE_REQUIRED_SECRETS enabled - verifying required secrets..." -ForegroundColor Yellow
    $missing = @()
    if (-not $env:DISCORD_BOT_TOKEN) { $missing += 'DISCORD_BOT_TOKEN' }
    if ($missing.Count -gt 0) {
        Write-Error "Required secrets missing: $($missing -join ', '); aborting as ENFORCE_REQUIRED_SECRETS=true"
        exit 2
    } else {
        Write-Host "All required secrets present" -ForegroundColor Green
    }
}

# Run smoke tests
Write-Host "Running smoke tests..."
python scripts/run_smoke_tests.py

# Run pytest full suite
Write-Host "Running pytest full suite..."
python -m pytest -q

Write-Host "All checks completed." -ForegroundColor Green
