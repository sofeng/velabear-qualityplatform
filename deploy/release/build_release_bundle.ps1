param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseTag,

    [string[]]$Components = @('backend', 'frontend'),

    [string]$OutputRoot = '.release_out',

    [switch]$SkipBuild,

    [switch]$IncludeRuntimeFiles = $true,

    [string]$BackendPythonBase,

    [string]$FrontendNodeBase,

    [string]$FrontendNginxBase,

    [string]$BackendRuntimeBase,

    [switch]$ProtectBackend,

    [switch]$SkipProtectionScan,

    [string]$PyArmorVersion = 'pyarmor',

    [string]$PyArmorOptions = '',

    [int]$PyArmorMaxScriptBytes = 30000,

    [string]$PyArmorLicenseFile = '',

    [switch]$RequirePyArmorLicense
)

$ErrorActionPreference = 'Stop'

function Test-DockerImageExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Image
    )

    try {
        docker image inspect $Image 1>$null 2>$null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Resolve-BaseImage {
    param(
        [string[]]$Candidates,
        [string]$Fallback
    )

    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-DockerImageExists -Image $candidate)) {
            return $candidate
        }
    }

    return $Fallback
}

function Set-LfFileContent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string[]]$Lines
    )

    $content = ($Lines -join "`n") + "`n"
    $encoding = [System.Text.ASCIIEncoding]::new()
    [System.IO.File]::WriteAllText($Path, $content, $encoding)
}

$validComponents = @('backend-runtime', 'backend', 'frontend', 'mysql', 'redis', 'aidev-runtime', 'codex-runtime', 'claude-runtime')
$normalizedComponents = @()
foreach ($component in $Components) {
    $items = [string]$component -split ','
    foreach ($item in $items) {
        $normalized = [string]$item
        $normalized = $normalized.Trim().ToLowerInvariant()
        if (-not $normalized) {
            continue
        }
        if ($validComponents -notcontains $normalized) {
            throw "Unsupported component: $normalized"
        }
        if ($normalizedComponents -notcontains $normalized) {
            $normalizedComponents += $normalized
        }
    }
}

