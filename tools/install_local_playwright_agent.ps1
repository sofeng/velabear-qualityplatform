param(
    [string]$InstallDir = "",
    [string]$Python = "python",
    [string]$PlatformUrl = "",
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"

$minPythonMajor = 3
$minPythonMinor = 10
$minPipVersion = "23.0"
$minRequestsVersion = "2.31.0"
$minPlaywrightVersion = "1.44.0"
$pythonInstallVersion = "3.12.10"
$pythonEmbeddedVersion = "3.12.10"
$pythonDownloadBaseUrl = "https://www.python.org/ftp/python"
$getPipUrl = "https://bootstrap.pypa.io/get-pip.py"
$agentHealthUrl = "http://127.0.0.1:18765/health"
$domesticPythonDownloadBaseUrls = @(
    "https://npmmirror.com/mirrors/python",
    "https://mirrors.huaweicloud.com/python",
    "https://registry.npmmirror.com/-/binary/python"
)
$domesticGetPipUrls = @(
    "https://mirrors.aliyun.com/pypi/get-pip.py"
)
$domesticPipIndexUrls = @(
    "https://mirrors.aliyun.com/pypi/simple/",
    "https://mirrors.cloud.tencent.com/pypi/simple/",
    "https://pypi.tuna.tsinghua.edu.cn/simple/"
)
$domesticPlaywrightDownloadHosts = @(
    "https://npmmirror.com/mirrors/playwright"
)
$dependencySourceFailurePatterns = @(
    "timed out",
    "timeout",
    "ReadTimeout",
    "ConnectTimeout",
    "ConnectionError",
    "Connection reset",
    "Failed to establish a new connection",
    "Max retries exceeded",
    "NameResolutionError",
    "ProxyError",
    "RemoteDisconnected",
    "SSLError",
    "Temporary failure",
    "Network is unreachable",
    "No route to host",
    "Client network socket",
    "socket hang up",
    "i/o timeout",
    "ECONNRESET",
    "ETIMEDOUT",
    "ENOTFOUND",
    "EAI_AGAIN",
    "Download failure",
    "Download failed",
    "Could not fetch URL",
    "Unable to connect",
    "The remote name could not be resolved",
    "请求超时",
    "操作超时",
    "连接超时",
    "无法连接",
    "无法解析",
    "未能解析",
    "读取超时",
    "名称解析",
    "远程主机强迫关闭",
    "基础连接已经关闭",
    "连接尝试失败",
    "连接失败"
)
$script:selectedPythonDownloadUrl = ""
$script:selectedGetPipUrl = ""
$script:selectedPipIndexUrl = ""
$script:selectedPlaywrightDownloadHost = ""

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "[TestHub Agent] $Message"
}

function Update-ProcessPathFromRegistry {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $paths = @($machinePath, $userPath) | Where-Object { ![string]::IsNullOrWhiteSpace($_) }
    if ($paths.Count -gt 0) {
        $env:Path = ($paths -join ";")
    }
}

function Add-ProcessPath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path) -or !(Test-Path -LiteralPath $Path)) {
        return
    }
    $existing = @($env:Path -split ';') | Where-Object { ![string]::IsNullOrWhiteSpace($_) }
    if ($existing -notcontains $Path) {
        $env:Path = "$Path;$env:Path"
    }
}

function Add-PythonInstallPathToProcess {
    param([string]$PythonExe)
    if ([string]::IsNullOrWhiteSpace($PythonExe) -or !(Test-Path -LiteralPath $PythonExe)) {
        return
    }
    $pythonDir = Split-Path -Parent $PythonExe
    Add-ProcessPath -Path $pythonDir
    Add-ProcessPath -Path (Join-Path $pythonDir "Scripts")
}

function Get-InstallerArchitecture {
    if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") {
        return "arm64"
    }
    return "amd64"
}

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$Arguments = @()
    )
    $stderrPath = Join-Path $env:TEMP ("testhub-agent-stderr-" + [guid]::NewGuid().ToString("N") + ".log")
    $output = @()
    try {
        $output = @(& $FilePath @Arguments 2> $stderrPath)
        $exitCode = $LASTEXITCODE
        $stderrOutput = @()
        if (Test-Path -LiteralPath $stderrPath) {
            $stderrOutput = @(Get-Content -LiteralPath $stderrPath -ErrorAction SilentlyContinue)
        }
        return [pscustomobject]@{
            ExitCode = $exitCode
            Output = @($output) + @($stderrOutput)
        }
    } finally {
        Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue
    }
}

