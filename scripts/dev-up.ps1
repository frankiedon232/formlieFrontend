# Starts the Formalie backend for development, quietly in the background: no windows open.
#
#   powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1           # services, API, Celery worker, Beat, Flower
#   powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1 -NoApi    # the same without the API
#   powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1 -NoApp    # services only
#   powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1 -Restart  # stop the API and workers first, then start them
#                                                                       # again (after new code): the one command to use
#
# Watch the logs live (in the terminal you run it in):  powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1
# Stop everything:                                      powershell -ExecutionPolicy Bypass -File scripts\dev-down.ps1
#
# 1. Wakes Ubuntu (WSL) and keeps it running in the background, so Redis, RabbitMQ, PgBouncer and Mailpit (they
#    start with Ubuntu) stay up with no Ubuntu window open. PostgreSQL starts with Windows.
# 2. Checks every service answers.
# 3. Starts the API (https://formalie.dev:5004), the Celery worker, Beat and Flower hidden; their output goes to
#    logs\dev\*.log. Safe to run again: anything already running is left as it is.
# Before 3, the database is brought up to date (`alembic upgrade head`) and the sample workspaces are seeded
# (scripts/seed_dev.py: existing workspaces and data are kept), so new tables never need a separate step
# (owner, 2026-10-12). Skip it with -NoMigrate.

param([switch]$NoApp, [switch]$NoApi, [switch]$Restart, [switch]$NoMigrate)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$distro = "Ubuntu-24.04"
$devLogs = Join-Path $root "logs\dev"

function Test-Running([string]$pattern) {
    return [bool](Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match $pattern })
}

Write-Host "== Ubuntu (WSL)" -ForegroundColor Cyan
if (-not (Test-Running "formalie-keepalive")) {
    # A hidden, idle process inside Ubuntu: WSL stays up (and its services with it) until dev-down.
    Start-Process -WindowStyle Hidden -FilePath "wsl.exe" -ArgumentList "-d $distro -- bash -c `"exec -a formalie-keepalive sleep infinity`""
    Write-Host "   started, kept running in the background"
} else {
    Write-Host "   already running"
}

Write-Host "== Services" -ForegroundColor Cyan
$services = [ordered]@{ "PostgreSQL" = 5432; "Redis" = 6379; "RabbitMQ" = 5672; "RabbitMQ UI" = 15672; "PgBouncer" = 6432; "Mailpit" = 8025 }
$deadline = (Get-Date).AddSeconds(60)
$missing = @()
foreach ($name in $services.Keys) {
    $port = $services[$name]
    $up = $false
    while (-not $up -and (Get-Date) -lt $deadline) {
        $client = New-Object System.Net.Sockets.TcpClient
        try { $client.Connect("127.0.0.1", $port); $up = $true } catch { Start-Sleep -Milliseconds 500 } finally { $client.Close() }
    }
    if ($up) { Write-Host ("   {0,-12} {1,5}  up" -f $name, $port) -ForegroundColor Green }
    else { Write-Host ("   {0,-12} {1,5}  NOT answering" -f $name, $port) -ForegroundColor Red; $missing += $name }
}
if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "Some services are down. In an Ubuntu window:  sudo systemctl restart redis-server rabbitmq-server pgbouncer mailpit" -ForegroundColor Yellow
    Write-Host "PostgreSQL (Windows, as administrator):        Restart-Service postgresql-x64-18" -ForegroundColor Yellow
    exit 1
}
if ($NoApp) { Write-Host "Services are up."; exit 0 }

$python = Join-Path $root "fmly\Scripts\python.exe"
if ($Restart) {
    Write-Host "== Restart: stopping the API and the Celery processes" -ForegroundColor Cyan
    $stopped = 0
    Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and (($_.CommandLine -match "celery_app (worker|beat|flower)") -or
            ($_.CommandLine -match [regex]::Escape($root) -and $_.CommandLine -match "-m app\.run"))
    } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $stopped++ }
    Write-Host "   stopped $stopped process(es)"
    Start-Sleep -Seconds 2
}

if (-not $NoMigrate) {
    Write-Host "== Database: migrations and sample workspaces" -ForegroundColor Cyan
    Push-Location $root
    try {
        & $python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { Write-Host "   migrations failed: see above (nothing was started)" -ForegroundColor Red; exit 1 }
        & $python scripts\seed_dev.py
        if ($LASTEXITCODE -ne 0) { Write-Host "   seeding failed: see above (the database is up to date; starting anyway)" -ForegroundColor Yellow }
    } finally { Pop-Location }
}

Write-Host "== Background processes (hidden; output in logs\dev\)" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $devLogs | Out-Null
$env:PYTHONUNBUFFERED = "1"  # each log line is written at once, so dev-logs shows it live
$python = Join-Path $root "fmly\Scripts\python.exe"
$celery = Join-Path $root "fmly\Scripts\celery.exe"

$jobs = [ordered]@{}
if (-not $NoApi) {
    $portBusy = Get-NetTCPConnection -LocalPort 5004 -State Listen -ErrorAction SilentlyContinue
    if ($portBusy -and -not (Test-Running "-m app\.run")) {
        Write-Host "   api     port 5004 is taken by another process (an API started by hand?): left as it is" -ForegroundColor Yellow
    } else {
        $jobs["api"] = @{ exe = $python; args = "-m app.run"; match = "-m app\.run" }
    }
}
$jobs["worker"] = @{ exe = $celery; args = "-A app.workers.celery_app worker -Q scheduled,logs,notifications,exports,destinations,webhooks --pool=solo -E -n worker1@%h -l info"; match = "celery_app worker" }
$jobs["beat"] = @{ exe = $celery; args = "-A app.workers.celery_app beat -s logs/celerybeat-schedule -l info"; match = "celery_app beat" }
$jobs["flower"] = @{ exe = $celery; args = "-A app.workers.celery_app flower --address=127.0.0.1 --port=5555"; match = "celery_app flower" }

foreach ($name in $jobs.Keys) {
    $job = $jobs[$name]
    if (Test-Running $job.match) { Write-Host ("   {0,-7} already running" -f $name); continue }
    Start-Process -WindowStyle Hidden -WorkingDirectory $root -FilePath $job.exe -ArgumentList $job.args `
        -RedirectStandardOutput (Join-Path $devLogs "$name.log") -RedirectStandardError (Join-Path $devLogs "$name.err.log") | Out-Null
    Write-Host ("   {0,-7} started" -f $name)
}

Write-Host ""
Write-Host "Ready." -ForegroundColor Green
Write-Host "   API        https://formalie.dev:5004/docs"
Write-Host "   Logs live  powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1"
Write-Host "   Flower http://127.0.0.1:5555  |  RabbitMQ http://127.0.0.1:15672  |  Mailpit http://127.0.0.1:8025"
