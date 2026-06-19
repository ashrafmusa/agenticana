# Agenticana v2 Setup Script for Windows
# Run this once to install all dependencies
# Usage: Right-click → "Run with PowerShell" OR: powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
$AgenticanaRoot = $PSScriptRoot

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "   Agenticana v2 — Windows Setup" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check Node.js ─────────────────────────────────────────────────────
Write-Host "[1/5] Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  ✅ Node.js found: $nodeVersion" -ForegroundColor Green
}
catch {
    Write-Host "  ❌ Node.js not found. Please install from https://nodejs.org (v20+)" -ForegroundColor Red
    Write-Host "     After installing, re-run this script." -ForegroundColor Red
    exit 1
}

# ── Step 2: Check Python ──────────────────────────────────────────────────────
Write-Host "[2/5] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✅ Python found: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "  ❌ Python not found. Please install from https://python.org (3.11+)" -ForegroundColor Red
    exit 1
}

# ── Step 3: Install MCP Server dependencies ───────────────────────────────────
Write-Host "[3/5] Installing MCP Server dependencies..." -ForegroundColor Yellow
$mcpDir = Join-Path $AgenticanaRoot "mcp"
if (Test-Path $mcpDir) {
    Push-Location $mcpDir
    npm install --silent
    Pop-Location
    Write-Host "  ✅ MCP dependencies installed" -ForegroundColor Green
}
else {
    Write-Host "  ⚠️  mcp/ directory not found — skipping" -ForegroundColor DarkYellow
}

# ── Step 4: Install optional Python ML deps (sentence-transformers) ───────────
Write-Host "[4/5] Installing Python dependencies (optional: sentence-transformers)..." -ForegroundColor Yellow
$requirementsFile = Join-Path $AgenticanaRoot "requirements.txt"
if (Test-Path $requirementsFile) {
    python -m pip install -r $requirementsFile --quiet
    Write-Host "  ✅ Python dependencies installed" -ForegroundColor Green
}
else {
    # Install just the core dep
    python -m pip install sentence-transformers --quiet 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ sentence-transformers installed (enables ML embeddings)" -ForegroundColor Green
    }
    else {
        Write-Host "  ℹ️  sentence-transformers not installed — fallback TF embeddings will be used" -ForegroundColor DarkYellow
        Write-Host "     To install later: pip install sentence-transformers" -ForegroundColor DarkGray
    }
}

# ── Step 5: Generate VS Code workspace settings ───────────────────────────────
Write-Host "[5/5] Configuring VS Code + GitHub Copilot MCP integration..." -ForegroundColor Yellow

$vscodeDir = Join-Path $AgenticanaRoot ".vscode"
if (-not (Test-Path $vscodeDir)) {
    New-Item -ItemType Directory -Path $vscodeDir | Out-Null
}

$mcpServerPath = Join-Path $AgenticanaRoot "mcp\server.js"
$mcpConfigPath = Join-Path $vscodeDir "mcp.json"

$mcpConfig = @{
    servers = @{
        Agenticana = @{
            type    = "stdio"
            command = "node"
            args    = @($mcpServerPath.Replace("\", "/"))
            env     = @{
                Agenticana_ROOT = $AgenticanaRoot.Replace("\", "/")
            }
        }
    }
} | ConvertTo-Json -Depth 5

Set-Content -Path $mcpConfigPath -Value $mcpConfig -Encoding UTF8
Write-Host "  ✅ VS Code MCP config written: .vscode/mcp.json" -ForegroundColor Green

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "   ✅ Setup Complete!" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Quick Start Commands:" -ForegroundColor White
Write-Host "  • Test ReasoningBank:" -ForegroundColor Gray
Write-Host "    python scripts/reasoning_bank.py stats" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  • Test Model Router:" -ForegroundColor Gray
Write-Host "    python scripts/router_cli.py `"fix a bug in login`"" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  • Start MCP Server (for Copilot tools):" -ForegroundColor Gray
Write-Host "    cd mcp && node server.js" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  • VS Code Copilot integration:" -ForegroundColor Gray
Write-Host "    Open VS Code → GitHub Copilot Chat → Tools icon → Enable 'Agenticana'" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  • Record a decision after completing a task:" -ForegroundColor Gray
Write-Host "    python scripts/reasoning_bank.py record --task `"X`" --decision `"Y`" --outcome `"Z`" --success true" -ForegroundColor DarkCyan
Write-Host ""
