#requires -Version 5
<#
  Lon — 서비스 종료 (8089 / 5173 점유 프로세스 모두 정리)
  사용:
    .\scripts\stop.ps1
#>
$ErrorActionPreference = "Continue"
$ROOT = Split-Path -Parent $PSScriptRoot

function Stop-Port($port, $label) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if (-not $conns) {
        Write-Host ("  [{0}:{1}] 점유 프로세스 없음" -f $label, $port) -ForegroundColor DarkGray
        return
    }
    $pids = ($conns | Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($pid in $pids) {
        try {
            $p = Get-Process -Id $pid -ErrorAction Stop
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Write-Host ("  [{0}:{1}] killed PID={2} ({3})" -f $label, $port, $pid, $p.ProcessName) -ForegroundColor Yellow
        } catch {
            Write-Host ("  [{0}:{1}] PID={2} 종료 실패: {3}" -f $label, $port, $pid, $_.Exception.Message) -ForegroundColor Red
        }
    }
}

Write-Host "[1/2] 포트별 프로세스 종료" -ForegroundColor Cyan
Stop-Port 8089 "API"
Stop-Port 5173 "Web"

# .lon-pids 가 있으면 부가 정리
$pidFile = Join-Path $ROOT ".lon-pids"
if (Test-Path $pidFile) {
    Write-Host "[2/2] .lon-pids 정리" -ForegroundColor Cyan
    Get-Content $pidFile | ForEach-Object {
        if ($_ -match "^(api|web)=(\d+)$") {
            $label = $Matches[1]; $pid = [int]$Matches[2]
            try {
                Stop-Process -Id $pid -Force -ErrorAction Stop
                Write-Host ("  {0}: PID={1} stopped" -f $label, $pid) -ForegroundColor Yellow
            } catch {
                # 이미 종료됐으면 무시
            }
        }
    }
    Remove-Item -Force $pidFile -ErrorAction SilentlyContinue
}
else {
    Write-Host "[2/2] .lon-pids 없음 (생략)" -ForegroundColor DarkGray
}

Write-Host "`n  종료 완료. 포트 8089/5173 해제됨." -ForegroundColor Green
