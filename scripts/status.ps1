#requires -Version 5
<#
  Lon — 서비스 상태 확인 (헬스체크 + 포트 사용 + 최근 git 상태)
#>
$ErrorActionPreference = "Continue"
$ROOT = Split-Path -Parent $PSScriptRoot

function Test-Url($url) {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
        return $r.StatusCode
    } catch { return 0 }
}

function Show-Port($port, $label) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Sort-Object OwningProcess -Unique
    if (-not $conns) {
        Write-Host ("  {0}:{1,5}  free" -f $label, $port) -ForegroundColor DarkGray
        return
    }
    foreach ($c in $conns) {
        try {
            $p = Get-Process -Id $c.OwningProcess -ErrorAction Stop
            Write-Host ("  {0}:{1,5}  PID={2}  {3}" -f $label, $port, $p.Id, $p.ProcessName) -ForegroundColor Cyan
        } catch {
            Write-Host ("  {0}:{1,5}  PID={2}  ?" -f $label, $port, $c.OwningProcess) -ForegroundColor DarkYellow
        }
    }
}

Write-Host "=== Lon 상태 ===" -ForegroundColor Green
Write-Host "[ports]"
Show-Port 8089 "API "
Show-Port 5173 "Web "
Show-Port 3306 "DB  "
Show-Port 27017 "Mongo"

Write-Host "`n[health]"
$apiCode = Test-Url "http://127.0.0.1:8089/healthz"
$webCode = Test-Url "http://127.0.0.1:5173/"
Write-Host ("  API healthz : {0}" -f $apiCode)
Write-Host ("  Web /       : {0}" -f $webCode)

Set-Location $ROOT
if (Test-Path (Join-Path $ROOT ".git")) {
    Write-Host "`n[git]"
    Write-Host ("  branch = {0}" -f (git rev-parse --abbrev-ref HEAD 2>$null))
    Write-Host ("  origin = {0}" -f (git config --get remote.origin.url))
    $dirty = git status --porcelain
    if ($dirty) {
        Write-Host ("  uncommitted changes : {0} files" -f (($dirty -split "`n") | Measure-Object).Count) -ForegroundColor Yellow
    } else {
        Write-Host "  uncommitted changes : 0" -ForegroundColor Green
    }
    $last = git log -1 --pretty=format:"%h %s (%ar)" 2>$null
    if ($last) { Write-Host ("  last commit : {0}" -f $last) }
}
