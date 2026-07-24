param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseTag,

    [string[]]$Components = @('backend', 'frontend'),

    [string]$RemoteHost = '172.31.119.49',

    [int]$RemotePort = 22,

    [string]$User = 'root',

    [string]$Password = $env:TESTHUB_SPLIT_REMOTE_PASSWORD,

    [string]$RemoteReleaseRoot = '/AIOps/releases/testhub-platform-split',

    [string]$RuntimeDir = '/AIOps/apps/testhub-platform-split-20260429',

    [string]$OutputRoot = '.release_out',

    [switch]$SkipBuild,

    [switch]$SkipSmoke
)

$ErrorActionPreference = 'Stop'

if (-not $Password) {
    throw 'Remote password is required. Pass -Password or set TESTHUB_SPLIT_REMOTE_PASSWORD.'
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
$buildScript = Join-Path $scriptDir 'build_release_bundle.ps1'
$publishScript = Join-Path $scriptDir 'publish_release_remote.ps1'

$buildParams = @{
    ReleaseTag = $ReleaseTag
    Components = $Components
    OutputRoot = $OutputRoot
}
if ($SkipBuild) {
    $buildParams.SkipBuild = $true
}

& $buildScript @buildParams
if ($LASTEXITCODE -ne 0) {
    throw 'Release bundle build failed.'
}

$releaseDir = Join-Path $repoRoot (Join-Path $OutputRoot "testhub-platform-release-$ReleaseTag")
if (-not (Test-Path -LiteralPath $releaseDir)) {
    throw "Release directory not found: $releaseDir"
}

$publishParams = @{
    ReleaseDir = $releaseDir
    RemoteHost = $RemoteHost
    RemotePort = $RemotePort
    User = $User
    Password = $Password
    RemoteReleaseRoot = $RemoteReleaseRoot
    RuntimeDir = $RuntimeDir
    AutoApply = $true
}
if (-not $SkipSmoke) {
    $publishParams.RunSmoke = $true
}

& $publishScript @publishParams
if ($LASTEXITCODE -ne 0) {
    throw 'Remote release publish/apply failed.'
}

Write-Host "Split runtime release completed: $ReleaseTag"