function Write-CommandOutput {
    param($Result)
    foreach ($line in @($Result.Output)) {
        Write-Host $line
    }
}

function Test-DependencySourceFailure {
    param(
        [string[]]$Output = @(),
        [string]$ExceptionMessage = ""
    )
    $text = ((@($Output) + @($ExceptionMessage)) | Where-Object { ![string]::IsNullOrWhiteSpace([string]$_) }) -join "`n"
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $false
    }
    foreach ($pattern in $dependencySourceFailurePatterns) {
        if ($text.IndexOf($pattern, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            return $true
        }
    }
    return $false
}

function Get-UniqueStringList {
    param([string[]]$Values = @())
    $items = New-Object System.Collections.Generic.List[string]
    $seen = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($value in @($Values)) {
        $item = [string]$value
        if (![string]::IsNullOrWhiteSpace($item) -and $seen.Add($item)) {
            $items.Add($item) | Out-Null
        }
    }
    return $items.ToArray()
}

function Get-PythonDownloadUrl {
    param(
        [string]$BaseUrl,
        [string]$Version,
        [string]$FileName
    )
    return "$($BaseUrl.TrimEnd('/'))/$Version/$FileName"
}

function Get-DomesticPythonDownloadUrls {
    param(
        [string]$Version,
        [string]$FileName
    )
    return @($domesticPythonDownloadBaseUrls | ForEach-Object {
        Get-PythonDownloadUrl -BaseUrl $_ -Version $Version -FileName $FileName
    })
}

function Invoke-WebDownloadWithMirrorRetry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PrimaryUrl,
        [string[]]$FallbackUrls = @(),
        [Parameter(Mandatory = $true)]
        [string]$OutFile,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $urls = Get-UniqueStringList -Values (@($PrimaryUrl) + @($FallbackUrls))
    $lastError = ""
    for ($i = 0; $i -lt $urls.Count; $i += 1) {
        $url = $urls[$i]
        if ($i -eq 0) {
            Write-Step "Downloading ${Label}: $url"
        } else {
            Write-Step "Retrying ${Label} with domestic mirror: $url"
        }
        try {
            Invoke-WebRequest -Uri $url -OutFile $OutFile -UseBasicParsing -TimeoutSec 180
            return $url
        } catch {
            $lastError = $_.Exception.Message
            Write-Warning "${Label} download failed from ${url}: $lastError"
            if ($i -eq 0 -and (Test-DependencySourceFailure -ExceptionMessage $lastError)) {
                Write-Warning "Detected network/source failure. Switching to domestic mirror and retrying automatically."
            }
        }
    }
    throw "Failed to download $Label. Last error: $lastError"
}

function Set-PipSourceForProcess {
    param([string]$IndexUrl)
    if ([string]::IsNullOrWhiteSpace($IndexUrl)) {
        return
    }
    $script:selectedPipIndexUrl = $IndexUrl
    $env:PIP_INDEX_URL = $IndexUrl
    $env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
    Write-Host "Using domestic PyPI source for this Agent installation: $IndexUrl"
}

function Invoke-PipCommandWithMirrorRetry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonPath,
        [string[]]$PipArguments,
        [Parameter(Mandatory = $true)]
        [string]$OperationName,
        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    $result = Invoke-NativeCommand -FilePath $PythonPath -Arguments (@("-m", "pip") + @($PipArguments))
    Write-CommandOutput -Result $result
    if ($result.ExitCode -eq 0) {
        return $result
    }

    if (!(Test-DependencySourceFailure -Output $result.Output)) {
        throw $FailureMessage
    }

    Write-Warning "Detected pip network/source failure during $OperationName. Configuring domestic PyPI source and retrying automatically."
    foreach ($indexUrl in $domesticPipIndexUrls) {
        Set-PipSourceForProcess -IndexUrl $indexUrl
        $retryArgs = @("-m", "pip") + @($PipArguments) + @("-i", $indexUrl, "--timeout", "60", "--retries", "5")
        $retryResult = Invoke-NativeCommand -FilePath $PythonPath -Arguments $retryArgs
        Write-CommandOutput -Result $retryResult
        if ($retryResult.ExitCode -eq 0) {
            return $retryResult
        }
    }

    throw $FailureMessage
}

