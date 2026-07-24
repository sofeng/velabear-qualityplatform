param(
    [int]$Port = 18765
)

$ErrorActionPreference = "Stop"

$processes = @(
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -like "*local_playwright_agent.py*" -and
            $_.CommandLine -like "*--serve*"
        }
)

if ($processes.Count -eq 0) {
    Write-Host "Local Playwright agent is not running."
    exit 0
}

foreach ($process in $processes) {
    Write-Host "Stopping Local Playwright agent process $($process.ProcessId)..."
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 1
$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    Write-Host "Port $Port is still listening. Check whether another process is using it."
    exit 1
}

Write-Host "Local Playwright agent stopped."
