param(
    [Parameter(Mandatory = $true)]
    [Alias('Host')]
    [string]$RemoteHost,

    [int]$RemotePort = 22,

    [Parameter(Mandatory = $true)]
    [string]$User,

    [Parameter(Mandatory = $true)]
    [string]$Password,

    [string]$RuntimeDir = '/AIOps/apps/testhub-platform-offline-20260424',

    [string]$ImageTag,

    [string]$HistoryDir,

    [string[]]$Components = @('backend', 'frontend'),

    [switch]$RunSmoke
)

$ErrorActionPreference = 'Stop'

if (-not $ImageTag -and -not $HistoryDir) {
    throw 'Either -ImageTag or -HistoryDir must be provided.'
}

$normalizedComponents = @()
foreach ($component in $Components) {
    foreach ($item in ([string]$component -split ',')) {
        $normalized = ([string]$item).Trim().ToLowerInvariant()
        if ($normalized) {
            $normalizedComponents += $normalized
        }
    }
}
$componentsCsv = [string]::Join(',', $normalizedComponents)
$askpass = Join-Path $env:TEMP 'codex-fast-rollback-askpass.cmd'
Set-Content -Path $askpass -Value "@echo $Password" -Encoding ASCII

try {
    $env:SSH_ASKPASS = $askpass
    $env:SSH_ASKPASS_REQUIRE = 'force'
    $env:DISPLAY = 'codex'

    $imageTagArg = if ($ImageTag) { "--image-tag $ImageTag" } else { '' }
    $historyArg = if ($HistoryDir) { "--history-dir $HistoryDir" } else { '' }
    $smokeArg = if ($RunSmoke) { '--run-smoke' } else { '' }
    $command = "bash $RuntimeDir/deploy/release/remote_rollback_release.sh --runtime-dir $RuntimeDir $imageTagArg $historyArg --components $componentsCsv $smokeArg"
    ssh -p $RemotePort -o StrictHostKeyChecking=no "$User@$RemoteHost" $command
    if ($LASTEXITCODE -ne 0) { throw 'Remote rollback failed.' }
}
finally {
    Remove-Item -LiteralPath $askpass -Force -ErrorAction SilentlyContinue
}
