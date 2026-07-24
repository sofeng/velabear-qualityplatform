param(
    [string[]]$Components = @('backend', 'frontend'),

    [string]$RemoteHost = '172.31.119.49',

    [int]$RemotePort = 22,

    [string]$User = 'root',

    [string]$Password = $env:TESTHUB_SPLIT_REMOTE_PASSWORD,

    [string]$RuntimeDir = '/AIOps/apps/testhub-platform-split-20260429'
)

$ErrorActionPreference = 'Stop'

if (-not $Password) {
    throw 'Remote password is required. Pass -Password or set TESTHUB_SPLIT_REMOTE_PASSWORD.'
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$smokeScript = Join-Path $scriptDir 'smoke_release_remote.ps1'

& $smokeScript `
    -RemoteHost $RemoteHost `
    -RemotePort $RemotePort `
    -User $User `
    -Password $Password `
    -RuntimeDir $RuntimeDir `
    -Components $Components

if ($LASTEXITCODE -ne 0) {
    throw 'Split runtime smoke verification failed.'
}