if ($normalizedComponents.Count -eq 0) {
    throw 'At least one component must be selected.'
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
$resolvedOutputRoot = Join-Path $repoRoot $OutputRoot
$releaseName = "testhub-platform-release-$ReleaseTag"
$releaseDir = Join-Path $resolvedOutputRoot $releaseName
$imagesDir = Join-Path $releaseDir 'images'
$runtimeDockerDir = Join-Path $releaseDir 'runtime\deploy\docker'
$runtimeReleaseDir = Join-Path $releaseDir 'runtime\deploy\release'

$resolvedBackendPythonBase = if ($BackendPythonBase) {
    $BackendPythonBase
} else {
    Resolve-BaseImage -Candidates @(
        'local/python-base:3.11-slim',
        'python:3.11-slim',
        'docker.1panel.live/library/python:3.11-slim'
    ) -Fallback 'docker.m.daocloud.io/library/python:3.11-slim'
}

$resolvedBackendRuntimeBase = if ($BackendRuntimeBase) {
    $BackendRuntimeBase
} else {
    Resolve-BaseImage -Candidates @(
        'local/testhub-platform-backend-runtime:latest'
    ) -Fallback 'local/testhub-platform-backend-runtime:latest'
}

$resolvedFrontendNodeBase = if ($FrontendNodeBase) {
    $FrontendNodeBase
} else {
    Resolve-BaseImage -Candidates @(
        'local/node-base:20-alpine',
        'node:20-alpine',
        'docker.1panel.live/library/node:20-alpine'
    ) -Fallback 'docker.m.daocloud.io/library/node:20-alpine'
}

$resolvedFrontendNginxBase = if ($FrontendNginxBase) {
    $FrontendNginxBase
} else {
    Resolve-BaseImage -Candidates @(
        'local/nginx-base:alpine',
        'nginx:alpine',
        'docker.1panel.live/library/nginx:alpine'
    ) -Fallback 'docker.m.daocloud.io/library/nginx:1.27-alpine'
}

if (Test-Path -LiteralPath $releaseDir) {
    throw "Release directory already exists: $releaseDir"
}

New-Item -ItemType Directory -Force -Path $imagesDir | Out-Null
if ($IncludeRuntimeFiles) {
    New-Item -ItemType Directory -Force -Path $runtimeDockerDir | Out-Null
    New-Item -ItemType Directory -Force -Path $runtimeReleaseDir | Out-Null
}

Push-Location $repoRoot
try {
    if (-not $SkipBuild) {
        if ($normalizedComponents -contains 'backend-runtime') {
            docker build `
                --build-arg "PYTHON_BASE=$resolvedBackendPythonBase" `
                -t "local/testhub-platform-backend-runtime:latest" `
                -t "local/testhub-platform-backend-runtime:$ReleaseTag" `
                -f deploy/docker/backend.runtime-base.Dockerfile .
            if ($LASTEXITCODE -ne 0) { throw 'Backend runtime image build failed.' }
        }

        if ($normalizedComponents -contains 'backend') {
            if (-not (Test-DockerImageExists -Image $resolvedBackendRuntimeBase)) {
                docker build `
                    --build-arg "PYTHON_BASE=$resolvedBackendPythonBase" `
                    -t "local/testhub-platform-backend-runtime:latest" `
                    -f deploy/docker/backend.runtime-base.Dockerfile .
                if ($LASTEXITCODE -ne 0) { throw 'Backend runtime image build failed.' }
                $resolvedBackendRuntimeBase = 'local/testhub-platform-backend-runtime:latest'
            }

            $backendDockerfile = if ($ProtectBackend) { 'deploy/docker/backend.protected.Dockerfile' } else { 'deploy/docker/backend.container.Dockerfile' }
            if ($ProtectBackend) {
                $env:DOCKER_BUILDKIT = '1'
            }
            $backendBuildArgs = @(
                'build',
                '--build-arg', "BACKEND_RUNTIME_BASE=$resolvedBackendRuntimeBase",
                '-t', "local/testhub-platform-backend-bundle:$ReleaseTag",
                '-f', $backendDockerfile
            )
            if ($ProtectBackend) {
                $backendBuildArgs += @(
                    '--build-arg', "PYTHON_BASE=$resolvedBackendPythonBase",
                    '--build-arg', "PYARMOR_VERSION=$PyArmorVersion",
                    '--build-arg', "PYARMOR_OPTIONS=$PyArmorOptions",
                    '--build-arg', "PYARMOR_MAX_SCRIPT_BYTES=$PyArmorMaxScriptBytes",
                    '--build-arg', "PYARMOR_LICENSE_REQUIRED=$(if ($RequirePyArmorLicense) { '1' } else { '0' })"
                )
                if ($PyArmorLicenseFile) {
                    $resolvedPyArmorLicenseFile = (Resolve-Path -LiteralPath $PyArmorLicenseFile).Path
                    $backendBuildArgs += @('--secret', "id=pyarmor_license,src=$resolvedPyArmorLicenseFile")
                }
            }
            $backendBuildArgs += '.'

            docker @backendBuildArgs
            if ($LASTEXITCODE -ne 0) { throw 'Backend image build failed.' }
        }

        if ($normalizedComponents -contains 'frontend') {
            docker build `
                --build-arg "NODE_BASE=$resolvedFrontendNodeBase" `
                --build-arg "NGINX_BASE=$resolvedFrontendNginxBase" `
                -t "local/testhub-platform-frontend-bundle:$ReleaseTag" `
                -f deploy/docker/frontend.container.Dockerfile .
            if ($LASTEXITCODE -ne 0) { throw 'Frontend image build failed.' }
        }

        if ($normalizedComponents -contains 'aidev-runtime') {
            docker build `
                -t "testhub/ai-dev:latest" `
                -t "testhub/ai-dev:$ReleaseTag" `
                -f deploy/Dockerfile.ai-dev .
            if ($LASTEXITCODE -ne 0) { throw 'AI dev runtime image build failed.' }
        }

        if ($normalizedComponents -contains 'codex-runtime') {
            docker build `
                -t "local/testhub-platform-codex-runtime:latest" `
                -t "local/testhub-platform-codex-runtime:$ReleaseTag" `
                -f deploy/docker/codex-runtime.Dockerfile .
            if ($LASTEXITCODE -ne 0) { throw 'Codex runtime image build failed.' }
        }

        if ($normalizedComponents -contains 'claude-runtime') {
            docker build `
                -t "local/testhub-platform-claude-runtime:latest" `
                -t "local/testhub-platform-claude-runtime:$ReleaseTag" `
                -f deploy/docker/claude-runtime.Dockerfile .
            if ($LASTEXITCODE -ne 0) { throw 'Claude runtime image build failed.' }
        }

        if ($ProtectBackend -and -not $SkipProtectionScan -and ($normalizedComponents -contains 'backend')) {
            $scanScript = Join-Path $repoRoot 'deploy\protection\scan_protected_release.ps1'
            if ($normalizedComponents -contains 'frontend') {
                & $scanScript -BackendImage "local/testhub-platform-backend-bundle:$ReleaseTag" -FrontendImage "local/testhub-platform-frontend-bundle:$ReleaseTag"
            } else {
                & $scanScript -BackendImage "local/testhub-platform-backend-bundle:$ReleaseTag"
            }
            if ($LASTEXITCODE -ne 0) { throw 'Protected release scan failed.' }
        }
    }

    if ($SkipBuild -and $ProtectBackend -and -not $SkipProtectionScan -and ($normalizedComponents -contains 'backend')) {
        $scanScript = Join-Path $repoRoot 'deploy\protection\scan_protected_release.ps1'
        if ($normalizedComponents -contains 'frontend') {
            & $scanScript -BackendImage "local/testhub-platform-backend-bundle:$ReleaseTag" -FrontendImage "local/testhub-platform-frontend-bundle:$ReleaseTag"
        } else {
            & $scanScript -BackendImage "local/testhub-platform-backend-bundle:$ReleaseTag"
        }
        if ($LASTEXITCODE -ne 0) { throw 'Protected release scan failed.' }
    }

    if ($normalizedComponents -contains 'mysql') {
        docker image inspect local/testhub-mysql-bundle:8.0 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'MySQL bundle image not found: local/testhub-mysql-bundle:8.0' }
    }

    if ($normalizedComponents -contains 'backend-runtime') {
        docker image inspect "local/testhub-platform-backend-runtime:latest" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Backend runtime image not found: local/testhub-platform-backend-runtime:latest' }
    }

    if ($normalizedComponents -contains 'redis') {
        docker image inspect local/testhub-redis-bundle:7-alpine | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Redis bundle image not found: local/testhub-redis-bundle:7-alpine' }
    }

    if ($normalizedComponents -contains 'aidev-runtime') {
        docker image inspect "testhub/ai-dev:latest" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'AI dev runtime image not found: testhub/ai-dev:latest' }
    }

    if ($normalizedComponents -contains 'codex-runtime') {
        docker image inspect "local/testhub-platform-codex-runtime:latest" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Codex runtime image not found: local/testhub-platform-codex-runtime:latest' }
    }

    if ($normalizedComponents -contains 'claude-runtime') {
        docker image inspect "local/testhub-platform-claude-runtime:latest" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Claude runtime image not found: local/testhub-platform-claude-runtime:latest' }
    }

    if ($normalizedComponents -contains 'backend') {
        docker save -o (Join-Path $imagesDir "backend-$ReleaseTag.tar") "local/testhub-platform-backend-bundle:$ReleaseTag"
        if ($LASTEXITCODE -ne 0) { throw 'Backend image export failed.' }
    }

    if ($normalizedComponents -contains 'backend-runtime') {
        docker save -o (Join-Path $imagesDir "backend-runtime-$ReleaseTag.tar") "local/testhub-platform-backend-runtime:latest" "local/testhub-platform-backend-runtime:$ReleaseTag"
        if ($LASTEXITCODE -ne 0) { throw 'Backend runtime image export failed.' }
    }

    if ($normalizedComponents -contains 'frontend') {
        docker save -o (Join-Path $imagesDir "frontend-$ReleaseTag.tar") "local/testhub-platform-frontend-bundle:$ReleaseTag"
        if ($LASTEXITCODE -ne 0) { throw 'Frontend image export failed.' }
    }

    if ($normalizedComponents -contains 'mysql') {
        docker save -o (Join-Path $imagesDir "mysql-8.0.tar") "local/testhub-mysql-bundle:8.0"
        if ($LASTEXITCODE -ne 0) { throw 'MySQL image export failed.' }
    }

    if ($normalizedComponents -contains 'redis') {
        docker save -o (Join-Path $imagesDir "redis-7-alpine.tar") "local/testhub-redis-bundle:7-alpine"
        if ($LASTEXITCODE -ne 0) { throw 'Redis image export failed.' }
    }

    if ($normalizedComponents -contains 'aidev-runtime') {
        docker save -o (Join-Path $imagesDir "aidev-runtime-$ReleaseTag.tar") "testhub/ai-dev:latest" "testhub/ai-dev:$ReleaseTag"
        if ($LASTEXITCODE -ne 0) { throw 'AI dev runtime image export failed.' }
    }

    if ($normalizedComponents -contains 'claude-runtime') {
        docker save -o (Join-Path $imagesDir "claude-runtime-$ReleaseTag.tar") "local/testhub-platform-claude-runtime:latest" "local/testhub-platform-claude-runtime:$ReleaseTag"
        if ($LASTEXITCODE -ne 0) { throw 'Claude runtime image export failed.' }
    }

    if ($normalizedComponents -contains 'codex-runtime') {
        docker save -o (Join-Path $imagesDir "codex-runtime-$ReleaseTag.tar") "local/testhub-platform-codex-runtime:latest" "local/testhub-platform-codex-runtime:$ReleaseTag"
        if ($LASTEXITCODE -ne 0) { throw 'Codex runtime image export failed.' }
    }
}
finally {
    Pop-Location
}