function Invoke-GetPipBootstrapWithMirrorRetry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonPath,
        [Parameter(Mandatory = $true)]
        [string]$GetPipPath
    )

    $baseArgs = @($GetPipPath, "--no-warn-script-location")
    $result = Invoke-NativeCommand -FilePath $PythonPath -Arguments $baseArgs
    Write-CommandOutput -Result $result
    if ($result.ExitCode -eq 0) {
        return $result
    }

    if (!(Test-DependencySourceFailure -Output $result.Output)) {
        throw "Failed to bootstrap pip in embedded Python runtime."
    }

    Write-Warning "Detected pip bootstrap source/network failure. Configuring domestic PyPI source and retrying automatically."
    foreach ($indexUrl in $domesticPipIndexUrls) {
        Set-PipSourceForProcess -IndexUrl $indexUrl
        $retryResult = Invoke-NativeCommand -FilePath $PythonPath -Arguments ($baseArgs + @("-i", $indexUrl, "--timeout", "60", "--retries", "5"))
        Write-CommandOutput -Result $retryResult
        if ($retryResult.ExitCode -eq 0) {
            return $retryResult
        }
    }

    throw "Failed to bootstrap pip in embedded Python runtime."
}

function Invoke-PlaywrightInstallWithMirrorRetry {
    param([string]$PythonPath)

    $result = Invoke-NativeCommand -FilePath $PythonPath -Arguments @("-m", "playwright", "install", "chromium")
    Write-CommandOutput -Result $result
    if ($result.ExitCode -eq 0) {
        return $result
    }

    if (!(Test-DependencySourceFailure -Output $result.Output)) {
        throw "Failed to install Playwright Chromium."
    }

    Write-Warning "Detected Playwright browser download source/network failure. Configuring domestic browser mirror and retrying automatically."
    foreach ($downloadHost in $domesticPlaywrightDownloadHosts) {
        $script:selectedPlaywrightDownloadHost = $downloadHost
        $env:PLAYWRIGHT_DOWNLOAD_HOST = $downloadHost
        Write-Host "Using domestic Playwright download host for this Agent installation: $downloadHost"
        $retryResult = Invoke-NativeCommand -FilePath $PythonPath -Arguments @("-m", "playwright", "install", "chromium")
        Write-CommandOutput -Result $retryResult
        if ($retryResult.ExitCode -eq 0) {
            return $retryResult
        }
    }

    throw "Failed to install Playwright Chromium."
}

