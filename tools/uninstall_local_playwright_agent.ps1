param(
    [switch]$RemoveFiles,
    [string]$ProtocolName = "testhub-agent",
    [int]$Port = 18765
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$stopScript = Join-Path $scriptDir "stop_local_playwright_agent.ps1"

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:$Port/shutdown" -Method Post -TimeoutSec 3 | Out-Null
    Start-Sleep -Seconds 1
} catch {
    if (Test-Path -LiteralPath $stopScript) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $stopScript -Port $Port
    }
}

$protocolRoot = "HKCU:\Software\Classes\$ProtocolName"
if (Test-Path -LiteralPath $protocolRoot) {
    Remove-Item -LiteralPath $protocolRoot -Recurse -Force
}

$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
if (Test-Path -LiteralPath $runKey) {
    Remove-ItemProperty -Path $runKey -Name "TestHubLocalAgent" -ErrorAction SilentlyContinue
}

if ($RemoveFiles) {
    $removeTarget = $scriptDir
    $parentDir = Split-Path -Parent $removeTarget
    $isSourceToolsDir = (
        (Split-Path -Leaf $removeTarget) -ieq "tools" -and
        (Test-Path -LiteralPath (Join-Path $parentDir ".git"))
    )
    if ($isSourceToolsDir) {
        Write-Warning "Refusing to remove source repository tools directory: $removeTarget"
        Write-Host "Protocol and startup entries were removed. Source files were kept."
        exit 0
    }

    $encodedTarget = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($removeTarget))
    $cleanupCommand = @"
`$target = [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('$encodedTarget'))
Start-Sleep -Seconds 2
if (Test-Path -LiteralPath `$target) {
    Remove-Item -LiteralPath `$target -Recurse -Force -ErrorAction SilentlyContinue
}
"@
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-Command",
        $cleanupCommand
    ) -WindowStyle Hidden | Out-Null
}

Write-Host "TestHub Local Agent uninstalled."
