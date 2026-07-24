param(
    [string]$BackendImage = 'local/testhub-platform-backend-bundle:latest',

    [string]$FrontendImage = '',

    [string[]]$SourceNeedles = @(
        'build_recording_script_generation_prompt',
        'class AssistantSessionWorkspace',
        'def create_workspace_from_prompt',
        'class AIDevelopmentTask',
        'OFFICIAL_PROJECT_PRODUCT_IMPLEMENTATION_PROMPT_CODE'
    )
)

$ErrorActionPreference = 'Stop'

function Test-DockerImageExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Image
    )

    try {
        docker image inspect $Image *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

if (-not (Test-DockerImageExists -Image $BackendImage)) {
    throw "Backend image not found: $BackendImage"
}

$needleArgs = @()
foreach ($needle in $SourceNeedles) {
    $needleArgs += $needle
}

$backendScanScript = @'
set -eu
fail=0
roots="/app/backend /app/apps /app/tools"

plain_files="$(
  for root in $roots; do
    if [ -d "$root" ]; then
      find "$root" -type f -name '*.py' -exec sh -c '
        for file do
          if grep -q "__pyarmor__" "$file"; then
            continue
          fi
          if grep -Eq "^[[:space:]]*(def |class |from |import |@)" "$file"; then
            echo "$file"
          fi
        done
      ' sh {} +
    fi
  done
)"

if [ -n "$plain_files" ]; then
  echo "[source-scan] plain Python source candidates detected:"
  echo "$plain_files"
  fail=1
else
  echo "[source-scan] no plain Python source candidates detected under backend/apps/tools."
fi

for needle in "$@"; do
  hits="$(grep -R -n -F "$needle" /app/backend /app/apps /app/tools 2>/dev/null || true)"
  if [ -n "$hits" ]; then
    echo "[source-scan] source marker detected: $needle"
    echo "$hits" | head -20
    fail=1
  fi
done

exit "$fail"
'@

docker run --rm --entrypoint sh $BackendImage -c $backendScanScript -- @needleArgs
if ($LASTEXITCODE -ne 0) {
    throw "Backend source protection scan failed for image: $BackendImage"
}

if ($FrontendImage) {
    if (-not (Test-DockerImageExists -Image $FrontendImage)) {
        throw "Frontend image not found: $FrontendImage"
    }

    $frontendFailed = $false

    $mapFiles = @(docker run --rm --entrypoint find $FrontendImage /usr/share/nginx/html -type f -name '*.map' 2>$null)
    if ($mapFiles.Count -gt 0) {
        Write-Host '[frontend-scan] source map files detected:'
        $mapFiles | ForEach-Object { Write-Host $_ }
        $frontendFailed = $true
    } else {
        Write-Host '[frontend-scan] no .map files detected.'
    }

    $sourceMapRefs = @(docker run --rm --entrypoint grep $FrontendImage -R -n -F sourceMappingURL /usr/share/nginx/html 2>$null)
    if ($sourceMapRefs.Count -gt 0) {
        Write-Host '[frontend-scan] sourceMappingURL references detected:'
        $sourceMapRefs | Select-Object -First 20 | ForEach-Object { Write-Host $_ }
        $frontendFailed = $true
    } else {
        Write-Host '[frontend-scan] no sourceMappingURL references detected.'
    }

    $srcRefs = @(docker run --rm --entrypoint grep $FrontendImage -R -n -F 'frontend/src' /usr/share/nginx/html 2>$null)
    if ($srcRefs.Count -gt 0) {
        Write-Host '[frontend-scan] frontend source path references detected:'
        $srcRefs | Select-Object -First 20 | ForEach-Object { Write-Host $_ }
        $frontendFailed = $true
    } else {
        Write-Host '[frontend-scan] no frontend/src references detected.'
    }

    if ($frontendFailed) {
        throw "Frontend source map scan failed for image: $FrontendImage"
    }
}

Write-Host 'Protected release scan passed.'