function Get-ExistingAgentConfig {
    param([string]$TargetInstallDir)
    $configPath = Join-Path $TargetInstallDir "agent_config.json"
    if (!(Test-Path -LiteralPath $configPath)) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Get-ConfigValue {
    param(
        $Config,
        [string]$Name
    )
    if ($null -ne $Config -and $Config.PSObject.Properties.Name -contains $Name) {
        return [string]$Config.$Name
    }
    return ""
}

function Get-VersionParts {
    param([string]$VersionText)
    $match = [regex]::Match([string]$VersionText, "\d+(?:\.\d+){0,3}")
    if (!$match.Success) {
        return @(0, 0, 0, 0)
    }
    $parts = @($match.Value.Split(".") | ForEach-Object { [int]$_ })
    while ($parts.Count -lt 4) {
        $parts += 0
    }
    return $parts[0..3]
}

function Test-VersionAtLeast {
    param(
        [string]$Current,
        [string]$Minimum
    )
    $currentParts = Get-VersionParts $Current
    $minimumParts = Get-VersionParts $Minimum
    for ($i = 0; $i -lt 4; $i += 1) {
        if ($currentParts[$i] -gt $minimumParts[$i]) {
            return $true
        }
        if ($currentParts[$i] -lt $minimumParts[$i]) {
            return $false
        }
    }
    return $true
}

function Get-PythonPackageVersion {
    param(
        [string]$PythonPath,
        [string]$PackageName
    )
    $versionScript = "import importlib.metadata as m; print(m.version('$PackageName'))"
    try {
        $output = @(& $PythonPath -c $versionScript 2>$null)
        if ($LASTEXITCODE -ne 0 -or $output.Count -lt 1) {
            return ""
        }
        return [string]$output[0]
    } catch {
        return ""
    }
}

function Get-PythonInfoFromCommand {
    param(
        [string]$Command,
        [string[]]$CommandArgs = @()
    )
    if ([string]::IsNullOrWhiteSpace($Command)) {
        return $null
    }

$probeScript = @"
import sys
print(sys.executable)
print('%d.%d.%d' % (sys.version_info.major, sys.version_info.minor, sys.version_info.micro))
raise SystemExit(0 if sys.version_info >= ($minPythonMajor, $minPythonMinor) else 7)
"@
    try {
        $probeResult = Invoke-NativeCommand -FilePath $Command -Arguments (@($CommandArgs) + @("-c", $probeScript))
        $output = @($probeResult.Output)
        if ($probeResult.ExitCode -ne 0 -or $output.Count -lt 2) {
            return $null
        }
        $resolvedPath = [string]$output[0]
        if ([string]::IsNullOrWhiteSpace($resolvedPath) -or !(Test-Path -LiteralPath $resolvedPath)) {
            return $null
        }
        return [pscustomobject]@{
            Path = (Resolve-Path -LiteralPath $resolvedPath).Path
            Version = [string]$output[1]
        }
    } catch {
        return $null
    }
}

function Get-CandidatePythonCommands {
    param(
        [string]$PreferredPython,
        [string]$ConfiguredPython
    )

    $candidates = New-Object System.Collections.Generic.List[object]
    $seen = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
    function Add-Candidate {
        param([string]$Command, [string[]]$Args = @())
        if (![string]::IsNullOrWhiteSpace($Command)) {
            $key = "$Command|$($Args -join ' ')"
            if ($seen.Add($key)) {
                $candidates.Add([pscustomobject]@{ Command = $Command; Args = $Args }) | Out-Null
            }
        }
    }

    Add-Candidate $ConfiguredPython
    Add-Candidate $PreferredPython
    Add-Candidate "python"
    Add-Candidate "python3"
    Add-Candidate "py" @("-3.12")
    Add-Candidate "py" @("-3.11")
    Add-Candidate "py" @("-3.10")
    Add-Candidate "py" @("-3")

    $commonRoots = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python")
        $env:ProgramFiles
        ${env:ProgramFiles(x86)}
    ) | Where-Object { ![string]::IsNullOrWhiteSpace($_) }
    foreach ($root in $commonRoots) {
        foreach ($versionDir in @("Python313", "Python312", "Python311", "Python310")) {
            Add-Candidate (Join-Path (Join-Path $root $versionDir) "python.exe")
        }
        if (Test-Path -LiteralPath $root) {
            Get-ChildItem -LiteralPath $root -Directory -Filter "Python3*" -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending |
                ForEach-Object { Add-Candidate (Join-Path $_.FullName "python.exe") }
        }
    }

    $registryRoots = @(
        "HKCU:\Software\Python\PythonCore",
        "HKLM:\Software\Python\PythonCore",
        "HKLM:\Software\WOW6432Node\Python\PythonCore"
    )
    foreach ($registryRoot in $registryRoots) {
        if (!(Test-Path -LiteralPath $registryRoot)) {
            continue
        }
        Get-ChildItem -LiteralPath $registryRoot -ErrorAction SilentlyContinue |
            Sort-Object PSChildName -Descending |
            ForEach-Object {
                $installPathKey = Join-Path $_.PSPath "InstallPath"
                try {
                    $installPath = (Get-ItemProperty -LiteralPath $installPathKey -ErrorAction Stop)."(default)"
                    if ([string]::IsNullOrWhiteSpace($installPath)) {
                        $installPath = (Get-ItemProperty -LiteralPath $installPathKey -ErrorAction Stop).ExecutablePath
                    }
                    if (![string]::IsNullOrWhiteSpace($installPath)) {
                        $pythonExe = if ($installPath.EndsWith(".exe", [System.StringComparison]::OrdinalIgnoreCase)) {
                            $installPath
                        } else {
                            Join-Path $installPath "python.exe"
                        }
                        Add-Candidate $pythonExe
                    }
                } catch {
                }
            }
    }

    $appPathKeys = @(
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\python.exe",
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\App Paths\python.exe"
    )
    foreach ($appPathKey in $appPathKeys) {
        try {
            $appPath = (Get-ItemProperty -LiteralPath $appPathKey -ErrorAction Stop)."(default)"
            Add-Candidate $appPath
        } catch {
        }
    }
    return $candidates
}

function Find-UsablePython {
    param(
        [string]$PreferredPython,
        [string]$ConfiguredPython
    )
    foreach ($candidate in Get-CandidatePythonCommands -PreferredPython $PreferredPython -ConfiguredPython $ConfiguredPython) {
        $info = Get-PythonInfoFromCommand -Command $candidate.Command -CommandArgs $candidate.Args
        if ($null -ne $info) {
            return $info
        }
    }
    return $null
}

