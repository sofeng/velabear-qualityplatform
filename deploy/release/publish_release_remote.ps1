param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseDir,

    [Parameter(Mandatory = $true)]
    [Alias('Host')]
    [string]$RemoteHost,

    [int]$RemotePort = 22,

    [Parameter(Mandatory = $true)]
    [string]$User,

    [Parameter(Mandatory = $true)]
    [string]$Password,

    [string]$RemoteReleaseRoot = '/AIOps/releases/testhub-platform',

    [string]$RuntimeDir = '/AIOps/apps/testhub-platform-offline-20260424',

    [switch]$AutoApply,

    [switch]$RunSmoke
)

$ErrorActionPreference = 'Stop'

$resolvedReleaseDir = (Resolve-Path $ReleaseDir).Path
$releaseLeaf = Split-Path -Leaf $resolvedReleaseDir
$remoteReleaseDir = "$RemoteReleaseRoot/$releaseLeaf"

$requiredFiles = @(
    (Join-Path $resolvedReleaseDir 'release.env'),
    (Join-Path $resolvedReleaseDir 'runtime\deploy\release\remote_apply_release.sh'),
    (Join-Path $resolvedReleaseDir 'runtime\deploy\release\remote_smoke_verify.sh'),
    (Join-Path $resolvedReleaseDir 'runtime\deploy\release\remote_rollback_release.sh')
)

foreach ($requiredFile in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $requiredFile)) {
        throw "Required release file not found: $requiredFile"
    }
}

$askpass = Join-Path $env:TEMP 'codex-fast-release-askpass.cmd'
Set-Content -Path $askpass -Value "@echo $Password" -Encoding ASCII

try {
    $env:SSH_ASKPASS = $askpass
    $env:SSH_ASKPASS_REQUIRE = 'force'
    $env:DISPLAY = 'codex'

    ssh -p $RemotePort -o StrictHostKeyChecking=no "$User@$RemoteHost" "mkdir -p $RemoteReleaseRoot"
    if ($LASTEXITCODE -ne 0) { throw 'Remote release root creation failed.' }

    scp -P $RemotePort -o StrictHostKeyChecking=no -r $resolvedReleaseDir "$User@$RemoteHost`:$RemoteReleaseRoot/"
    if ($LASTEXITCODE -ne 0) { throw 'Release upload failed.' }

    if ($AutoApply) {
        $smokeFlag = if ($RunSmoke) { '--run-smoke' } else { '' }
        $command = "bash $remoteReleaseDir/runtime/deploy/release/remote_apply_release.sh --runtime-dir $RuntimeDir --release-dir $remoteReleaseDir $smokeFlag"
        ssh -p $RemotePort -o StrictHostKeyChecking=no "$User@$RemoteHost" $command
        if ($LASTEXITCODE -ne 0) { throw 'Remote release apply failed.' }
    }
}
finally {
    Remove-Item -LiteralPath $askpass -Force -ErrorAction SilentlyContinue
}

Write-Host "Remote release directory: $remoteReleaseDir"
