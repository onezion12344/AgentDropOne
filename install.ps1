# ═══════════════════════════════════════════════════════════
#  AgentDropOne — Windows PowerShell Installer
#
#  Usage:
#    irm https://raw.githubusercontent.com/onezion12344/AgentDropOne/main/install.ps1 | iex
#
#  Or with a bundle:
#    .\install.ps1 -Bundle bundle.zip
# ═══════════════════════════════════════════════════════════

param(
    [string]$Bundle = "",
    [switch]$DockerPack,
    [switch]$Update,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$Repo = "https://github.com/onezion12344/AgentDropOne.git"
$InstallDir = if ($env:AGENTDROPONE_DIR) { $env:AGENTDROPONE_DIR } else { "$env:USERPROFILE\.agentdropone" }

# ── Helpers ────────────────────────────────────────────────
function Write-Info  { Write-Host "[INFO]  $args" -ForegroundColor Cyan }
function Write-Ok    { Write-Host "[OK]    $args" -ForegroundColor Green }
function Write-Warn  { Write-Host "[WARN]  $args" -ForegroundColor Yellow }
function Write-Err   { Write-Host "[ERROR] $args" -ForegroundColor Red }
function Has-Cmd($cmd) { $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue) }

# ── Banner ─────────────────────────────────────────────────
Write-Host ""
Write-Host "  ╔═══════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "  ║     AgentDropOne Installer v0.4.0     ║" -ForegroundColor Magenta
Write-Host "  ║   Windows PowerShell Edition           ║" -ForegroundColor Magenta
Write-Host "  ╚═══════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

if ($Help) {
    Write-Host "Usage:"
    Write-Host "  .\install.ps1                        Install AgentDropOne only"
    Write-Host "  .\install.ps1 -Bundle bundle.zip     Install + setup from bundle"
    Write-Host "  .\install.ps1 -DockerPack            Pack as Docker image"
    Write-Host "  .\install.ps1 -Update                Update to latest"
    exit 0
}

# ── OS Detection ───────────────────────────────────────────
Write-Info "Detected: Windows ($env:PROCESSOR_ARCHITECTURE)"

# ── Prerequisites ──────────────────────────────────────────
Write-Info "Checking prerequisites..."

# Python
if (Has-Cmd "python") {
    $pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    Write-Ok "Python $pyVer already installed"
} elseif (Has-Cmd "python3") {
    $pyVer = python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    Write-Ok "Python $pyVer already installed"
} else {
    Write-Info "Installing Python..."
    if (Has-Cmd "winget") {
        winget install Python.Python.3.12 --silent --accept-package-agreements
    } elseif (Has-Cmd "choco") {
        choco install python3 -y
    } else {
        Write-Err "Please install Python 3.9+ from https://python.org"
        exit 1
    }
    Write-Ok "Python installed"
}

# Git
if (Has-Cmd "git") {
    Write-Ok "Git already installed"
} else {
    Write-Info "Installing Git..."
    if (Has-Cmd "winget") {
        winget install Git.Git --silent --accept-package-agreements
    } elseif (Has-Cmd "choco") {
        choco install git -y
    } else {
        Write-Err "Please install Git from https://git-scm.com"
        exit 1
    }
    Write-Ok "Git installed"
}

# Node.js
if (Has-Cmd "node") {
    Write-Ok "Node.js already installed"
} else {
    Write-Info "Installing Node.js..."
    if (Has-Cmd "winget") {
        winget install OpenJS.NodeJS.LTS --silent --accept-package-agreements
    } elseif (Has-Cmd "choco") {
        choco install nodejs-lts -y
    }
    Write-Warn "Node.js install may need terminal restart"
}

# Docker (optional)
if (Has-Cmd "docker") {
    Write-Ok "Docker already installed"
} else {
    Write-Info "Docker not found — skipping (optional)"
}

Write-Ok "Prerequisites ready"
Write-Host ""

# ── Clone AgentDropOne ─────────────────────────────────────
if (Test-Path "$InstallDir\.git") {
    Write-Info "AgentDropOne already installed. Updating..."
    Set-Location $InstallDir
    git pull --quiet 2>$null
} else {
    Write-Info "Cloning AgentDropOne..."
    if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force }
    git clone --quiet $Repo $InstallDir
}
Write-Ok "AgentDropOne ready at $InstallDir"

# ── PATH setup ─────────────────────────────────────────────
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*agentdropone*") {
    [Environment]::SetEnvironmentVariable("Path", "$InstallDir;$currentPath", "User")
    $env:Path = "$InstallDir;$env:Path"
    Write-Info "Added to PATH (restart terminal to pick up)"
}

# ── Bundle mode ────────────────────────────────────────────
function Run-Bundle($path) {
    if (-not (Test-Path $path)) {
        Write-Err "Bundle not found: $path"
        exit 1
    }
    Write-Info "Running setup with bundle: $path"
    python "$InstallDir\onesync-skills\full-migrate\agentdropone-setup.py" $path
}

# ── Main ───────────────────────────────────────────────────
if ($Update) {
    Write-Ok "Updated to latest version"
    exit 0
}

Write-Host ""
Write-Host "  ╔═══════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║    AgentDropOne installed!             ║" -ForegroundColor Green
Write-Host "  ╚═══════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

if ($Bundle) {
    Run-Bundle $Bundle
} else {
    $answer = Read-Host "  No bundle provided. Create migration bundle now? [Y/n]"
    if ($answer -eq "" -or $answer -match "^[Yy]") {
        $bundlePath = "$env:USERPROFILE\Desktop\agentdropone-bundle.zip"
        Write-Info "Creating bundle at $bundlePath..."
        Set-Location $InstallDir
        python -m agentsync.cli export-secrets -o "$env:TEMP\secrets.json"
        python -m agentsync.cli chat-export -o "$env:TEMP\chat-export"
        python -m agentsync.cli discover > "$env:TEMP\discover.txt"
        Compress-Archive -Path "$env:TEMP\secrets.json","$env:TEMP\chat-export","$env:TEMP\discover.txt" -DestinationPath $bundlePath -Force
        Write-Ok "Bundle created: $bundlePath"
        Write-Host ""
        Write-Host "  Transfer to new machine, then run:"
        Write-Host "    .\install.ps1 -Bundle bundle.zip"
    } else {
        Write-Host ""
        Write-Host "  Manual export later:"
        Write-Host "    cd $InstallDir"
        Write-Host "    python -m agentsync.cli scan"
        Write-Host "    python -m agentsync.cli export-secrets"
    }
}
