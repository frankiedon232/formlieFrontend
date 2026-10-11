# Follows the background processes' logs live, in this one terminal (Ctrl+C to stop):
#
#   powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1                 # all: api, worker, beat, flower
#   powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 api             # one
#   powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 api worker      # some
#   powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 -Errors         # only lines with ERROR / CRITICAL / Traceback
#
# Each line starts with where it came from. It shows the last 20 lines of each first, then new lines as they come.
# The files are logs\dev\{name}.log (normal output) and {name}.err.log (Python warnings and crashes).

param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Names, [switch]$Errors)

$root = Split-Path -Parent $PSScriptRoot
$devLogs = Join-Path $root "logs\dev"
$all = @("api", "worker", "beat", "flower")
if (-not $Names -or $Names.Count -eq 0) { $Names = $all }
$colors = @{ "api" = "Cyan"; "worker" = "Green"; "beat" = "Magenta"; "flower" = "Yellow" }
$filter = "ERROR|CRITICAL|Traceback|Exception"

# Each file and how far it has been read
$files = @()
foreach ($name in $Names) {
    foreach ($suffix in @("", ".err")) {
        $path = Join-Path $devLogs "$name$suffix.log"
        $files += [pscustomobject]@{ Name = $name; Path = $path; Position = 0L }
    }
}

# The real size (Windows lists a stale size for a file another process is still writing)
function Get-Length([string]$path) {
    $stream = [System.IO.File]::Open($path, "Open", "Read", "ReadWrite")
    try { return $stream.Length } finally { $stream.Close() }
}

function Show-Line($file, [string]$line) {
    if (-not $line.Trim()) { return }
    if ($Errors -and $line -notmatch $filter) { return }
    $tag = "{0,-6}" -f $file.Name
    Write-Host "$tag " -ForegroundColor $colors[$file.Name] -NoNewline
    Write-Host $line
}

# The last 20 lines of each, then follow
foreach ($file in $files) {
    if (Test-Path $file.Path) {
        Get-Content -Path $file.Path -Tail 20 -Encoding UTF8 | ForEach-Object { Show-Line $file $_ }
        $file.Position = Get-Length $file.Path
    }
}
Write-Host ("-- following {0} (Ctrl+C to stop) --" -f ($Names -join ", ")) -ForegroundColor DarkGray

while ($true) {
    foreach ($file in $files) {
        if (-not (Test-Path $file.Path)) { continue }
        $length = Get-Length $file.Path
        if ($length -lt $file.Position) { $file.Position = 0 }  # the file was started again
        if ($length -gt $file.Position) {
            $stream = [System.IO.File]::Open($file.Path, "Open", "Read", "ReadWrite")
            try {
                $stream.Seek($file.Position, "Begin") | Out-Null
                $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::UTF8)
                while ($null -ne ($line = $reader.ReadLine())) { Show-Line $file $line }
                $file.Position = $stream.Position
            } finally { $stream.Close() }
        }
    }
    Start-Sleep -Milliseconds 400
}