function Install-PythonForCurrentUser {
    Write-Step "Python $minPythonMajor.$minPythonMinor+ was not found or does not satisfy the minimum version. Installing Python for current user..."

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        try {
            $wingetResult = Invoke-NativeCommand -FilePath $winget.Source -Arguments @("install", "--id", "Python.Python.3.12", "--exact", "--source", "winget", "--scope", "user", "--silent", "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity")
            foreach ($line in $wingetResult.Output) {
                Write-Host $line
            }
            if ($wingetResult.ExitCode -eq 0) {
                Update-ProcessPathFromRegistry
                return
            }
            Write-Warning "winget Python installation exited with code $($wingetResult.ExitCode). Falling back to python.org installer."
        } catch {
            Write-Warning "winget Python installation failed: $($_.Exception.Message). Falling back to python.org installer."
        }
    }

    $architecture = Get-InstallerArchitecture
    $installerName = "python-$pythonInstallVersion-$architecture.exe"
    $installerUrl = Get-PythonDownloadUrl -BaseUrl $pythonDownloadBaseUrl -Version $pythonInstallVersion -FileName $installerName
    $installerPath = Join-Path $env:TEMP $installerName
    $targetDir = Join-Path (Join-Path $env:LOCALAPPDATA "Programs\Python") "Python312"

    $script:selectedPythonDownloadUrl = Invoke-WebDownloadWithMirrorRetry `
        -PrimaryUrl $installerUrl `
        -FallbackUrls (Get-DomesticPythonDownloadUrls -Version $pythonInstallVersion -FileName $installerName) `
        -OutFile $installerPath `
        -Label "Python installer"

    Write-Step "Running Python installer..."
    $installArgs = @(
        "/quiet",
        "InstallAllUsers=0",
        "TargetDir=$targetDir",
        "PrependPath=1",
        "Include_pip=1",
        "Include_launcher=1",
        "Include_test=0",
        "SimpleInstall=1"
    )
    $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
    if ($process.ExitCode -ne 0 -and $process.ExitCode -ne 3010) {
        throw "Python installer failed with exit code $($process.ExitCode)"
    }
    Update-ProcessPathFromRegistry
    Add-PythonInstallPathToProcess -PythonExe (Join-Path $targetDir "python.exe")
}

function Install-EmbeddedPythonRuntime {
    param([string]$TargetInstallDir)

    Write-Step "Installing embedded Python runtime for TestHub Agent..."
    $architecture = Get-InstallerArchitecture
    $runtimeRoot = Join-Path $TargetInstallDir "python-runtime"
    $runtimeDir = Join-Path $runtimeRoot "python-$pythonEmbeddedVersion"
    $pythonExe = Join-Path $runtimeDir "python.exe"
    if (Test-Path -LiteralPath $pythonExe) {
        Add-PythonInstallPathToProcess -PythonExe $pythonExe
        return $pythonExe
    }

    New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
    if (Test-Path -LiteralPath $runtimeDir) {
        Remove-Item -LiteralPath $runtimeDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

    $zipName = "python-$pythonEmbeddedVersion-embed-$architecture.zip"
    $zipUrl = Get-PythonDownloadUrl -BaseUrl $pythonDownloadBaseUrl -Version $pythonEmbeddedVersion -FileName $zipName
    $zipPath = Join-Path $env:TEMP $zipName
    $script:selectedPythonDownloadUrl = Invoke-WebDownloadWithMirrorRetry `
        -PrimaryUrl $zipUrl `
        -FallbackUrls (Get-DomesticPythonDownloadUrls -Version $pythonEmbeddedVersion -FileName $zipName) `
        -OutFile $zipPath `
        -Label "embedded Python runtime"

    Write-Step "Extracting embedded Python runtime..."
    Expand-Archive -LiteralPath $zipPath -DestinationPath $runtimeDir -Force

    $pthFile = Get-ChildItem -LiteralPath $runtimeDir -Filter "python*._pth" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pthFile) {
        $pthLines = Get-Content -LiteralPath $pthFile.FullName -Encoding UTF8
        $updatedLines = @()
        $hasImportSite = $false
        foreach ($line in $pthLines) {
            if ($line -match '^\s*#\s*import\s+site\s*$') {
                $updatedLines += 'import site'
                $hasImportSite = $true
            } else {
                if ($line -match '^\s*import\s+site\s*$') {
                    $hasImportSite = $true
                }
                $updatedLines += $line
            }
        }
        if ($updatedLines -notcontains "Lib\site-packages") {
            $updatedLines += "Lib\site-packages"
        }
        if (!$hasImportSite) {
            $updatedLines += 'import site'
        }
        [System.IO.File]::WriteAllLines(
            $pthFile.FullName,
            [string[]]$updatedLines,
            (New-Object System.Text.UTF8Encoding($false))
        )
    }

    if (!(Test-Path -LiteralPath $pythonExe)) {
        throw "Embedded Python extraction failed. Missing file: $pythonExe"
    }

    Add-PythonInstallPathToProcess -PythonExe $pythonExe

    $getPipPath = Join-Path $env:TEMP "get-pip.py"
    $script:selectedGetPipUrl = Invoke-WebDownloadWithMirrorRetry `
        -PrimaryUrl $getPipUrl `
        -FallbackUrls $domesticGetPipUrls `
        -OutFile $getPipPath `
        -Label "pip bootstrap"
    Write-Step "Bootstrapping pip in embedded Python runtime..."
    $null = Invoke-GetPipBootstrapWithMirrorRetry -PythonPath $pythonExe -GetPipPath $getPipPath
    return [string]$pythonExe
}

