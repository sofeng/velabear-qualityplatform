param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseTag,

    [Parameter(Mandatory = $true)]
    [string]$RegistryEndpoint,

    [string]$RegistryNamespace = 'testhub-platform',

    [string[]]$Components = @('backend', 'frontend'),

    [string]$OutputRoot = '.release_out',

    [switch]$SkipBuild,

    [switch]$SkipPush,

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

function Push-TaggedImage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceImage,

        [Parameter(Mandatory = $true)]
        [string]$TargetImage
    )

    docker image inspect $SourceImage *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Source image not found: $SourceImage"
    }

    docker tag $SourceImage $TargetImage
    if ($LASTEXITCODE -ne 0) { throw "Failed to tag image: $SourceImage -> $TargetImage" }

    docker push $TargetImage
    if ($LASTEXITCODE -ne 0) { throw "Failed to push image: $TargetImage" }
}

$validComponents = @('backend-runtime', 'backend', 'frontend', 'mysql', 'redis', 'aidev-runtime', 'codex-runtime', 'claude-runtime')
$normalizedComponents = @()
foreach ($component in $Components) {
    $items = [string]$component -split ','
    foreach ($item in $items) {
        $normalized = ([string]$item).Trim().ToLowerInvariant()
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
$releaseName = "testhub-platform-registry-release-$ReleaseTag"
$releaseDir = Join-Path $resolvedOutputRoot $releaseName
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

$registryBase = "$RegistryEndpoint/$RegistryNamespace"
$componentRefs = @{
    'backend-runtime' = "$registryBase/backend-runtime:$ReleaseTag"
    'backend' = "$registryBase/backend:$ReleaseTag"
    'frontend' = "$registryBase/frontend:$ReleaseTag"
    'mysql' = "$registryBase/mysql:$ReleaseTag"
    'redis' = "$registryBase/redis:$ReleaseTag"
    'aidev-runtime' = "$registryBase/ai-dev:$ReleaseTag"
    'codex-runtime' = "$registryBase/codex-runtime:$ReleaseTag"
    'claude-runtime' = "$registryBase/claude-runtime:$ReleaseTag"
}

if (Test-Path -LiteralPath $releaseDir) {
    throw "Release directory already exists: $releaseDir"
}

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
if ($IncludeRuntimeFiles) {
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
                -t "testhub/ai-dev:$ReleaseTag" `
                -f deploy/Dockerfile.ai-dev .
            if ($LASTEXITCODE -ne 0) { throw 'AI dev runtime image build failed.' }
        }

        if ($normalizedComponents -contains 'codex-runtime') {
            docker build `
                -t "local/testhub-platform-codex-runtime:$ReleaseTag" `
                -f deploy/docker/codex-runtime.Dockerfile .
            if ($LASTEXITCODE -ne 0) { throw 'Codex runtime image build failed.' }
        }

        if ($normalizedComponents -contains 'claude-runtime') {
            docker build `
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

    if (-not $SkipPush) {
        if ($normalizedComponents -contains 'backend-runtime') {
            Push-TaggedImage -SourceImage "local/testhub-platform-backend-runtime:$ReleaseTag" -TargetImage $componentRefs['backend-runtime']
        }

        if ($normalizedComponents -contains 'backend') {
            Push-TaggedImage -SourceImage "local/testhub-platform-backend-bundle:$ReleaseTag" -TargetImage $componentRefs['backend']
        }

        if ($normalizedComponents -contains 'frontend') {
            Push-TaggedImage -SourceImage "local/testhub-platform-frontend-bundle:$ReleaseTag" -TargetImage $componentRefs['frontend']
        }

        if ($normalizedComponents -contains 'mysql') {
            Push-TaggedImage -SourceImage 'local/testhub-mysql-bundle:8.0' -TargetImage $componentRefs['mysql']
        }

        if ($normalizedComponents -contains 'redis') {
            Push-TaggedImage -SourceImage 'local/testhub-redis-bundle:7-alpine' -TargetImage $componentRefs['redis']
        }

        if ($normalizedComponents -contains 'aidev-runtime') {
            Push-TaggedImage -SourceImage "testhub/ai-dev:$ReleaseTag" -TargetImage $componentRefs['aidev-runtime']
        }

        if ($normalizedComponents -contains 'claude-runtime') {
            Push-TaggedImage -SourceImage "local/testhub-platform-claude-runtime:$ReleaseTag" -TargetImage $componentRefs['claude-runtime']
        }

        if ($normalizedComponents -contains 'codex-runtime') {
            Push-TaggedImage -SourceImage "local/testhub-platform-codex-runtime:$ReleaseTag" -TargetImage $componentRefs['codex-runtime']
        }
    } else {
        if ($normalizedComponents -contains 'backend-runtime') {
            docker image inspect "local/testhub-platform-backend-runtime:$ReleaseTag" *> $null
            if ($LASTEXITCODE -ne 0) { throw "Missing local image for dry-run: local/testhub-platform-backend-runtime:$ReleaseTag" }
        }

        if ($normalizedComponents -contains 'backend') {
            docker image inspect "local/testhub-platform-backend-bundle:$ReleaseTag" *> $null
            if ($LASTEXITCODE -ne 0) { throw "Missing local image for dry-run: local/testhub-platform-backend-bundle:$ReleaseTag" }
        }

        if ($normalizedComponents -contains 'frontend') {
            docker image inspect "local/testhub-platform-frontend-bundle:$ReleaseTag" *> $null
            if ($LASTEXITCODE -ne 0) { throw "Missing local image for dry-run: local/testhub-platform-frontend-bundle:$ReleaseTag" }
        }

        if ($normalizedComponents -contains 'mysql') {
            docker image inspect 'local/testhub-mysql-bundle:8.0' *> $null
            if ($LASTEXITCODE -ne 0) { throw 'Missing local image for dry-run: local/testhub-mysql-bundle:8.0' }
        }

        if ($normalizedComponents -contains 'redis') {
            docker image inspect 'local/testhub-redis-bundle:7-alpine' *> $null
            if ($LASTEXITCODE -ne 0) { throw 'Missing local image for dry-run: local/testhub-redis-bundle:7-alpine' }
        }

        if ($normalizedComponents -contains 'aidev-runtime') {
            docker image inspect "testhub/ai-dev:$ReleaseTag" *> $null
            if ($LASTEXITCODE -ne 0) { throw "Missing local image for dry-run: testhub/ai-dev:$ReleaseTag" }
        }

        if ($normalizedComponents -contains 'codex-runtime') {
            docker image inspect "local/testhub-platform-codex-runtime:$ReleaseTag" *> $null
            if ($LASTEXITCODE -ne 0) { throw "Missing local image for dry-run: local/testhub-platform-codex-runtime:$ReleaseTag" }
        }

        if ($normalizedComponents -contains 'claude-runtime') {
            docker image inspect "local/testhub-platform-claude-runtime:$ReleaseTag" *> $null
            if ($LASTEXITCODE -ne 0) { throw "Missing local image for dry-run: local/testhub-platform-claude-runtime:$ReleaseTag" }
        }
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
    'RELEASE_MODE=registry'
    "RELEASE_TAG=$ReleaseTag"
    "RELEASE_CREATED_AT_UTC=$([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))"
    "COMPONENTS_CSV=$componentsCsv"
    "UPDATE_IMAGE_TAG=$updateImageTag"
    "RUN_BACKEND_INIT=$runBackendInit"
    "SKIP_PUSH=$([int]$SkipPush.IsPresent)"
    "PROTECT_BACKEND=$([int]$ProtectBackend.IsPresent)"
    "REGISTRY_ENDPOINT=$RegistryEndpoint"
    "REGISTRY_NAMESPACE=$RegistryNamespace"
    "RECREATE_SERVICES=""$([string]::Join(' ', $recreateServices))"""
    "SMOKE_SERVICES=""$([string]::Join(' ', $smokeServices))"""
)

foreach ($component in $normalizedComponents) {
    switch ($component) {
        'backend-runtime' { $releaseEnv += "BACKEND_RUNTIME_IMAGE_REF=$($componentRefs[$component])" }
        'backend' { $releaseEnv += "BACKEND_IMAGE_REF=$($componentRefs[$component])" }
        'frontend' { $releaseEnv += "FRONTEND_IMAGE_REF=$($componentRefs[$component])" }
        'mysql' { $releaseEnv += "MYSQL_IMAGE_REF=$($componentRefs[$component])" }
        'redis' { $releaseEnv += "REDIS_IMAGE_REF=$($componentRefs[$component])" }
        'aidev-runtime' { $releaseEnv += "AIDEV_RUNTIME_IMAGE_REF=$($componentRefs[$component])" }
        'codex-runtime' { $releaseEnv += "CODEX_RUNTIME_IMAGE_REF=$($componentRefs[$component])" }
        'claude-runtime' { $releaseEnv += "CLAUDE_RUNTIME_IMAGE_REF=$($componentRefs[$component])" }
    }
}

Set-LfFileContent -Path (Join-Path $releaseDir 'release.env') -Lines $releaseEnv

$releaseNotes = @(
    "Release: $ReleaseTag"
    "Mode: registry"
    "CreatedAtUtc: $([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))"
    "RegistryEndpoint: $RegistryEndpoint"
    "RegistryNamespace: $RegistryNamespace"
    "Components: $componentsCsv"
    "SkipPush: $($SkipPush.IsPresent)"
    "ProtectBackend: $($ProtectBackend.IsPresent)"
    "PyArmorVersion: $PyArmorVersion"
    "PyArmorOptions: $PyArmorOptions"
    "PyArmorMaxScriptBytes: $PyArmorMaxScriptBytes"
    "UpdateImageTag: $updateImageTag"
    "RunBackendInit: $runBackendInit"
    "BackendPythonBase: $resolvedBackendPythonBase"
    "BackendRuntimeBase: $resolvedBackendRuntimeBase"
    "FrontendNodeBase: $resolvedFrontendNodeBase"
    "FrontendNginxBase: $resolvedFrontendNginxBase"
)
Set-LfFileContent -Path (Join-Path $releaseDir 'RELEASE_NOTES.txt') -Lines $releaseNotes

$manifestLines = @()
foreach ($component in $normalizedComponents) {
    $manifestLines += "$component=$($componentRefs[$component])"
}
Set-LfFileContent -Path (Join-Path $releaseDir 'image-manifest.txt') -Lines $manifestLines

if ($IncludeRuntimeFiles) {
    Copy-Item -LiteralPath (Join-Path $repoRoot 'deploy\release\remote_apply_registry_release.sh') -Destination $runtimeReleaseDir -Force
    Copy-Item -LiteralPath (Join-Path $repoRoot 'deploy\release\remote_smoke_verify.sh') -Destination $runtimeReleaseDir -Force
    Copy-Item -LiteralPath (Join-Path $repoRoot 'deploy\release\remote_rollback_registry_release.sh') -Destination $runtimeReleaseDir -Force
}

if ($SkipPush) {
    Write-Host "Registry release dry-run created: $releaseDir"
} else {
    Write-Host "Registry release created: $releaseDir"
}
