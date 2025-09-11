<#
scripts/install_ffmpeg.ps1

PowerShell helper to install FFmpeg on Windows developer machines or CI.

Behavior (best-effort):
- If ffmpeg already on PATH, do nothing.
- Try user-level installation with Scoop (if installed).
- Fall back to Chocolatey (requires admin privileges).
- If neither is available, download a portable static build (BtbN) and extract to
  %USERPROFILE%\bin\ffmpeg, then add that directory to the user PATH.

Usage (developer):
  # Open PowerShell (preferably as Administrator for choco path installs)
  ./scripts/install_ffmpeg.ps1

Notes:
- This script makes a persistent change to the user PATH when downloading the
  portable build. A new shell is required for PATH to take effect.
- CI usage: call this script in a setup step on Windows runners before running
  tests that require ffmpeg.
#>

set -e

function Write-Info($msg) { Write-Host "[info] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Write-ErrorExit($msg) { Write-Host "[error] $msg" -ForegroundColor Red; exit 1 }

# Check if ffmpeg already available
function Test-FFmpegExists {
    $null -ne (Get-Command ffmpeg -ErrorAction SilentlyContinue)
}

if (Test-FFmpegExists) {
    Write-Info "ffmpeg is already installed and on PATH. Nothing to do."
    exit 0
}

# Try Scoop (user-level)
function Try-ScoopInstall {
    if (Get-Command scoop -ErrorAction SilentlyContinue) {
        try {
            Write-Info "Scoop detected — installing ffmpeg via scoop..."
            scoop install ffmpeg
            if (Test-FFmpegExists) { Write-Info "ffmpeg installed via scoop."; return $true }
        } catch {
            Write-Warn "Scoop install failed: $_"
        }
    }
    return $false
}

# Try Chocolatey (may require admin)
function Try-ChocoInstall {
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        try {
            Write-Info "Chocolatey detected — installing ffmpeg via choco..."
            choco install ffmpeg -y
            if (Test-FFmpegExists) { Write-Info "ffmpeg installed via choco."; return $true }
        } catch {
            Write-Warn "Chocolatey install failed: $_"
        }
    }
    return $false
}

# Download portable static build and add to user PATH
function Try-DownloadPortable {
    Write-Info "Downloading portable ffmpeg build (BtbN builds) and extracting..."

    $tmp = [IO.Path]::Combine($env:TEMP, "ffmpeg_download.zip")
    $destDir = [IO.Path]::Combine($env:USERPROFILE, "bin", "ffmpeg")

    if (-Not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }

    $url = 'https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-release-essentials.zip'

    try {
        Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing -ErrorAction Stop
    } catch {
        Write-Warn "Failed to download ffmpeg archive: $_"
        return $false
    }

    try {
        Expand-Archive -Path $tmp -DestinationPath $destDir -Force
    } catch {
        Write-Warn "Failed to extract ffmpeg archive: $_"
        return $false
    } finally {
        Remove-Item $tmp -ErrorAction SilentlyContinue
    }

    # The archive typically contains a directory like ffmpeg-*-essentials_build\bin
    $binPath = Get-ChildItem -Path $destDir -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $binPath) {
        Write-Warn "Could not locate extracted ffmpeg bin directory under $destDir"
        return $false
    }

    $ffmpegBin = Join-Path $binPath.FullName 'bin'
    if (-Not (Test-Path $ffmpegBin)) {
        # Maybe the archive already placed bin directly under destDir
        $ffmpegBin = $binPath.FullName
    }

    if (-Not (Test-Path $ffmpegBin)) {
        Write-Warn "ffmpeg bin directory not found after extraction"
        return $false
    }

    # Add to user PATH if not already present
    $currentUserPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
    if ($currentUserPath -notlike "*$ffmpegBin*") {
        $newPath = "$currentUserPath;$ffmpegBin"
        [Environment]::SetEnvironmentVariable('PATH', $newPath, 'User')
        Write-Info "Added ffmpeg bin to user PATH: $ffmpegBin"
        Write-Info "You may need to start a new shell for PATH changes to take effect."
    } else {
        Write-Info "ffmpeg bin already present in user PATH"
    }

    # Validate installation
    if (Test-FFmpegExists) { Write-Info "ffmpeg available after portable install."; return $true }

    Write-Warn "ffmpeg not found on PATH after portable install. You may need to add $ffmpegBin to PATH manually."
    return $false
}

# Run installation attempts
if (Try-ScoopInstall) { exit 0 }
if (Try-ChocoInstall) { exit 0 }

Write-Info "Falling back to portable download and user PATH addition..."
if (Try-DownloadPortable) { exit 0 }

Write-ErrorExit "All install attempts failed. Please install ffmpeg manually or use a package manager."