$componentsCsv = [string]::Join(',', $normalizedComponents)
$updateImageTag = if ($normalizedComponents -contains 'backend' -or $normalizedComponents -contains 'frontend') { '1' } else { '0' }
$runBackendInit = if ($normalizedComponents -contains 'backend') { '1' } else { '0' }

$recreateServices = @()
$smokeServices = @()

if ($normalizedComponents -contains 'mysql') {
    $recreateServices += 'testhub-mysql'
    $smokeServices += 'testhub-mysql'
}
if ($normalizedComponents -contains 'redis') {
    $recreateServices += 'testhub-redis'
    $smokeServices += 'testhub-redis'
}
if ($normalizedComponents -contains 'backend') {
    $recreateServices += 'testhub-backend'
    $recreateServices += 'testhub-celery-worker'
    $recreateServices += 'testhub-ai-dev-worker'
    $smokeServices += 'testhub-backend'
    $smokeServices += 'testhub-celery-worker'
    $smokeServices += 'testhub-ai-dev-worker'
}
if ($normalizedComponents -contains 'frontend') {
    $recreateServices += 'testhub-frontend'
    $smokeServices += 'testhub-frontend'
}

$releaseEnv = @(
    "RELEASE_TAG=$ReleaseTag"
    "RELEASE_CREATED_AT_UTC=$([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))"
    "COMPONENTS_CSV=$componentsCsv"
    "UPDATE_IMAGE_TAG=$updateImageTag"
    "RUN_BACKEND_INIT=$runBackendInit"
    "PROTECT_BACKEND=$([int]$ProtectBackend.IsPresent)"
    "RECREATE_SERVICES=""$([string]::Join(' ', $recreateServices))"""
    "SMOKE_SERVICES=""$([string]::Join(' ', $smokeServices))"""
)
Set-LfFileContent -Path (Join-Path $releaseDir 'release.env') -Lines $releaseEnv

