#Requires -RunAsAdministrator
<#
.SYNOPSIS
    PostgreSQL 서비스 자동 복구 + 시작 유형 설정.
    컴퓨터가 갑자기 꺼져도 재부팅 시 PostgreSQL이 자동으로 복구됩니다.

.USAGE
    관리자 권한 PowerShell에서:
    .\tools\setup-pg-recovery.ps1
#>

$ServiceName = "postgresql-x64-18"

# 1. 서비스 존재 확인
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Error "Service '$ServiceName' not found!"
    exit 1
}

Write-Host "=== PostgreSQL Service Recovery Setup ===" -ForegroundColor Cyan

# 2. 시작 유형 = 자동 (Automatic)
Set-Service -Name $ServiceName -StartupType Automatic
Write-Host "[OK] Startup type: Automatic" -ForegroundColor Green

# 3. 실패 시 자동 재시작 (1차: 즉시, 2차: 30초 후, 3차: 60초 후)
# sc failure 명령 사용 (Set-Service로는 recovery 설정 불가)
sc.exe failure $ServiceName reset= 86400 actions= restart/0/restart/30000/restart/60000
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Recovery: restart on failure (0s / 30s / 60s)" -ForegroundColor Green
} else {
    Write-Error "Failed to set recovery options"
}

# 4. 현재 상태 확인
Write-Host ""
Write-Host "=== Current Status ===" -ForegroundColor Cyan
sc.exe qfailure $ServiceName
Write-Host ""
Get-Service -Name $ServiceName | Format-Table Name, Status, StartType -AutoSize

Write-Host ""
Write-Host "Done. PostgreSQL will auto-restart on crash or reboot." -ForegroundColor Green
