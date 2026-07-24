param(
    [string]$ReleaseTag = 'protected-local',

    [ValidateSet('core', 'automation', 'document', 'asset', 'integration', 'report', 'deployment', 'ai-dev')]
    [string]$Role = 'core',

    [string]$ImageRepository = 'local/testhub-platform-backend-bundle',

    [string]$BackendRuntimeBase = '',

    [string]$BackendCoreRuntimeBase = 'local/testhub-platform-backend-core-runtime:latest',

    [string]$BackendPythonBase = 'docker.m.daocloud.io/library/python:3.11-slim',

    [string]$ProtectedCodeImage = '',

    [string]$ProtectedCodeImageRepository = 'local/testhub-platform-backend-protected-code',

    [string]$PyArmorVersion = 'pyarmor',

    [string]$PyArmorOptions = '',

    [int]$PyArmorMaxScriptBytes = 30000,

    [string]$PyArmorLicenseFile = '',

    [switch]$RequirePyArmorLicense,

    [string]$PipIndexUrl = $(if ($env:PIP_INDEX_URL) { $env:PIP_INDEX_URL } else { 'https://pypi.tuna.tsinghua.edu.cn/simple' }),

    [string]$PipTrustedHost = $env:PIP_TRUSTED_HOST,

    [switch]$BuildRuntimeBase,

    [switch]$SkipProtectedCodeBuild,

    [switch]$NoCache,

    [switch]$TagLatest
)

$ErrorActionPreference = 'Stop'

function Test-DockerImageExists {
    param([Parameter(Mandatory = $true)][string]$Image)

    try {
        docker image inspect $Image *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

$runtimeDefaults = @{
    core = $BackendCoreRuntimeBase
    automation = 'local/testhub-platform-backend-automation-runtime:latest'
    document = 'local/testhub-platform-backend-document-runtime:latest'
    asset = 'local/testhub-platform-backend-asset-runtime:latest'
    integration = 'local/testhub-platform-backend-integration-runtime:latest'
    report = 'local/testhub-platform-backend-report-runtime:latest'
    deployment = 'local/testhub-platform-backend-deployment-runtime:latest'
    'ai-dev' = 'local/testhub-platform-backend-integration-runtime:latest'
}

$runtimeDockerfiles = @{
    core = 'deploy/docker/backend.core-runtime.Dockerfile'
    automation = 'deploy/docker/backend.automation-runtime.Dockerfile'
    document = 'deploy/docker/backend.document-runtime.Dockerfile'
    asset = 'deploy/docker/backend.asset-runtime.Dockerfile'
    integration = 'deploy/docker/backend.integration-runtime.Dockerfile'
    report = 'deploy/docker/backend.report-runtime.Dockerfile'
    deployment = 'deploy/docker/backend.deployment-runtime.Dockerfile'
    'ai-dev' = 'deploy/docker/backend.integration-runtime.Dockerfile'
}

$finalDockerfiles = @{
    core = 'deploy/docker/backend.protected.Dockerfile'
    automation = 'deploy/docker/backend.protected-automation.Dockerfile'
    document = 'deploy/docker/backend.protected-service.Dockerfile'
    asset = 'deploy/docker/backend.protected-service.Dockerfile'
    integration = 'deploy/docker/backend.protected-service.Dockerfile'
    report = 'deploy/docker/backend.protected-service.Dockerfile'
    deployment = 'deploy/docker/backend.protected-deployment.Dockerfile'
    'ai-dev' = 'deploy/docker/backend.protected-service.Dockerfile'
}

if (-not $BackendRuntimeBase) {
    $BackendRuntimeBase = $runtimeDefaults[$Role]
}
if (-not $ProtectedCodeImage) {
    $ProtectedCodeImage = "${ProtectedCodeImageRepository}:${ReleaseTag}"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
$targetImage = "${ImageRepository}:${ReleaseTag}"
$env:DOCKER_BUILDKIT = '1'

Push-Location $repoRoot
try {
    if ($BuildRuntimeBase -or -not (Test-DockerImageExists -Image $BackendRuntimeBase)) {
        $runtimeArgs = @(
            'build',
            '--build-arg', "PYTHON_BASE=$BackendPythonBase",
            '--build-arg', "BACKEND_CORE_RUNTIME_BASE=$BackendCoreRuntimeBase",
            '-t', $BackendRuntimeBase,
            '-f', $runtimeDockerfiles[$Role]
        )
        if ($NoCache) { $runtimeArgs += '--no-cache' }
        $runtimeArgs += '.'
        docker @runtimeArgs
        if ($LASTEXITCODE -ne 0) { throw "Runtime image build failed for role '$Role'." }
    }

    if (-not $SkipProtectedCodeBuild) {
        $codeArgs = @(
            'build',
            '--build-arg', "PYTHON_BASE=$BackendPythonBase",
            '--build-arg', "PYARMOR_VERSION=$PyArmorVersion",
            '--build-arg', "PYARMOR_OPTIONS=$PyArmorOptions",
            '--build-arg', "PYARMOR_MAX_SCRIPT_BYTES=$PyArmorMaxScriptBytes",
            '--build-arg', "PYARMOR_LICENSE_REQUIRED=$(if ($RequirePyArmorLicense) { '1' } else { '0' })",
            '--build-arg', "PIP_INDEX_URL=$PipIndexUrl",
            '-t', $ProtectedCodeImage,
            '-f', 'deploy/docker/backend.protected-code.Dockerfile'
        )
        if ($PipTrustedHost) {
            $codeArgs += @('--build-arg', "PIP_TRUSTED_HOST=$PipTrustedHost")
        }
        if ($NoCache) { $codeArgs += '--no-cache' }
        if ($PyArmorLicenseFile) {
            $resolvedLicenseFile = (Resolve-Path -LiteralPath $PyArmorLicenseFile).Path
            $codeArgs += @('--secret', "id=pyarmor_license,src=$resolvedLicenseFile")
        }
        $codeArgs += '.'
        docker @codeArgs
        if ($LASTEXITCODE -ne 0) { throw 'Protected code artifact build failed.' }
    }
    elseif (-not (Test-DockerImageExists -Image $ProtectedCodeImage)) {
        throw "Protected code image does not exist: $ProtectedCodeImage"
    }

    $finalArgs = @(
        'build',
        '--build-arg', "PROTECTED_CODE_IMAGE=$ProtectedCodeImage",
        '--build-arg', "BACKEND_RUNTIME_BASE=$BackendRuntimeBase",
        '--build-arg', "TESTHUB_RUNTIME_ROLE=$Role",
        '-t', $targetImage,
        '-f', $finalDockerfiles[$Role]
    )
    if ($NoCache) { $finalArgs += '--no-cache' }
    $finalArgs += '.'

    docker @finalArgs
    if ($LASTEXITCODE -ne 0) { throw "Protected image build failed for role '$Role'." }

    if ($TagLatest) {
        docker tag $targetImage "${ImageRepository}:latest"
        if ($LASTEXITCODE -ne 0) { throw 'Failed to tag protected image as latest.' }
    }
}
finally {
    Pop-Location
}

Write-Host "Protected image built: $targetImage"
Write-Host "Runtime role: $Role"
Write-Host "Runtime base: $BackendRuntimeBase"
Write-Host "Protected code artifact: $ProtectedCodeImage"
if ($TagLatest) {
    Write-Host "Latest tag updated: ${ImageRepository}:latest"
}
