#requires -Version 5
# Lon · 시드 데이터 (V2__seed_categories.sql 적용)
param(
  [string]$Password = "CHANGE_ME_LON_2026"
)
$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot

Write-Host "표준 목차 시드 적용..." -ForegroundColor Cyan
Get-Content "$ROOT\db\mariadb\migration\V2__seed_categories.sql" -Raw | mariadb -u lon_app "-p$Password" lon

Write-Host "DONE" -ForegroundColor Green
