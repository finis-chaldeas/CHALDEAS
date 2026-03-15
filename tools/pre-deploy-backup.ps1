# Pre-deploy database backup script
# Run BEFORE each production deployment
#
# Usage:
#   .\tools\pre-deploy-backup.ps1
#
# Output:
#   data\compact_export\backup_YYYYMMDD\chaldeas_full_YYYYMMDD.dump

$ErrorActionPreference = "Stop"

$date = Get-Date -Format "yyyyMMdd"
$backupDir = "data\compact_export\backup_$date"
$backupFile = "$backupDir\chaldeas_full_$date.dump"
$pgDump = "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"

# Check pg_dump exists
if (-not (Test-Path $pgDump)) {
    Write-Error "pg_dump not found at $pgDump"
    exit 1
}

# Create backup directory
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}

# Check if backup already exists
if (Test-Path $backupFile) {
    Write-Warning "Backup already exists: $backupFile"
    $confirm = Read-Host "Overwrite? (y/N)"
    if ($confirm -ne "y") {
        Write-Host "Backup skipped."
        exit 0
    }
}

Write-Host "Creating backup: $backupFile ..." -ForegroundColor Cyan

$env:PGPASSWORD = "chaldeas_dev"
& $pgDump -h 127.0.0.1 -U chaldeas -Fc chaldeas -f $backupFile

if ($LASTEXITCODE -ne 0) {
    Write-Error "pg_dump failed with exit code $LASTEXITCODE"
    exit 1
}

$size = (Get-Item $backupFile).Length / 1MB
Write-Host "Backup complete: $backupFile ($([math]::Round($size, 1)) MB)" -ForegroundColor Green
Write-Host ""
Write-Host "To restore: pg_restore -h 127.0.0.1 -U chaldeas -d chaldeas --clean $backupFile"
