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
Write-Host "Done. Activate and run:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python -m pytest tests/ -v -m `"not integration`""
Write-Host "  python scripts/run_eval.py              # offline regression (CI)"
Write-Host "  python scripts/run_dashboard.py         # Streamlit 控制台"
Write-Host ""
Write-Host "Live eval (optional): set DEEPSEEK_API_KEY in .env, then:"
Write-Host "  python scripts/run_eval.py --live --judge"
Write-Host ""
Write-Host "Docs: README.md | docs/ARCHITECTURE.md | docs/EVAL.md"
