#requires -Version 5
# Lon · 환경 점검 (DB/Node/Python/Mongo)
$ErrorActionPreference = "Continue"
$ok = $true

function Try-Cmd($name, $cmd) {
  try {
    $v = & $cmd 2>&1 | Select-Object -First 1
    Write-Host ("[OK]  {0,-10} {1}" -f $name, $v)
  } catch {
    Write-Host ("[--]  {0,-10} not found" -f $name) -ForegroundColor Yellow
    $script:ok = $false
  }
}

Write-Host "=== Lon 환경 점검 ===" -ForegroundColor Cyan
Try-Cmd "node"     { node -v }
Try-Cmd "pnpm"     { pnpm -v }
Try-Cmd "python"   { python --version }
Try-Cmd "mariadb"  { mariadb --version }
Try-Cmd "mongosh"  { mongosh --version }
Try-Cmd "java"     { java -version }
Try-Cmd "git"      { git --version }

# 포트 점유 확인
Write-Host "`n=== 포트 점유 ===" -ForegroundColor Cyan
foreach ($p in 8080, 5173, 3306, 27017) {
  $busy = (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) -ne $null
  $tag  = if ($busy) { "USED" } else { "FREE" }
  $color = if ($busy) { "Yellow" } else { "Green" }
  Write-Host ("  {0,-6} {1}" -f $p, $tag) -ForegroundColor $color
}

if ($ok) { Write-Host "`n환경 OK" -ForegroundColor Green } else { Write-Host "`n일부 누락" -ForegroundColor Yellow }
