# switch-db.ps1 - Switch between compact (C: SSD) and archive (E: HDD) PostgreSQL databases
#
# Usage:
#   .\tools\switch-db.ps1              # Switch to compact (default)
#   .\tools\switch-db.ps1 compact      # Switch to compact (C: SSD, ~150MB)
#   .\tools\switch-db.ps1 archive      # Switch to archive (E: HDD, 44GB)
#   .\tools\switch-db.ps1 status       # Show which DB is running
#
# Both use port 5432, same DATABASE_URL - no code changes needed.

param(
    [string]$target = "compact"
)

$pgctl = "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe"
$compactData = "C:\PostgreSQL\data"
$archiveData = "E:\PostgreSQL\data"

function Get-RunningDB {
    # Check compact
    $compactRunning = & $pgctl status -D $compactData 2>&1
    if ($LASTEXITCODE -eq 0) { return "compact" }

    # Check archive
    $archiveRunning = & $pgctl status -D $archiveData 2>&1
    if ($LASTEXITCODE -eq 0) { return "archive" }

    return "none"
}

function Stop-DB($dataDir, $label) {
    $status = & $pgctl status -D $dataDir 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Stopping $label DB ($dataDir)..." -ForegroundColor Yellow
        & $pgctl stop -D $dataDir -m fast 2>&1 | Out-Null
        Start-Sleep -Seconds 2
        Write-Host "  Stopped." -ForegroundColor Gray
    }
}

function Start-DB($dataDir, $logFile, $label) {
    Write-Host "Starting $label DB ($dataDir)..." -ForegroundColor Green
    & $pgctl start -D $dataDir -l $logFile 2>&1 | Out-Null
    Start-Sleep -Seconds 2

    $status = & $pgctl status -D $dataDir 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Running on port 5432." -ForegroundColor Green
    } else {
        Write-Host "  FAILED to start! Check $logFile" -ForegroundColor Red
        exit 1
    }
}

# Main logic
$running = Get-RunningDB

switch ($target) {
    "status" {
        Write-Host ""
        Write-Host "  PostgreSQL Status" -ForegroundColor Cyan
        Write-Host "  =================" -ForegroundColor Cyan
        switch ($running) {
            "compact" {
                Write-Host "  Active: COMPACT (C: SSD, ~150MB light)" -ForegroundColor Green
                Write-Host "  Path:   $compactData" -ForegroundColor Gray
            }
            "archive" {
                Write-Host "  Active: ARCHIVE (E: HDD, 44GB full)" -ForegroundColor Yellow
                Write-Host "  Path:   $archiveData" -ForegroundColor Gray
            }
            "none" {
                Write-Host "  Active: NONE (no PostgreSQL running)" -ForegroundColor Red
            }
        }
        Write-Host "  Port:   5432" -ForegroundColor Gray
        Write-Host ""
    }

    "compact" {
        if ($running -eq "compact") {
            Write-Host "Already running COMPACT DB." -ForegroundColor Green
            return
        }
        if (!(Test-Path $compactData)) {
            Write-Host "ERROR: Compact data dir not found: $compactData" -ForegroundColor Red
            Write-Host "Run initdb first. See CLAUDE.md for setup instructions." -ForegroundColor Yellow
            exit 1
        }
        Stop-DB $archiveData "ARCHIVE"
        Start-DB $compactData "$compactData\pg.log" "COMPACT"
        Write-Host ""
        Write-Host "  Switched to COMPACT DB (C: SSD, ~150MB light)" -ForegroundColor Cyan
        Write-Host "  Same port 5432, same DATABASE_URL - no code changes." -ForegroundColor Gray
        Write-Host ""
    }

    "archive" {
        if ($running -eq "archive") {
            Write-Host "Already running ARCHIVE DB." -ForegroundColor Yellow
            return
        }
        if (!(Test-Path $archiveData)) {
            Write-Host "ERROR: Archive data dir not found: $archiveData" -ForegroundColor Red
            Write-Host "Is the E: drive connected?" -ForegroundColor Yellow
            exit 1
        }
        Stop-DB $compactData "COMPACT"
        Start-DB $archiveData "$archiveData\pg.log" "ARCHIVE"
        Write-Host ""
        Write-Host "  Switched to ARCHIVE DB (E: HDD, 44GB full)" -ForegroundColor Cyan
        Write-Host "  WARNING: Large queries will be slow on HDD!" -ForegroundColor Yellow
        Write-Host ""
    }

    default {
        Write-Host "Usage: .\tools\switch-db.ps1 [compact|archive|status]" -ForegroundColor Yellow
    }
}
