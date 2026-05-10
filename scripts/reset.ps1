#requires -Version 5
# Lon · DB 초기화 (사용자/스키마 + 마이그레이션)
# 주의: --reset 옵션은 모든 테이블/컬렉션을 DROP합니다.
param(
  [string]$RootPassword = "",
  [string]$AppPassword = "CHANGE_ME_LON_2026",
  [switch]$Reset = $false
)
$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot

# 1) MariaDB: 사용자/DB 생성 (root 패스워드 필요)
Write-Host "[1/3] MariaDB 사용자/DB 생성" -ForegroundColor Cyan
$createSql = @"
CREATE DATABASE IF NOT EXISTS lon
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'lon_app'@'localhost' IDENTIFIED BY '$AppPassword';
GRANT ALL PRIVILEGES ON lon.* TO 'lon_app'@'localhost';
FLUSH PRIVILEGES;
"@
if ($RootPassword -eq "") {
  Write-Host "  root 패스워드 없이 mariadb -u root 시도..." -ForegroundColor Yellow
  $createSql | mariadb -u root
} else {
  $createSql | mariadb -u root "-p$RootPassword"
}

# 2) MariaDB 마이그레이션
Write-Host "`n[2/3] MariaDB 마이그레이션 적용" -ForegroundColor Cyan
Push-Location $ROOT
. "$ROOT\apps\api\.venv\Scripts\Activate.ps1"
$args = @()
if ($Reset) { $args += "--reset" }
python "$ROOT\db\init_mariadb.py" @args
deactivate
Pop-Location

# 3) MongoDB
Write-Host "`n[3/3] MongoDB 초기화" -ForegroundColor Cyan
Push-Location $ROOT
. "$ROOT\apps\api\.venv\Scripts\Activate.ps1"
$args = @()
if ($Reset) { $args += "--reset" }
python "$ROOT\db\init_mongo.py" @args
deactivate
Pop-Location

Write-Host "`nDONE — 다음: .\scripts\seed.ps1 (시드 데이터)" -ForegroundColor Green
