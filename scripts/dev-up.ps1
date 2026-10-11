# Starts the Formalie backend for development after a restart. One command, from the project folder:
#
#   powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1          # services + API + workers + Flower
#   powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1 -NoApp   # services only
#   powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1 -NoApi   # all but the API (you start it yourself)
#
# 1. Wakes Ubuntu (WSL) and keeps it running in the background, so Redis, RabbitMQ, PgBouncer and Mailpit
#    (systemd services, they start with Ubuntu) stay up even with no Ubuntu window open.
# 2. Checks every service answers (PostgreSQL runs as a Windows service and starts with Windows).
# 3. Opens one window each for the API (https://formalie.dev:5004), the Celery worker, Celery Beat and Flower.
# Stop everything with scripts\dev-down.ps1.

param([switch]$NoApp, [switch]$NoApi)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$distro = "Ubuntu-24.04"

Write-Host "== Ubuntu (WSL)" -ForegroundColor Cyan
$keepalive = Get-CimInstance Win32_Process -Filter "Name = 'wsl.exe'" |
    Where-Object { $_.CommandLine -match "formalie-keepalive" }
if (-not $keepalive) {
    # A hidden, idle process inside Ubuntu: WSL stays up (and its services with it) until dev-down.
    Start-Process -WindowStyle Hidden -FilePath "wsl.exe" -ArgumentList "-d $distro -- bash -c `"exec -a formalie-keepalive sleep infinity`""
    Write-Host "   started and kept running in the background"
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

if ($NoApp) { Write-Host "Services are up (-NoApp: API and workers not started)."; exit 0 }

Write-Host "== API, workers, dashboards" -ForegroundColor Cyan
$python = Join-Path $root "fmly\Scripts\python.exe"
$celery = Join-Path $root "fmly\Scripts\celery.exe"
$windows = [ordered]@{
    "Formalie API"    = "& '$python' -m app.run"
    "Celery worker"   = "& '$celery' -A app.workers.celery_app worker -Q scheduled,logs --pool=solo -E -n worker1@%h -l info"
    "Celery beat"     = "& '$celery' -A app.workers.celery_app beat -s logs/celerybeat-schedule -l info"
    "Flower"          = "& '$celery' -A app.workers.celery_app flower --address=127.0.0.1 --port=5555"
}
if ($NoApi) { $windows.Remove("Formalie API") }
foreach ($title in $windows.Keys) {
    $command = "`$host.UI.RawUI.WindowTitle = 'formalie: $title'; Set-Location '$root'; $($windows[$title])"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $command | Out-Null
    Write-Host "   $title"
}

Write-Host ""
Write-Host "Ready:" -ForegroundColor Green
Write-Host "   API        https://formalie.dev:5004/docs"
Write-Host "   Flower     http://127.0.0.1:5555"
Write-Host "   RabbitMQ   http://127.0.0.1:15672"
Write-Host "   Mailpit    http://127.0.0.1:8025"
