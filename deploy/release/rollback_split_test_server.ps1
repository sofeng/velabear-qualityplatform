param(
    [string]$ImageTag,

    [string]$HistoryDir,

    [string[]]$Components = @('backend', 'frontend'),

    [string]$RemoteHost = '172.31.119.49',

    [int]$RemotePort = 22,

    [string]$User = 'root',

    [string]$Password = $env:TESTHUB_SPLIT_REMOTE_PASSWORD,

    [string]$RuntimeDir = '/AIOps/apps/testhub-platform-split-20260429',

    [switch]$RunSmoke
)

$ErrorActionPreference = 'Stop'

if (-not $Password) {
    throw 'Remote password is required. Pass -Password or set TESTHUB_SPLIT_REMOTE_PASSWORD.'
}

if (-not $ImageTag -and -not $HistoryDir) {
    throw 'Either -ImageTag or -HistoryDir must be provided.'
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rollbackScript = Join-Path $scriptDir 'rollback_release_remote.ps1'

$rollbackParams = @{
    RemoteHost = $RemoteHost
    RemotePort = $RemotePort
    User = $User
    Password = $Password
    RuntimeDir = $RuntimeDir
    Components = $Components
}
if ($ImageTag) {
    $rollbackParams.ImageTag = $ImageTag
}
if ($HistoryDir) {
    $rollbackParams.HistoryDir = $HistoryDir
}
if ($RunSmoke) {
    $rollbackParams.RunSmoke = $true
}

& $rollbackScript @rollbackParams
if ($LASTEXITCODE -ne 0) {
    throw 'Split runtime rollback failed.'
}
