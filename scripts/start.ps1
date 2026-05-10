#requires -Version 5
<#
  Lon — 서비스 기동 (API uvicorn 8089 + Web Vite 5173)
  사용:
    .\scripts\start.ps1            # 별도 창으로 BE/FE 기동
    .\scripts\start.ps1 -Background # 현재 창에서 백그라운드 작업으로 기동
#>
param(
    [switch]$Background
)
$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot
$API_DIR = Join-Path $ROOT "apps\api"
$WEB_DIR = Join-Path $ROOT "apps\web"

# 0) 이미 기동 중인 프로세스 정리
function Stop-Port($port) {
    Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
Write-Host "[0/3] 기존 포트 정리 (8089/5173)" -ForegroundColor DarkGray
Stop-Port 8089
Stop-Port 5173
Start-Sleep -Milliseconds 500

# 1) MariaDB / Mongo 살아있는지 확인 (정보용 — 죽어있어도 계속 진행)
function Test-Tcp($h, $p) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.ReceiveTimeout = 800; $c.SendTimeout = 800
        $iar = $c.BeginConnect($h, $p, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(800, $false)
        if ($ok) { $c.EndConnect($iar); $c.Close(); return $true }
        $c.Close(); return $false
    } catch { return $false }
}
$dbOk = Test-Tcp "127.0.0.1" 3306
$moOk = Test-Tcp "127.0.0.1" 27017
Write-Host "  MariaDB:3306  $([bool]$dbOk -as [string])"
Write-Host "  MongoDB:27017 $([bool]$moOk -as [string])"
if (-not $dbOk -or -not $moOk) {
    Write-Host "  WARN: DB 가 응답하지 않으면 API 가 정상 동작하지 않을 수 있습니다." -ForegroundColor Yellow
}

if ($Background) {
    Write-Host "[1/3] BE (uvicorn :8089) 백그라운드" -ForegroundColor Cyan
    $api = Start-Process -FilePath (Join-Path $API_DIR ".venv\Scripts\python.exe") `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8089", "--log-level", "warning") `
        -WorkingDirectory $API_DIR -PassThru -WindowStyle Hidden

    Start-Sleep -Seconds 3
    Write-Host "[2/3] FE (vite :5173) 백그라운드" -ForegroundColor Cyan
    $web = Start-Process -FilePath "npm" `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1") `
        -WorkingDirectory $WEB_DIR -PassThru -WindowStyle Hidden

    Set-Content -Encoding utf8 -Path (Join-Path $ROOT ".lon-pids") `
        -Value ("api={0}`nweb={1}" -f $api.Id, $web.Id)
}
else {
    Write-Host "[1/3] BE (uvicorn :8089) — 새 창" -ForegroundColor Cyan
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$API_DIR'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8089"
    ) | Out-Null

    Start-Sleep -Seconds 2
    Write-Host "[2/3] FE (vite :5173) — 새 창" -ForegroundColor Cyan
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$WEB_DIR'; npm run dev -- --host 127.0.0.1"
    ) | Out-Null
}

# 3) 헬스체크
Write-Host "[3/3] 헬스체크 대기..." -ForegroundColor Cyan
$apiOk = $false; $webOk = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    if (-not $apiOk) {
        try { $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8089/healthz" -TimeoutSec 1; if ($r.StatusCode -eq 200) { $apiOk = $true } } catch {}
    }
    if (-not $webOk) {
        try { $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5173/" -TimeoutSec 1; if ($r.StatusCode -eq 200) { $webOk = $true } } catch {}
    }
    if ($apiOk -and $webOk) { break }
}

Write-Host ""
Write-Host "=== 기동 결과 ===" -ForegroundColor Green
Write-Host ("  API : {0}  http://127.0.0.1:8089" -f ($apiOk ? 'OK' : 'NG'))
Write-Host ("  Web : {0}  http://127.0.0.1:5173" -f ($webOk ? 'OK' : 'NG'))
Write-Host ""
Write-Host "  접속: http://localhost:5173"
Write-Host "  API  Swagger : http://localhost:8089/docs"
Write-Host "  Healthz      : http://localhost:8089/healthz"
