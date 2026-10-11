# Stops what scripts\dev-up.ps1 started: the API, Celery worker, Beat and Flower windows, and the background
# process that keeps Ubuntu (WSL) running. Data is not touched. Ubuntu itself stops a little later on its own.
#
#   powershell -ExecutionPolicy Bypass -File scripts\dev-down.ps1

$root = Split-Path -Parent $PSScriptRoot
$stopped = 0
Get-CimInstance Win32_Process | Where-Object {
    ($_.CommandLine -match "formalie: " -and $_.Name -eq "powershell.exe") -or
    ($_.CommandLine -match [regex]::Escape($root) -and $_.CommandLine -match "app\.run|celery") -or
    ($_.Name -eq "wsl.exe" -and $_.CommandLine -match "formalie-keepalive")
} | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    $stopped++
}
Write-Host "Stopped $stopped process(es)."