$releaseNotes = @(
    "Release: $ReleaseTag"
    "CreatedAtUtc: $([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))"
    "Components: $componentsCsv"
    "UpdateImageTag: $updateImageTag"
    "RunBackendInit: $runBackendInit"
    "ProtectBackend: $($ProtectBackend.IsPresent)"
    "PyArmorVersion: $PyArmorVersion"
    "PyArmorOptions: $PyArmorOptions"
    "PyArmorMaxScriptBytes: $PyArmorMaxScriptBytes"
    "BackendPythonBase: $resolvedBackendPythonBase"
    "BackendRuntimeBase: $resolvedBackendRuntimeBase"
    "FrontendNodeBase: $resolvedFrontendNodeBase"
    "FrontendNginxBase: $resolvedFrontendNginxBase"
)
Set-LfFileContent -Path (Join-Path $releaseDir 'RELEASE_NOTES.txt') -Lines $releaseNotes

if ($IncludeRuntimeFiles) {
    Copy-Item -LiteralPath (Join-Path $repoRoot 'deploy\docker\docker-compose.offline.yml') -Destination $runtimeDockerDir -Force
    Copy-Item -LiteralPath (Join-Path $repoRoot 'deploy\docker\.env.bundle.example') -Destination $runtimeDockerDir -Force
    Copy-Item -LiteralPath (Join-Path $repoRoot 'deploy\release\remote_apply_release.sh') -Destination $runtimeReleaseDir -Force
    Copy-Item -LiteralPath (Join-Path $repoRoot 'deploy\release\remote_smoke_verify.sh') -Destination $runtimeReleaseDir -Force
    Copy-Item -LiteralPath (Join-Path $repoRoot 'deploy\release\remote_rollback_release.sh') -Destination $runtimeReleaseDir -Force
}

Write-Host "Release bundle created: $releaseDir"