function Wait-ForUsablePython {
    param(
        [string]$PreferredPython,
        [string]$ConfiguredPython,
        [int]$TimeoutSeconds = 60
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        Update-ProcessPathFromRegistry
        $info = Find-UsablePython -PreferredPython $PreferredPython -ConfiguredPython $ConfiguredPython
        if ($null -ne $info) {
            Add-PythonInstallPathToProcess -PythonExe $info.Path
            return $info
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    return $null
}

function Ensure-Pip {
    param([string]$PythonPath)
    Write-Step "Checking pip version >= $minPipVersion..."
        $pipVersion = Get-PythonPackageVersion -PythonPath $PythonPath -PackageName "pip"
    if ([string]::IsNullOrWhiteSpace($pipVersion)) {
        Write-Step "pip was not found. Bootstrapping pip with ensurepip..."
        $ensurePipResult = Invoke-NativeCommand -FilePath $PythonPath -Arguments @("-m", "ensurepip", "--upgrade")
        Write-CommandOutput -Result $ensurePipResult
        if ($ensurePipResult.ExitCode -ne 0) {
            Write-Warning "ensurepip failed. Falling back to get-pip.py with automatic domestic mirror retry."
            $getPipPath = Join-Path $env:TEMP "get-pip.py"
            $script:selectedGetPipUrl = Invoke-WebDownloadWithMirrorRetry `
                -PrimaryUrl $getPipUrl `
                -FallbackUrls $domesticGetPipUrls `
                -OutFile $getPipPath `
                -Label "pip bootstrap"
            $null = Invoke-GetPipBootstrapWithMirrorRetry -PythonPath $PythonPath -GetPipPath $getPipPath
        }
        $pipVersion = Get-PythonPackageVersion -PythonPath $PythonPath -PackageName "pip"
    }

    if (!(Test-VersionAtLeast -Current $pipVersion -Minimum $minPipVersion)) {
        Write-Step "pip $pipVersion is below $minPipVersion. Upgrading pip..."
        $null = Invoke-PipCommandWithMirrorRetry `
            -PythonPath $PythonPath `
            -PipArguments @("install", "--upgrade", "--no-warn-script-location", "pip>=$minPipVersion", "setuptools", "wheel") `
            -OperationName "pip upgrade" `
            -FailureMessage "Failed to upgrade pip/setuptools/wheel."
    } else {
        Write-Host "pip version OK: $pipVersion"
    }

    $pipVersion = Get-PythonPackageVersion -PythonPath $PythonPath -PackageName "pip"
    if (!(Test-VersionAtLeast -Current $pipVersion -Minimum $minPipVersion)) {
        throw "pip version $pipVersion is below required $minPipVersion after upgrade."
    }
}

function Ensure-AgentPythonDependencies {
    param([string]$PythonPath)
    Write-Step "Checking Python package versions..."
    $requestsVersion = Get-PythonPackageVersion -PythonPath $PythonPath -PackageName "requests"
    $playwrightVersion = Get-PythonPackageVersion -PythonPath $PythonPath -PackageName "playwright"
    $requiresUpgrade = $false

    if ([string]::IsNullOrWhiteSpace($requestsVersion) -or !(Test-VersionAtLeast -Current $requestsVersion -Minimum $minRequestsVersion)) {
        Write-Host "requests version needs install/upgrade. Current: $requestsVersion Required: $minRequestsVersion"
        $requiresUpgrade = $true
    } else {
        Write-Host "requests version OK: $requestsVersion"
    }

    if ([string]::IsNullOrWhiteSpace($playwrightVersion) -or !(Test-VersionAtLeast -Current $playwrightVersion -Minimum $minPlaywrightVersion)) {
        Write-Host "playwright version needs install/upgrade. Current: $playwrightVersion Required: $minPlaywrightVersion"
        $requiresUpgrade = $true
    } else {
        Write-Host "playwright version OK: $playwrightVersion"
    }

    if ($requiresUpgrade) {
        Write-Step "Installing/upgrading Python packages to required versions..."
        $null = Invoke-PipCommandWithMirrorRetry `
            -PythonPath $PythonPath `
            -PipArguments @("install", "--upgrade", "--no-warn-script-location", "requests>=$minRequestsVersion", "playwright>=$minPlaywrightVersion") `
            -OperationName "requests/playwright install" `
            -FailureMessage "Failed to install/upgrade requests/playwright."
    }

    $requestsVersion = Get-PythonPackageVersion -PythonPath $PythonPath -PackageName "requests"
    $playwrightVersion = Get-PythonPackageVersion -PythonPath $PythonPath -PackageName "playwright"
    if (!(Test-VersionAtLeast -Current $requestsVersion -Minimum $minRequestsVersion)) {
        throw "requests version $requestsVersion is below required $minRequestsVersion after upgrade."
    }
    if (!(Test-VersionAtLeast -Current $playwrightVersion -Minimum $minPlaywrightVersion)) {
        throw "playwright version $playwrightVersion is below required $minPlaywrightVersion after upgrade."
    }

    Write-Step "Installing Playwright Chromium browser..."
    $null = Invoke-PlaywrightInstallWithMirrorRetry -PythonPath $PythonPath

    Write-Step "Verifying Python packages and Playwright Chromium..."
    $verifyScript = @"
import requests
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
browser_path = p.chromium.executable_path
print('chromium_executable=' + browser_path)
try:
    b = p.chromium.launch(headless=True)
    b.close()
    print('chromium_launch=ok')
except Exception as exc:
    print('chromium_launch=warning:' + repr(exc))
p.stop()
print('ok')
"@
    $verifyResult = Invoke-NativeCommand -FilePath $PythonPath -Arguments @("-c", $verifyScript)
    foreach ($line in $verifyResult.Output) {
        Write-Host $line
    }
    if ($verifyResult.ExitCode -ne 0) {
        Write-Warning "Playwright Chromium launch verification did not complete. The Agent installation will continue; if browser actions fail later, run install.bat again or check local security policies."
    }
}

function Resolve-AgentPython {
    param(
        [string]$PreferredPython,
        [string]$ConfiguredPython,
        [string]$TargetInstallDir,
        [bool]$AllowInstall
    )

    $info = Find-UsablePython -PreferredPython $PreferredPython -ConfiguredPython $ConfiguredPython
    if ($null -ne $info) {
        Write-Step "Using Python $($info.Version): $($info.Path)"
        return $info
    }

    if (!$AllowInstall) {
        Write-Warning "Python was not resolved because dependency installation was skipped."
        return [pscustomobject]@{ Path = $PreferredPython; Version = "" }
    }

    Install-PythonForCurrentUser
    Write-Step "Resolving installed Python..."
    $info = Wait-ForUsablePython -PreferredPython $PreferredPython -ConfiguredPython $ConfiguredPython -TimeoutSeconds 60
    if ($null -eq $info) {
        $expectedPath = Join-Path (Join-Path (Join-Path $env:LOCALAPPDATA "Programs\Python") "Python312") "python.exe"
        Write-Warning "System Python installation finished, but python.exe could not be resolved. Expected path checked: $expectedPath"
        Write-Warning "Falling back to an embedded Python runtime managed by TestHub Agent."
        $embeddedPython = Install-EmbeddedPythonRuntime -TargetInstallDir $TargetInstallDir
        $info = Get-PythonInfoFromCommand -Command $embeddedPython
        if ($null -eq $info) {
            throw "Embedded Python runtime was installed but could not be started: $embeddedPython"
        }
    }
    Write-Step "Using Python $($info.Version): $($info.Path)"
    return $info
}

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "TestHub\LocalAgent"
}

$existingConfig = Get-ExistingAgentConfig -TargetInstallDir $InstallDir
$configuredPython = Get-ConfigValue -Config $existingConfig -Name "python_path"
$configuredPlatformUrl = Get-ConfigValue -Config $existingConfig -Name "platform_url"
$configuredInstalledAt = Get-ConfigValue -Config $existingConfig -Name "installed_at"
if ([string]::IsNullOrWhiteSpace($PlatformUrl)) {
    $PlatformUrl = $configuredPlatformUrl
}
$pythonInfo = Resolve-AgentPython -PreferredPython $Python -ConfiguredPython $configuredPython -TargetInstallDir $InstallDir -AllowInstall:(!$SkipDependencyInstall)
$resolvedPython = $pythonInfo.Path

if (!$SkipDependencyInstall) {
    Ensure-Pip -PythonPath $resolvedPython
    Ensure-AgentPythonDependencies -PythonPath $resolvedPython
}

$sourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$requiredFiles = @(
    "local_playwright_agent.py",
    "start_local_playwright_agent.ps1",
    "start_local_playwright_agent.bat",
    "stop_local_playwright_agent.ps1",
    "stop_local_playwright_agent.bat",
    "register_local_playwright_agent.ps1",
    "testhub_agent_protocol.ps1",
    "uninstall_local_playwright_agent.ps1",
    "install_local_playwright_agent.ps1"
)

Write-Step "Copying Agent files to $InstallDir"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

foreach ($fileName in $requiredFiles) {
    $sourcePath = Join-Path $sourceDir $fileName
    if (!(Test-Path -LiteralPath $sourcePath)) {
        throw "Installer package is incomplete. Missing file: $fileName"
    }
    $destinationPath = Join-Path $InstallDir $fileName
    $resolvedSourcePath = (Resolve-Path -LiteralPath $sourcePath).Path
    $resolvedDestinationPath = if (Test-Path -LiteralPath $destinationPath) { (Resolve-Path -LiteralPath $destinationPath).Path } else { $destinationPath }
    if ($resolvedSourcePath -ieq $resolvedDestinationPath) {
        continue
    }
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
}

$installedAt = if ([string]::IsNullOrWhiteSpace($configuredInstalledAt)) { (Get-Date).ToString("o") } else { $configuredInstalledAt }
$config = @{
    platform_url = $PlatformUrl
    installed_at = $installedAt
    updated_at = (Get-Date).ToString("o")
    dependency_checked_at = (Get-Date).ToString("o")
    dependency_status = if ($SkipDependencyInstall) { "skipped" } else { "ready" }
    agent_url = "http://127.0.0.1:18765"
    agent_health_url = $agentHealthUrl
    python_path = $resolvedPython
    python_version = $pythonInfo.Version
    min_python_version = "$minPythonMajor.$minPythonMinor"
    min_pip_version = $minPipVersion
    min_requests_version = $minRequestsVersion
    min_playwright_version = $minPlaywrightVersion
    pip_version = if ($SkipDependencyInstall) { "" } else { Get-PythonPackageVersion -PythonPath $resolvedPython -PackageName "pip" }
    requests_version = if ($SkipDependencyInstall) { "" } else { Get-PythonPackageVersion -PythonPath $resolvedPython -PackageName "requests" }
    playwright_version = if ($SkipDependencyInstall) { "" } else { Get-PythonPackageVersion -PythonPath $resolvedPython -PackageName "playwright" }
    python_download_url = $script:selectedPythonDownloadUrl
    get_pip_url = $script:selectedGetPipUrl
    pip_index_url = $script:selectedPipIndexUrl
    playwright_download_host = $script:selectedPlaywrightDownloadHost
}
$configJson = $config | ConvertTo-Json -Depth 5
$configUtf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $InstallDir "agent_config.json"), $configJson, $configUtf8NoBom)

Write-Step "Registering testhub-agent protocol and startup entry..."
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $InstallDir "register_local_playwright_agent.ps1") -InstallDir $InstallDir -Python $resolvedPython
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Step "Starting local Agent and checking health..."
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $InstallDir "start_local_playwright_agent.ps1") -Python $resolvedPython -WaitSeconds 30
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

try {
    $health = Invoke-RestMethod -Uri $agentHealthUrl -Method Get -TimeoutSec 5
    Write-Host ""
    Write-Host "TestHub Local Agent installed and started."
    Write-Host "Agent health: $agentHealthUrl"
    Write-Host "Agent version: $($health.version)"
    Write-Host "Agent PID: $($health.pid)"
} catch {
    Write-Warning "Agent was started, but final health check failed: $($_.Exception.Message)"
    exit 1
}
