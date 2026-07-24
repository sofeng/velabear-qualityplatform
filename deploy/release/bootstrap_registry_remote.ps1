param(
    [Parameter(Mandatory = $true)]
    [Alias('Host')]
    [string]$RemoteHost,

    [Parameter(Mandatory = $true)]
    [string]$User,

    [Parameter(Mandatory = $true)]
    [string]$Password,

    [string]$RegistryHost,

    [int]$RegistryPort = 5443,

    [string]$DataRoot = '/AIOps/data/testhub-release-registry',

    [string]$ContainerName = 'testhub-release-registry',

    [string]$BindIp = '0.0.0.0',

    [int]$CertDays = 3650,

    [switch]$ForceRegenerateCert
)

$ErrorActionPreference = 'Stop'

if (-not $RegistryHost) {
    $RegistryHost = $RemoteHost
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$remoteScript = (Resolve-Path (Join-Path $scriptDir 'remote_bootstrap_registry.sh')).Path
$askpass = Join-Path $env:TEMP 'codex-registry-bootstrap-askpass.cmd'
$localTempRoot = Join-Path $env:TEMP 'codex-registry-bootstrap'
$localCertPath = Join-Path $localTempRoot "$RegistryHost-$RegistryPort-registry.crt"
$remoteBootstrapDir = "/tmp/testhub-registry-bootstrap-$([DateTime]::UtcNow.ToString('yyyyMMddHHmmss'))"
$forceArg = if ($ForceRegenerateCert) { '--force-regenerate-cert' } else { '' }

New-Item -ItemType Directory -Force -Path $localTempRoot | Out-Null
Set-Content -Path $askpass -Value "@echo $Password" -Encoding ASCII

try {
    $env:SSH_ASKPASS = $askpass
    $env:SSH_ASKPASS_REQUIRE = 'force'
    $env:DISPLAY = 'codex'

    ssh -o StrictHostKeyChecking=no "$User@$RemoteHost" "mkdir -p $remoteBootstrapDir"
    if ($LASTEXITCODE -ne 0) { throw 'Remote bootstrap temp directory creation failed.' }

    scp -o StrictHostKeyChecking=no $remoteScript "$User@$RemoteHost`:$remoteBootstrapDir/"
    if ($LASTEXITCODE -ne 0) { throw 'Remote bootstrap script upload failed.' }

    $command = "bash $remoteBootstrapDir/remote_bootstrap_registry.sh --registry-host $RegistryHost --registry-port $RegistryPort --data-root $DataRoot --container-name $ContainerName --bind-ip $BindIp --cert-days $CertDays $forceArg"
    ssh -o StrictHostKeyChecking=no "$User@$RemoteHost" $command
    if ($LASTEXITCODE -ne 0) { throw 'Remote registry bootstrap failed.' }

    scp -o StrictHostKeyChecking=no "$User@$RemoteHost`:$DataRoot/certs/registry.crt" $localCertPath
    if ($LASTEXITCODE -ne 0) { throw 'Registry CA certificate download failed.' }

    Import-Certificate -FilePath $localCertPath -CertStoreLocation Cert:\CurrentUser\Root | Out-Null

    Write-Host "Registry bootstrap completed: https://$RegistryHost`:$RegistryPort"
    Write-Host "CA certificate imported to Cert:\\CurrentUser\\Root"
    Write-Host "If docker push or pull still reports TLS trust errors, restart Docker Desktop once."
}
finally {
    Remove-Item -LiteralPath $askpass -Force -ErrorAction SilentlyContinue
}
