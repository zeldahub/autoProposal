#requires -Version 5
<#
  Lon — 변경사항 자동 커밋 + GitHub(zeldahub/autoProposal) 푸시 + (옵션) PR 머지
  사용:
    .\scripts\deploy.ps1                       # 변경사항을 main 에 직접 푸시
    .\scripts\deploy.ps1 -Message "..."        # 커밋 메시지 지정
    .\scripts\deploy.ps1 -Branch feat/xyz      # 브랜치 만들고 PR 생성 후 자동 머지
    .\scripts\deploy.ps1 -Branch feat/xyz -NoMerge   # PR 만들고 머지는 수동

  요구사항:
    - gh (GitHub CLI) 인증 필요  (gh auth login → zeldahub)
    - origin = https://github.com/zeldahub/autoProposal.git
#>
param(
    [string]$Message = "",
    [string]$Branch = "main",
    [switch]$NoMerge,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

function Section($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Step($t)    { Write-Host "  > $t" -ForegroundColor DarkCyan }
function Ok($t)      { Write-Host "  OK $t"  -ForegroundColor Green }
function Warn($t)    { Write-Host "  ! $t"   -ForegroundColor Yellow }
function Fail($t)    { Write-Host "  FAIL $t" -ForegroundColor Red; exit 1 }

# 0) gh / git 사전 확인
Section "사전 확인"
try { gh --version | Out-Null } catch { Fail "GitHub CLI(gh) 미설치 또는 PATH 누락" }
try { git --version | Out-Null } catch { Fail "git 미설치" }

$ghStatus = gh auth status 2>&1 | Out-String
if ($ghStatus -notmatch "Logged in to github.com account zeldahub") {
    Fail "gh 가 zeldahub 로 로그인되어 있지 않습니다. 'gh auth login' 실행 필요"
}
Ok "gh = zeldahub"

# 1) git 저장소인지 확인
if (-not (Test-Path (Join-Path $ROOT ".git"))) {
    Fail ".git 디렉토리 없음 (먼저 git 초기화 필요)"
}
$origin = git config --get remote.origin.url
if (-not $origin) { Fail "remote.origin 미설정" }
Ok "origin = $origin"

# 2) 변경사항 확인
Section "변경사항 확인"
$dirty = git status --porcelain
if (-not $dirty) {
    Warn "변경사항 없음 — 푸시할 것이 없습니다."
    exit 0
}
git status -s
Ok ("changed lines: {0}" -f ($dirty -split "`n").Count)

# 3) 브랜치 결정
$current = (git rev-parse --abbrev-ref HEAD 2>$null)
if (-not $current -or $current -eq "HEAD") { $current = "" }
Step ("current branch = '{0}'  target = '{1}'" -f $current, $Branch)

if ($Branch -ne "main") {
    # 새 브랜치
    if ($current -ne $Branch) {
        try { git switch -c $Branch 2>$null } catch { git switch $Branch }
        Ok "switched to $Branch"
    }
}
else {
    if ($current -ne "main") {
        try { git switch main 2>$null } catch { git switch -c main }
        Ok "switched to main"
    }
}

# 4) 커밋 메시지
if (-not $Message) {
    $Message = "chore: auto-deploy $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}
Step "commit message: $Message"

# 5) DryRun
if ($DryRun) {
    Warn "DryRun — 실제 commit/push 생략"
    git diff --stat
    exit 0
}

# 6) commit
Section "커밋"
git add -A
$diffCached = git diff --cached --name-only
if (-not $diffCached) {
    Warn "스테이지된 변경 없음 — 종료"
    exit 0
}
$msgFile = Join-Path $env:TEMP ("lon-commit-{0}.txt" -f ([guid]::NewGuid()))
@"
$Message

Co-Authored-By: Lon AutoDeploy <noreply@anthropic.com>
"@ | Set-Content -Encoding utf8 -Path $msgFile

git commit -F $msgFile
Remove-Item -Force $msgFile -ErrorAction SilentlyContinue
Ok "committed"

# 7) push
Section "푸시"
$hasRemoteBranch = (git ls-remote --heads origin $Branch | Select-String $Branch) -ne $null
if ($hasRemoteBranch) {
    git push origin $Branch
}
else {
    git push -u origin $Branch
}
Ok "pushed origin/$Branch"

# 8) main 으로 직접 푸시면 끝
if ($Branch -eq "main") {
    Section "완료"
    $repo = $origin -replace '\.git$','' -replace 'https://github.com/',''
    Write-Host ("  GitHub: https://github.com/{0}/commits/main" -f $repo) -ForegroundColor Green
    exit 0
}

# 9) 다른 브랜치 → PR 생성 + (옵션) 자동 머지
Section "PR 생성"
$prTitle = ($Message -split "`n")[0]
$prBody  = "Automated deploy from local. Branch ``$Branch`` → ``main``."
$prUrl = gh pr create --title $prTitle --body $prBody --base main --head $Branch 2>&1
if ($LASTEXITCODE -ne 0) { Fail ("gh pr create 실패: " + $prUrl) }
Ok "PR: $prUrl"

if ($NoMerge) {
    Warn "-NoMerge 지정 — 자동 머지 생략 (수동으로 진행)"
    exit 0
}

Section "자동 머지"
# squash 머지 후 브랜치 삭제 (--auto 는 require 룰 없을 때만 동작 → 폴백 처리)
$mergeOut = gh pr merge --squash --delete-branch --admin 2>&1
if ($LASTEXITCODE -ne 0) {
    # --admin 권한 없으면 일반 squash 시도
    Warn "admin 머지 실패 — 일반 squash 재시도"
    $mergeOut = gh pr merge --squash --delete-branch 2>&1
    if ($LASTEXITCODE -ne 0) { Fail ("gh pr merge 실패: " + $mergeOut) }
}
Ok "merged & deleted branch"

# main 동기화
git switch main
git pull --ff-only origin main
Ok "local main 동기화 완료"
