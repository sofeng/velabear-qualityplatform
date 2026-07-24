param(
    [switch]$Build,
    [switch]$SkipCompose,
    [switch]$SkipAgent,
    [string]$ComposeFile = "deploy/docker/docker-compose.bundle.yml",
    [string]$LocalOverrideFile = "deploy/docker/docker-compose.local-validate.yml"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

if (!$SkipCompose) {
    $composeArgs = @("compose", "-f", $ComposeFile, "-f", $LocalOverrideFile, "up", "-d")
    if ($Build) {
        $composeArgs += "--build"
    }

    Write-Host "Starting TestHub local Docker services..."
    & docker @composeArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (!$SkipAgent) {
    Write-Host "Starting Local Playwright agent..."
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools/start_local_playwright_agent.ps1")
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Host ""
Write-Host "TestHub local services are ready."
Write-Host "Frontend: http://localhost:41080"
Write-Host "Backend:  http://localhost:48000"
Write-Host "Agent:    http://127.0.0.1:18765/health"
