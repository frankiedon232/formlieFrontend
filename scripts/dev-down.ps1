# Stops what scripts\dev-up.ps1 started: the Celery worker, Beat, Flower, the API if it was started with -WithApi,
# and the background process that keeps Ubuntu (WSL) running. Data is never touched. An API you started yourself
# in your own terminal is left alone (stop it there with Ctrl+C).
#
#   powershell -ExecutionPolicy Bypass -File scripts\dev-down.ps1

$root = Split-Path -Parent $PSScriptRoot
$stopped = 0
Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and (
        ($_.CommandLine -match "celery_app (worker|beat|flower)") -or
        ($_.CommandLine -match [regex]::Escape($root) -and $_.CommandLine -match "-m app\.run") -or
        ($_.Name -eq "wsl.exe" -and $_.CommandLine -match "formalie-keepalive"))
} | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    $stopped++
}
Write-Host "Stopped $stopped process(es)."
