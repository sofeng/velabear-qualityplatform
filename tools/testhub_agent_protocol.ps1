param(
    [string]$Url = "testhub-agent://start"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$startScript = Join-Path $scriptDir "start_local_playwright_agent.ps1"
$stopScript = Join-Path $scriptDir "stop_local_playwright_agent.ps1"
$uninstallScript = Join-Path $scriptDir "uninstall_local_playwright_agent.ps1"
$installScript = Join-Path $scriptDir "install_local_playwright_agent.ps1"
$configPath = Join-Path $scriptDir "agent_config.json"

function Get-AgentPython {
    if (Test-Path -LiteralPath $configPath) {
        try {
            $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if (
                $config.PSObject.Properties.Name -contains "python_path" -and
                ![string]::IsNullOrWhiteSpace([string]$config.python_path) -and
                (Test-Path -LiteralPath ([string]$config.python_path))
            ) {
                return [string]$config.python_path
            }
        } catch {
        }
    }
    return "python"
}

function Get-AgentAction {
    param([string]$RawUrl)

    if ([string]::IsNullOrWhiteSpace($RawUrl)) {
        return "start"
    }

    try {
        $uri = [Uri]$RawUrl
        if (![string]::IsNullOrWhiteSpace($uri.Host)) {
            return $uri.Host.ToLowerInvariant()
        }
        $trimmed = $uri.AbsolutePath.Trim("/")
        if (![string]::IsNullOrWhiteSpace($trimmed)) {
            return $trimmed.ToLowerInvariant()
        }
    } catch {
        return $RawUrl.ToLowerInvariant().Replace("testhub-agent://", "").Trim("/")
    }

    return "start"
}

$action = Get-AgentAction $Url
$agentPython = Get-AgentPython

switch ($action) {
    "start" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $startScript -Python $agentPython
    }
    "restart" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $stopScript
        & powershell -NoProfile -ExecutionPolicy Bypass -File $startScript -Python $agentPython
    }
    "update" {
        if (Test-Path -LiteralPath $installScript) {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $installScript -InstallDir $scriptDir -Python $agentPython
        } else {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $startScript -Python $agentPython
        }
    }
    "stop" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $stopScript
    }
    "uninstall" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $uninstallScript -RemoveFiles
    }
    default {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $startScript -Python $agentPython
    }
}
