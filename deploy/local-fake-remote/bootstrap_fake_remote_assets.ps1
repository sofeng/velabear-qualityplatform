param(
    [int]$ProjectId = 1,
    [string]$BundleRoot = '/workspace-release',
    [string]$BundlePathPrefix = '/workspace-release',
    [switch]$RefreshRuntimeScripts
)

$composeFile = 'deploy/local-fake-remote/docker-compose.ssh-gateway.yml'

docker compose -f $composeFile up -d --build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker exec testhub-fake-remote-ssh /usr/local/bin/fake-remote-bootstrap-runtime --force
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker exec testhub-local-backend python manage.py bootstrap_fake_remote_target --project-id $ProjectId
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$artifactCommand = @(
    'docker', 'exec', 'testhub-local-backend',
    'python', 'manage.py', 'bootstrap_local_release_artifacts',
    '--project-id', $ProjectId,
    '--bundle-root', $BundleRoot,
    '--bundle-path-prefix', $BundlePathPrefix
)

if ($RefreshRuntimeScripts) {
    $artifactCommand += '--refresh-runtime-scripts'
}

& $artifactCommand[0] $artifactCommand[1..($artifactCommand.Length - 1)]
exit $LASTEXITCODE
