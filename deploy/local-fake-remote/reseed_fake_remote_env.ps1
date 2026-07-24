param(
    [string]$ImageTag = 'latest',
    [string]$BackupDir = '.docker-data/fake-remote-backups',
    [switch]$SkipBackup,
    [switch]$SkipRuntimeSync
)

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
    $scriptPath = if ($PSScriptRoot) {
        $PSScriptRoot
    } elseif ($PSCommandPath) {
        Split-Path -Parent $PSCommandPath
    } else {
        Split-Path -Parent $MyInvocation.MyCommand.Path
    }
    $scriptRoot = $scriptPath
    return (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
}

function Test-ContainerExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $names = docker ps -a --format '{{.Names}}'
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to inspect docker containers.'
    }

    return @($names) -contains $Name
}

function Wait-BackendInit {
    param(
        [int]$MaxAttempts = 180,
        [int]$SleepSeconds = 2
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt += 1) {
        $state = docker inspect testhub-fake-remote-backend-init --format '{{.State.Status}} {{.State.ExitCode}}' 2>$null
        if ($LASTEXITCODE -eq 0) {
            if ($state -eq 'exited 0') {
                return
            }

            if ($state -like 'exited *') {
                docker logs testhub-fake-remote-backend-init --tail 200
                throw "Fake remote backend init failed: $state"
            }
        }

        Start-Sleep -Seconds $SleepSeconds
    }

    docker logs testhub-fake-remote-backend-init --tail 200
    throw 'Timed out waiting for fake remote backend init to finish.'
}

function Invoke-RetryWebRequest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$MaxAttempts = 20,
        [int]$SleepSeconds = 3
    )

    $lastError = $null
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt += 1) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 30
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $response
            }
        }
        catch {
            $lastError = $_
        }

        Start-Sleep -Seconds $SleepSeconds
    }

    if ($lastError) {
        throw "HTTP probe failed for ${Url}: $($lastError.Exception.Message)"
    }

    throw "HTTP probe failed for ${Url}"
}

$repoRoot = Get-RepoRoot
$scriptRoot = if ($PSScriptRoot) {
    $PSScriptRoot
} elseif ($PSCommandPath) {
    Split-Path -Parent $PSCommandPath
} else {
    Split-Path -Parent $MyInvocation.MyCommand.Path
}
$composeFile = Join-Path $scriptRoot 'docker-compose.fake-remote-target.yml'
$templateEnv = Join-Path $scriptRoot '.env.fake-remote-target.example'
$syncScript = Join-Path $scriptRoot 'sync_fake_remote_runtime.ps1'
$resolvedBackupDir = if ([System.IO.Path]::IsPathRooted($BackupDir)) {
    $BackupDir
} else {
    Join-Path $repoRoot $BackupDir
}

$tempEnv = Join-Path $env:TEMP "testhub-fake-remote-$ImageTag.env"
$volumes = @(
    'testhub-fake-remote_testhub_fake_remote_mysql'
    'testhub-fake-remote_testhub_fake_remote_redis'
    'testhub-fake-remote_testhub_fake_remote_appdata'
    'testhub-fake-remote_testhub_fake_remote_media'
    'testhub-fake-remote_testhub_fake_remote_static'
    'testhub-fake-remote_testhub_fake_remote_logs'
)

Copy-Item -LiteralPath $templateEnv -Destination $tempEnv -Force
try {
    $envLines = Get-Content $tempEnv
    $envLines = $envLines | ForEach-Object {
        if ($_ -match '^IMAGE_TAG=') {
            "IMAGE_TAG=$ImageTag"
        } else {
            $_
        }
    }
    Set-Content -Path $tempEnv -Value $envLines -Encoding ASCII

    if (-not $SkipRuntimeSync -and (Test-ContainerExists -Name 'testhub-fake-remote-ssh')) {
        & $syncScript
        if ($LASTEXITCODE -ne 0) {
            throw 'Failed to sync fake remote runtime.'
        }
    }

    if (-not $SkipBackup -and (Test-ContainerExists -Name 'testhub-fake-remote-mysql')) {
        New-Item -ItemType Directory -Force -Path $resolvedBackupDir | Out-Null
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $backupFile = Join-Path $resolvedBackupDir "fake-remote-mysql-$stamp.sql"
        docker exec testhub-fake-remote-mysql sh -lc "mysqldump -uroot -proot123 --databases testhub --single-transaction --quick --routines --events" |
            Out-File -FilePath $backupFile -Encoding utf8
        Write-Host "Backup created: $backupFile"
    }

    docker compose --env-file $tempEnv -f $composeFile down
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to stop fake remote environment.'
    }

    docker volume rm $volumes
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to remove fake remote volumes.'
    }

    docker compose --env-file $tempEnv -f $composeFile up -d
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to recreate fake remote environment.'
    }

    Wait-BackendInit

    $backendResponse = Invoke-RetryWebRequest -Url 'http://localhost:58000/admin/login/'
    $frontendResponse = Invoke-RetryWebRequest -Url 'http://localhost:51080/'

    Write-Host "Backend admin status: $($backendResponse.StatusCode)"
    Write-Host "Frontend status: $($frontendResponse.StatusCode)"
    Write-Host "Fake remote reseed completed with IMAGE_TAG=$ImageTag"
}
finally {
    Remove-Item -LiteralPath $tempEnv -Force -ErrorAction SilentlyContinue
}
