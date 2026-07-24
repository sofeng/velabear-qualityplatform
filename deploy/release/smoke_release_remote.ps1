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

    [string[]]$Components = @('backend', 'frontend')
)

$ErrorActionPreference = 'Stop'

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
$askpass = Join-Path $env:TEMP 'codex-fast-smoke-askpass.cmd'
Set-Content -Path $askpass -Value "@echo $Password" -Encoding ASCII

try {
    $env:SSH_ASKPASS = $askpass
    $env:SSH_ASKPASS_REQUIRE = 'force'
    $env:DISPLAY = 'codex'

    $command = "bash $RuntimeDir/deploy/release/remote_smoke_verify.sh --runtime-dir $RuntimeDir --components $componentsCsv"
    ssh -p $RemotePort -o StrictHostKeyChecking=no "$User@$RemoteHost" $command
    if ($LASTEXITCODE -ne 0) { throw 'Remote smoke verification failed.' }
}
finally {
    Remove-Item -LiteralPath $askpass -Force -ErrorAction SilentlyContinue
}
