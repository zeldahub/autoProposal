#requires -Version 5
# Lon · 의존성 설치 (Python venv + pnpm)
$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot

# 1) BE Python venv
Write-Host "[1/2] Python venv + pip install" -ForegroundColor Cyan
Push-Location "$ROOT\apps\api"
if (-not (Test-Path ".venv")) {
  python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
if (-not (Test-Path ".env")) { Copy-Item .env.example .env }
deactivate
Pop-Location

# 2) FE pnpm install
Write-Host "`n[2/2] FE pnpm install" -ForegroundColor Cyan
Push-Location "$ROOT\apps\web"
if (Get-Command pnpm -ErrorAction SilentlyContinue) {
  pnpm install
} elseif (Get-Command npm -ErrorAction SilentlyContinue) {
  Write-Host "pnpm 없음 → npm install 사용" -ForegroundColor Yellow
  npm install
} else {
  Write-Host "Node 패키지 매니저를 찾을 수 없습니다" -ForegroundColor Red
  exit 1
}
if (-not (Test-Path ".env.local")) { Copy-Item .env.example .env.local }
Pop-Location

Write-Host "`nDONE — 다음: .\scripts\reset.ps1 (DB 초기화)" -ForegroundColor Green
