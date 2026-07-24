param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 18765,
    [string]$Python = "python",
    [int]$WaitSeconds = 20,
    [switch]$SkipRegister
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$agentScript = Join-Path $scriptDir "local_playwright_agent.py"
$logsDir = Join-Path $repoRoot "logs"
$stdoutLog = Join-Path $logsDir "local_playwright_agent.out.log"
$stderrLog = Join-Path $logsDir "local_playwright_agent.err.log"
$healthUrl = "http://${HostName}:${Port}/health"
$registerScript = Join-Path $scriptDir "register_local_playwright_agent.ps1"
$configPath = Join-Path $scriptDir "agent_config.json"

function Resolve-AgentPython {
    param([string]$RequestedPython)
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
            Write-Warning "Failed to read Agent config: $($_.Exception.Message)"
        }
    }
    return $RequestedPython
}

function Test-AgentHealth {
    try {
        $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 3
        return $response.status -eq "ok" -and $response.service -eq "testhub-local-playwright-agent"
    } catch {
        return $false
    }
}

function Get-AgentProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -like "*local_playwright_agent.py*" -and
            $_.CommandLine -like "*--serve*"
        }
}

if (!(Test-Path -LiteralPath $agentScript)) {
    throw "Local Playwright agent script not found: $agentScript"
}

$Python = Resolve-AgentPython -RequestedPython $Python
Write-Host "Using Python for Local Agent: $Python"

if (!$SkipRegister -and (Test-Path -LiteralPath $registerScript)) {
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $registerScript -InstallDir $scriptDir -Python $Python
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Local Playwright agent protocol registration exited with code $LASTEXITCODE."
        }
    } catch {
        Write-Warning "Local Playwright agent protocol registration failed: $($_.Exception.Message)"
    }
}

if (!(Test-Path -LiteralPath $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

if (Test-AgentHealth) {
    Write-Host "Local Playwright agent is already running at $healthUrl"
    exit 0
}

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $agentProcessIds = @(Get-AgentProcesses | Select-Object -ExpandProperty ProcessId)
    $foreignListeners = @($listeners | Where-Object { $agentProcessIds -notcontains $_.OwningProcess })
    if ($foreignListeners.Count -gt 0) {
        $owners = ($foreignListeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
        throw "Port $Port is already occupied by non-agent process(es): $owners"
    }

    foreach ($processId in $agentProcessIds) {
        Write-Host "Stopping unhealthy Local Playwright agent process $processId..."
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
}

Write-Host "Starting Local Playwright agent at $healthUrl..."
$arguments = @(
    $agentScript,
    "--serve",
    "--host",
    $HostName,
    "--port",
    [string]$Port
)

Start-Process `
    -FilePath $Python `
    -ArgumentList $arguments `
    -WorkingDirectory $repoRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden | Out-Null

for ($i = 0; $i -lt $WaitSeconds; $i += 1) {
    Start-Sleep -Seconds 1
    if (Test-AgentHealth) {
        Write-Host "Local Playwright agent is ready at $healthUrl"
        exit 0
    }
}

Write-Host "Local Playwright agent did not become ready within $WaitSeconds seconds."
if (Test-Path -LiteralPath $stderrLog) {
    Write-Host "--- stderr tail ---"
    Get-Content -LiteralPath $stderrLog -Tail 40
}
if (Test-Path -LiteralPath $stdoutLog) {
    Write-Host "--- stdout tail ---"
    Get-Content -LiteralPath $stdoutLog -Tail 40
}
exit 1
