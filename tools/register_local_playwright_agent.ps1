param(
    [string]$InstallDir = "",
    [string]$ProtocolName = "testhub-agent",
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$InstallDir = (Resolve-Path -LiteralPath $InstallDir).Path
$startScript = Join-Path $InstallDir "start_local_playwright_agent.ps1"
$protocolScript = Join-Path $InstallDir "testhub_agent_protocol.ps1"

function Get-QuotedPowerShellValue {
    param([string]$Value)
    return '"' + $Value.Replace('"', '\"') + '"'
}

if (!(Test-Path -LiteralPath $startScript)) {
    throw "Start script not found: $startScript"
}
if (!(Test-Path -LiteralPath $protocolScript)) {
    throw "Protocol script not found: $protocolScript"
}

$protocolRoot = "HKCU:\Software\Classes\$ProtocolName"
$protocolCommandKey = Join-Path $protocolRoot "shell\open\command"
New-Item -Path $protocolCommandKey -Force | Out-Null
Set-Item -Path $protocolRoot -Value "URL:TestHub Local Agent Protocol"
New-ItemProperty -Path $protocolRoot -Name "URL Protocol" -Value "" -PropertyType String -Force | Out-Null

$protocolCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$protocolScript`" `"%1`""
Set-Item -Path $protocolCommandKey -Value $protocolCommand

$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
New-Item -Path $runKey -Force | Out-Null
$startupCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScript`""
if (![string]::IsNullOrWhiteSpace($Python)) {
    $startupCommand += " -Python $(Get-QuotedPowerShellValue $Python)"
}
Set-ItemProperty -Path $runKey -Name "TestHubLocalAgent" -Value $startupCommand

Write-Host "Registered $ProtocolName protocol and TestHubLocalAgent startup entry."
