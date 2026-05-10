#requires -Version 5
# Lon · BE + FE 동시 실행 (각각 새 PowerShell 창)
$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot

Write-Host "[1/2] BE (FastAPI :8080)" -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "cd '$ROOT\apps\api'; . .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8080"
)

Start-Sleep -Seconds 2

Write-Host "[2/2] FE (Vite :5173)" -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "cd '$ROOT\apps\web'; pnpm dev"
)

Write-Host "`n  BE: http://localhost:8080/docs"
Write-Host "  FE: http://localhost:5173" -ForegroundColor Green
