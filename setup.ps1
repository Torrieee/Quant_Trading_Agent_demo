# Create project-local venv and install all dependencies.
# Usage (PowerShell): .\setup.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating .venv ..."
    python -m venv .venv
}

$py = ".\.venv\Scripts\python.exe"
$pip = ".\.venv\Scripts\pip.exe"

Write-Host "Installing dependencies into .venv ..."
& $pip install --upgrade pip
& $pip install -e ".[dev]"

Write-Host ""
Write-Host "Done. Activate and run tests:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python -m pytest tests/ -v"
Write-Host "  python scripts/run_harness.py --gate"
