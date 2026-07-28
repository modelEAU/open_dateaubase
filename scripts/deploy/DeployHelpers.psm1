#Requires -Version 5.1
<#
.SYNOPSIS
    Helper functions for deploying open_datEAUbase on Windows Server.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

function Write-Step {
    param(
        [string]$Message,
        [switch]$Success,
        [switch]$Warn
    )
    $ts = Get-Date -Format 'HH:mm:ss'
    if ($Success) {
        Write-Host "[$ts] OK  $Message" -ForegroundColor Green
    } elseif ($Warn) {
        Write-Host "[$ts] WARN $Message" -ForegroundColor Yellow
    } else {
        Write-Host "[$ts] --> $Message" -ForegroundColor Cyan
    }
}

function Invoke-WithRetry {
    param(
        [scriptblock]$ScriptBlock,
        [int]$MaxAttempts = 5,
        [int]$DelaySeconds = 3
    )
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            return & $ScriptBlock
        } catch {
            if ($i -eq $MaxAttempts) { throw }
            Write-Step "Attempt $i failed: $_  Retrying in ${DelaySeconds}s..." -Warn
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

# ---------------------------------------------------------------------------
# Environment file parser
# ---------------------------------------------------------------------------

function Import-EnvFile {
    <#
    .SYNOPSIS
        Parses a .env file (KEY=VALUE lines) and returns an ordered hashtable.
        Strips surrounding quotes, skips blank lines and comments.
    #>
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        throw "Env file not found: $Path"
    }
    $result = [ordered]@{}
    foreach ($line in Get-Content $Path) {
        $line = $line.Trim()
        if ($line -eq '' -or $line.StartsWith('#')) { continue }
        $eq = $line.IndexOf('=')
        if ($eq -lt 1) { continue }
        $key   = $line.Substring(0, $eq).Trim()
        $value = $line.Substring($eq + 1).Trim().Trim('"').Trim("'")
        $result[$key] = $value
    }
    return $result
}

# ---------------------------------------------------------------------------
# uv
# ---------------------------------------------------------------------------

function Find-Uv {
    param([string]$UvPath = '')
    $candidates = @(
        $UvPath,
        (Get-Command uv -ErrorAction SilentlyContinue)?.Source,
        "$env:USERPROFILE\.cargo\bin\uv.exe",
        "$env:LOCALAPPDATA\uv\uv.exe",
        "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_*\uv.exe"
    ) | Where-Object { $_ -and (Test-Path $_) }
    # @(...) keeps array context so a lone candidate isn't indexed char-wise.
    if ($candidates) { return @($candidates)[0] }
    return $null
}

function Install-Uv {
    Write-Step 'Installing uv via winget...'
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        # Pipe to Out-Null: winget's console output must not leak into the
        # function's output stream, or it pollutes the returned path.
        & winget install astral-sh.uv --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        $uv = Find-Uv
        if ($uv) { return $uv }
    }
    Write-Step 'winget not available or uv not found after winget; trying PowerShell installer...' -Warn
    # Ensure TLS 1.2 for corporate proxies
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-Expression (Invoke-WebRequest -UseBasicParsing https://astral.sh/uv/install.ps1).Content
    # Refresh PATH from registry
    $machinePath = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
    $userPath    = [Environment]::GetEnvironmentVariable('PATH', 'User')
    $env:PATH    = "$userPath;$machinePath"
    $uv = Find-Uv
    if (-not $uv) { throw 'uv installation failed. Install manually from https://docs.astral.sh/uv/' }
    return $uv
}

function Assert-PythonVersion {
    param([string]$UvExe, [string]$InstallDir)
    Write-Step 'Checking Python 3.13...'
    Push-Location $InstallDir
    try {
        $list = & $UvExe python list 2>&1 | Out-String
        if ($list -notmatch '3\.13') {
            Write-Step 'Python 3.13 not found; installing via uv...'
            & $UvExe python install '3.13'
        } else {
            Write-Step 'Python 3.13 available.' -Success
        }
    } finally {
        Pop-Location
    }
}

function Invoke-UvSync {
    param([string]$UvExe, [string]$InstallDir)
    Write-Step 'Running uv sync (api + app extras; importer workspace member)...'
    Push-Location $InstallDir
    try {
        & $UvExe sync --all-packages --extra api --extra app
        if ($LASTEXITCODE -ne 0) { throw "uv sync exited with code $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
    Write-Step 'uv sync complete.' -Success
}

# ---------------------------------------------------------------------------
# NSSM
# ---------------------------------------------------------------------------

function Find-Nssm {
    param([string]$NssmPath = '', [string]$InstallDir = '')
    $candidates = @(
        $NssmPath,
        (Get-Command nssm -ErrorAction SilentlyContinue)?.Source,
        "$InstallDir\tools\nssm\nssm.exe",
        'C:\nssm\nssm.exe',
        "$env:ProgramFiles\NSSM\nssm.exe"
    ) | Where-Object { $_ -and (Test-Path $_) }
    # @(...) keeps array context so a lone candidate isn't indexed char-wise.
    if ($candidates) { return @($candidates)[0] }
    return $null
}

function Install-Nssm {
    param([string]$InstallDir)
    Write-Step 'Installing NSSM via winget...'
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        # Pipe to Out-Null: winget's console output must not leak into the
        # function's output stream, or it pollutes the returned path.
        & winget install NSSM.NSSM --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        $nssm = Find-Nssm -InstallDir $InstallDir
        if ($nssm) { return $nssm }
    }
    Write-Step 'winget unavailable or NSSM not found; downloading nssm-2.24...' -Warn
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $zipUrl  = 'https://nssm.cc/release/nssm-2.24.zip'
    $zipPath = Join-Path $env:TEMP 'nssm-2.24.zip'
    $destDir = Join-Path $InstallDir 'tools\nssm'
    Invoke-WithRetry { Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing }
    Expand-Archive -Path $zipPath -DestinationPath (Join-Path $env:TEMP 'nssm-extract') -Force
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    Copy-Item (Join-Path $env:TEMP 'nssm-extract\nssm-2.24\win64\nssm.exe') -Destination $destDir -Force
    Remove-Item $zipPath, (Join-Path $env:TEMP 'nssm-extract') -Recurse -Force -ErrorAction SilentlyContinue
    $nssm = Join-Path $destDir 'nssm.exe'
    if (-not (Test-Path $nssm)) { throw 'NSSM installation failed. Download manually from https://nssm.cc/' }
    return $nssm
}

function Test-NssmServiceExists {
    param([string]$ServiceName)
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    return ($null -ne $svc)
}

function Install-NssmService {
    <#
    .SYNOPSIS
        Installs or fully reconfigures an NSSM-managed Windows service.
    #>
    param(
        [string]$NssmExe,
        [string]$ServiceName,
        [string]$Application,
        [string]$AppParameters,
        [string]$AppDirectory,
        [string]$DisplayName,
        [string]$Description,
        [string]$StdoutLog,
        [string]$StderrLog,
        [string]$ServiceUser     = 'LocalSystem',
        [string]$ServicePassword = '',
        [hashtable]$AppEnvironment = @{}
    )

    $exists = Test-NssmServiceExists -ServiceName $ServiceName

    if ($exists) {
        Write-Step "Service '$ServiceName' exists — stopping for reconfiguration..."
        $svcState = (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue)?.Status
        if ($svcState -eq 'Paused') {
            Resume-Service -Name $ServiceName -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
        & $NssmExe stop $ServiceName confirm 2>&1 | Out-Null
        Start-Sleep -Seconds 2
    } else {
        Write-Step "Installing service '$ServiceName'..."
        & $NssmExe install $ServiceName $Application $AppParameters
        if ($LASTEXITCODE -ne 0) { throw "nssm install '$ServiceName' failed." }
    }

    # Core config (applied whether new or updated)
    & $NssmExe set $ServiceName Application   $Application
    & $NssmExe set $ServiceName AppParameters $AppParameters
    & $NssmExe set $ServiceName AppDirectory  $AppDirectory
    & $NssmExe set $ServiceName DisplayName   $DisplayName
    & $NssmExe set $ServiceName Description   $Description
    & $NssmExe set $ServiceName Start         SERVICE_AUTO_START

    # Service account
    if ($ServiceUser -eq 'LocalSystem') {
        & $NssmExe set $ServiceName ObjectName LocalSystem
    } else {
        & $NssmExe set $ServiceName ObjectName $ServiceUser $ServicePassword
    }

    # Log routing (append mode)
    & $NssmExe set $ServiceName AppStdout                       $StdoutLog
    & $NssmExe set $ServiceName AppStderr                       $StderrLog
    & $NssmExe set $ServiceName AppStdoutCreationDisposition    4
    & $NssmExe set $ServiceName AppStderrCreationDisposition    4

    # Log rotation at 10 MB, while running
    & $NssmExe set $ServiceName AppRotateFiles  1
    & $NssmExe set $ServiceName AppRotateBytes  10485760
    & $NssmExe set $ServiceName AppRotateOnline 1

    # Restart policy: always restart, 3 s delay, 60 s throttle window
    & $NssmExe set $ServiceName AppExit         Default Restart
    & $NssmExe set $ServiceName AppRestartDelay 3000
    & $NssmExe set $ServiceName AppThrottle     60000

    # Extra environment variables
    if ($AppEnvironment.Count -gt 0) {
        $envString = ($AppEnvironment.GetEnumerator() |
            ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n"
        & $NssmExe set $ServiceName AppEnvironmentExtra $envString
    }

    Write-Step "Service '$ServiceName' configured." -Success
}

function Remove-NssmService {
    param([string]$NssmExe, [string]$ServiceName)
    if (Test-NssmServiceExists -ServiceName $ServiceName) {
        Write-Step "Removing service '$ServiceName'..."
        & $NssmExe stop   $ServiceName confirm 2>&1 | Out-Null
        & $NssmExe remove $ServiceName confirm
    }
}

function Start-ManagedService {
    param([string]$NssmExe, [string]$ServiceName, [int]$TimeoutSeconds = 30)
    Write-Step "Starting service '$ServiceName'..."
    & $NssmExe start $ServiceName 2>&1 | Out-Null
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($svc -and $svc.Status -eq 'Running') {
            Write-Step "Service '$ServiceName' is Running." -Success
            return
        }
        if ($svc -and $svc.Status -eq 'Paused') {
            Write-Step "Service '$ServiceName' is Paused — resuming..." -Warn
            Resume-Service -Name $ServiceName -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }
    throw "Service '$ServiceName' did not reach Running state within ${TimeoutSeconds}s."
}

function Stop-ManagedService {
    param([string]$NssmExe, [string]$ServiceName, [int]$TimeoutSeconds = 20)
    if (Test-NssmServiceExists -ServiceName $ServiceName) {
        & $NssmExe stop $ServiceName confirm 2>&1 | Out-Null
        $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
        while ((Get-Date) -lt $deadline) {
            $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
            if (-not $svc -or $svc.Status -eq 'Stopped') { return }
            Start-Sleep -Seconds 2
        }
    }
}

# ---------------------------------------------------------------------------
# nginx
# ---------------------------------------------------------------------------

function Find-Nginx {
    <#
    .SYNOPSIS
        Locates nginx.exe inside a per-environment prefix directory.
    .DESCRIPTION
        Only an explicit -NginxPath or the env-specific -NginxRoot is consulted;
        a globally installed nginx on PATH is deliberately ignored so that two
        environments on one host never share a single nginx.conf / runtime dir.
    #>
    param([string]$NginxPath = '', [string]$NginxRoot = '')
    $candidates = @(
        $NginxPath,
        $(if ($NginxRoot) { Join-Path $NginxRoot 'nginx.exe' })
    ) | Where-Object { $_ -and (Test-Path $_) }
    # @(...) keeps array context so a lone candidate isn't indexed char-wise.
    if ($candidates) { return @($candidates)[0] }
    return $null
}

function Install-Nginx {
    param([string]$DestDir)
    Write-Step 'Downloading nginx for Windows...'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    # Fetch the stable download page to discover the latest Windows zip filename
    $indexUrl  = 'https://nginx.org/en/download.html'
    $indexHtml = (Invoke-WithRetry { Invoke-WebRequest -Uri $indexUrl -UseBasicParsing }).Content
    # Match the latest stable Windows zip link, e.g. nginx-1.26.1.zip
    if ($indexHtml -match 'href="(/download/(nginx-[\d.]+\.zip))"') {
        $zipName = $matches[2]
        $zipUrl  = "https://nginx.org/download/$zipName"
    } else {
        # Fallback to a known-good version
        $zipName = 'nginx-1.26.2.zip'
        $zipUrl  = "https://nginx.org/download/$zipName"
    }
    $zipPath  = Join-Path $env:TEMP $zipName
    Invoke-WithRetry { Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing }
    $extractBase = Join-Path $env:TEMP 'nginx-extract'
    Expand-Archive -Path $zipPath -DestinationPath $extractBase -Force
    # The zip contains a single top-level directory (e.g. nginx-1.26.2)
    $extracted = Get-ChildItem $extractBase -Directory | Select-Object -First 1
    New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    Copy-Item "$($extracted.FullName)\*" -Destination $DestDir -Recurse -Force
    Remove-Item $zipPath, $extractBase -Recurse -Force -ErrorAction SilentlyContinue
    $nginx = Join-Path $DestDir 'nginx.exe'
    if (-not (Test-Path $nginx)) { throw 'nginx installation failed.' }
    return $nginx
}

function New-SelfSignedNginxCert {
    <#
    .SYNOPSIS
        Generates a self-signed TLS cert (cert.pem + key.pem) for nginx at
        $CertDir, if one isn't already there.
    .DESCRIPTION
        Uses the Windows PKI cmdlets + built-in .NET PEM export only — no
        openssl or other external tool required. The cert is created in the
        machine store just long enough to export it, then removed; the PEM
        files on disk are the only copy nginx (or anyone else) reads.
        Browsers will show an untrusted-certificate warning for this cert —
        that's expected for a self-signed staging/internal deployment.
    #>
    param(
        [Parameter(Mandatory)]
        [string]$CertDir,
        [Parameter(Mandatory)]
        [string]$CommonName,
        [int]$ValidityYears = 5
    )
    $certPath = Join-Path $CertDir 'cert.pem'
    $keyPath  = Join-Path $CertDir 'key.pem'

    if ((Test-Path $certPath) -and (Test-Path $keyPath)) {
        Write-Step "Self-signed cert already present at $CertDir — reusing." -Success
        return [pscustomobject]@{ CertPath = $certPath; KeyPath = $keyPath }
    }

    Write-Step "Generating self-signed cert for '$CommonName' (valid $ValidityYears years)..."
    New-Item -ItemType Directory -Path $CertDir -Force | Out-Null

    $cert = New-SelfSignedCertificate `
        -DnsName           $CommonName `
        -CertStoreLocation 'Cert:\LocalMachine\My' `
        -KeyExportPolicy   Exportable `
        -KeyAlgorithm      RSA `
        -KeyLength         2048 `
        -NotAfter          (Get-Date).AddYears($ValidityYears) `
        -FriendlyName      'open_datEAUbase self-signed (nginx)'

    try {
        $certPem = "-----BEGIN CERTIFICATE-----`n" +
            [Convert]::ToBase64String(
                $cert.Export([Security.Cryptography.X509Certificates.X509ContentType]::Cert),
                [Base64FormattingOptions]::InsertLineBreaks
            ) + "`n-----END CERTIFICATE-----"

        $rsa = $cert.GetRSAPrivateKey()
        $keyPem = "-----BEGIN PRIVATE KEY-----`n" +
            [Convert]::ToBase64String(
                $rsa.ExportPkcs8PrivateKey(),
                [Base64FormattingOptions]::InsertLineBreaks
            ) + "`n-----END PRIVATE KEY-----"

        Set-Content -Path $certPath -Value $certPem -Encoding ASCII
        Set-Content -Path $keyPath  -Value $keyPem  -Encoding ASCII
    } finally {
        # Exportable private key shouldn't linger in the machine store once
        # it's on disk as key.pem.
        Remove-Item -Path "Cert:\LocalMachine\My\$($cert.Thumbprint)" -Force -ErrorAction SilentlyContinue
    }

    Write-Step "Self-signed cert written to $CertDir." -Success
    return [pscustomobject]@{ CertPath = $certPath; KeyPath = $keyPath }
}

function Write-NginxConf {
    <#
    .SYNOPSIS
        Generates nginx.conf pointing logs to $LogDir\nginx\ and writing
        WebSocket-aware proxy rules for the Streamlit app and FastAPI, with the
        public server block terminating TLS via a self-signed cert.
    #>
    param(
        [string]$NginxDir,
        [string]$ApiPort,
        [string]$AppPort,
        [string]$ProxyPort,
        [string]$LogDir,
        [Parameter(Mandatory)]
        [string]$CertPath,
        [Parameter(Mandatory)]
        [string]$KeyPath,
        [string]$LogViewerPort = '',
        [string]$DocsPort = ''
    )
    # nginx requires forward slashes in paths
    $logDirFwd  = $LogDir.Replace('\', '/')
    $certPathFwd = $CertPath.Replace('\', '/')
    $keyPathFwd  = $KeyPath.Replace('\', '/')

    # Optional MkDocs site (mkdocs serve), exposed under /docs/. The trailing
    # slash on proxy_pass strips the /docs/ prefix because mkdocs serves at root.
    # WebSocket headers cover mkdocs' livereload; the site renders fine regardless.
    $docsBlock = ''
    if ($DocsPort) {
        $docsBlock = @"

        # MkDocs documentation site
        location = /docs { return 301 /docs/; }
        location /docs/ {
            proxy_pass         http://127.0.0.1:$DocsPort/;
            proxy_http_version 1.1;
            proxy_set_header   Upgrade `$http_upgrade;
            proxy_set_header   Connection "upgrade";
            proxy_set_header   Host `$host;
            proxy_set_header   X-Real-IP `$remote_addr;
        }
"@
    }

    # Optional OpenObserve log viewer block, exposed under /logs/ (set via
    # ZO_BASE_URI=/logs on the service). Uses the same WebSocket-upgrade headers
    # as the Streamlit block because OpenObserve's UI streams live tail over ws.
    $logViewerBlock = ''
    if ($LogViewerPort) {
        $logViewerBlock = @"

        # OpenObserve log viewer -- WebSocket upgrade for live tail
        location /logs/ {
            proxy_pass         http://127.0.0.1:$LogViewerPort;
            proxy_http_version 1.1;
            proxy_set_header   Upgrade `$http_upgrade;
            proxy_set_header   Connection "upgrade";
            proxy_set_header   Host `$host;
            proxy_set_header   X-Real-IP `$remote_addr;
            proxy_read_timeout 86400;
            proxy_buffering    off;
        }
"@
    }

    $conf = @"
worker_processes 1;

events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    # nginx defaults to 1M, which rejects real phone photos (lab image
    # uploads) with a bare 413 before Streamlit/FastAPI ever see the request.
    client_max_body_size 25M;

    # JSON access log with request/upstream timing, ingested by Vector ->
    # OpenObserve for the performance dashboard. upstream_* fields are quoted
    # because nginx writes '-' (or comma-joined values) when there's no upstream.
    log_format perf_json escape=json
        '{'
          '"time":"`$time_iso8601",'
          '"remote_addr":"`$remote_addr",'
          '"method":"`$request_method",'
          '"uri":"`$uri",'
          '"status":`$status,'
          '"body_bytes":`$body_bytes_sent,'
          '"request_time":`$request_time,'
          '"upstream_response_time":"`$upstream_response_time",'
          '"upstream_addr":"`$upstream_addr"'
        '}';

    access_log  $logDirFwd/nginx/access.log perf_json;
    error_log   $logDirFwd/nginx/error.log;

    # Streamlit app -- WebSocket upgrade required for live reactivity.
    # TLS-terminated with a self-signed cert (see New-SelfSignedNginxCert) —
    # browsers show an untrusted-certificate warning, which is expected.
    server {
        listen $ProxyPort ssl;

        ssl_certificate     $certPathFwd;
        ssl_certificate_key $keyPathFwd;

        location / {
            proxy_pass         http://127.0.0.1:$AppPort;
            proxy_http_version 1.1;
            proxy_set_header   Upgrade `$http_upgrade;
            proxy_set_header   Connection "upgrade";
            proxy_set_header   Host `$host;
            proxy_set_header   X-Real-IP `$remote_addr;
            proxy_read_timeout 86400;
            proxy_buffering    off;
        }

        # FastAPI REST API
        location /api/ {
            proxy_pass       http://127.0.0.1:$ApiPort/api/;
            proxy_set_header Host `$host;
            proxy_set_header X-Real-IP `$remote_addr;
        }
$docsBlock
$logViewerBlock
    }
}
"@

    $confPath = Join-Path $NginxDir 'conf\nginx.conf'
    New-Item -ItemType Directory -Path (Split-Path $confPath) -Force | Out-Null
    Set-Content -Path $confPath -Value $conf -Encoding UTF8
    Write-Step "nginx.conf written to $confPath" -Success
}

# ---------------------------------------------------------------------------
# OpenObserve (log viewer) + Vector (log shipper)
# ---------------------------------------------------------------------------

# Pinned fallbacks used only when the dynamic "latest release" lookup fails
# (e.g. offline GitHub, rate limit). Mirrors Install-Nginx's fallback approach.
$script:OpenObserveFallbackVersion = 'v0.14.4'
$script:VectorFallbackVersion      = '0.43.1'

function Find-OpenObserve {
    <#
    .SYNOPSIS
        Locates openobserve.exe inside a per-host tools directory.
    #>
    param([string]$OpenObservePath = '', [string]$DestDir = '')
    $candidates = @(
        $OpenObservePath,
        $(if ($DestDir) { Join-Path $DestDir 'openobserve.exe' })
    ) | Where-Object { $_ -and (Test-Path $_) }
    # @(...) keeps array context so a lone candidate isn't indexed char-wise.
    if ($candidates) { return @($candidates)[0] }
    return $null
}

function Install-OpenObserve {
    <#
    .SYNOPSIS
        Downloads + extracts the OpenObserve Windows amd64 zip into $DestDir.
    .DESCRIPTION
        Tries the GitHub "latest release" API to discover the current
        windows-amd64 asset, falling back to a pinned known-good version.
        Mirrors Install-Nginx's TLS-1.2 + Invoke-WebRequest + Expand-Archive flow.
    #>
    param([string]$DestDir)
    Write-Step 'Downloading OpenObserve (log viewer) for Windows...'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    $zipUrl = $null
    try {
        $rel = Invoke-RestMethod -Uri 'https://api.github.com/repos/openobserve/openobserve/releases/latest' `
            -Headers @{ 'User-Agent' = 'open-dateaubase-deploy' } -UseBasicParsing
        $asset = $rel.assets | Where-Object { $_.name -match 'windows-amd64\.zip$' } | Select-Object -First 1
        if ($asset) { $zipUrl = $asset.browser_download_url }
    } catch {
        Write-Step "OpenObserve latest-release lookup failed ($_); using pinned $($script:OpenObserveFallbackVersion)." -Warn
    }
    if (-not $zipUrl) {
        $v = $script:OpenObserveFallbackVersion
        $zipUrl = "https://github.com/openobserve/openobserve/releases/download/$v/openobserve-$v-windows-amd64.zip"
    }

    $zipPath     = Join-Path $env:TEMP 'openobserve-windows.zip'
    $extractBase = Join-Path $env:TEMP 'openobserve-extract'
    Invoke-WithRetry { Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing }
    if (Test-Path $extractBase) { Remove-Item $extractBase -Recurse -Force }
    Expand-Archive -Path $zipPath -DestinationPath $extractBase -Force
    $exe = Get-ChildItem $extractBase -Recurse -Filter 'openobserve.exe' | Select-Object -First 1
    if (-not $exe) { throw 'OpenObserve installation failed: openobserve.exe not found in archive.' }
    New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    Copy-Item $exe.FullName -Destination $DestDir -Force
    Remove-Item $zipPath, $extractBase -Recurse -Force -ErrorAction SilentlyContinue
    $dest = Join-Path $DestDir 'openobserve.exe'
    if (-not (Test-Path $dest)) { throw 'OpenObserve installation failed.' }
    Write-Step "OpenObserve installed: $dest" -Success
    return $dest
}

function Find-Vector {
    <#
    .SYNOPSIS
        Locates vector.exe inside a per-host tools directory.
    #>
    param([string]$VectorPath = '', [string]$DestDir = '')
    $candidates = @(
        $VectorPath,
        $(if ($DestDir) { Join-Path $DestDir 'vector.exe' })
    ) | Where-Object { $_ -and (Test-Path $_) }
    # @(...) keeps array context so a lone candidate isn't indexed char-wise.
    if ($candidates) { return @($candidates)[0] }
    return $null
}

function Install-Vector {
    <#
    .SYNOPSIS
        Downloads + extracts the Vector Windows (msvc) zip into $DestDir.
    .DESCRIPTION
        Tries the GitHub "latest release" API to discover the current
        x86_64-pc-windows-msvc asset, falling back to a pinned known-good version.
    #>
    param([string]$DestDir)
    Write-Step 'Downloading Vector (log shipper) for Windows...'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    $zipUrl = $null
    try {
        $rel = Invoke-RestMethod -Uri 'https://api.github.com/repos/vectordotdev/vector/releases/latest' `
            -Headers @{ 'User-Agent' = 'open-dateaubase-deploy' } -UseBasicParsing
        $asset = $rel.assets | Where-Object { $_.name -match 'x86_64-pc-windows-msvc\.zip$' } | Select-Object -First 1
        if ($asset) { $zipUrl = $asset.browser_download_url }
    } catch {
        Write-Step "Vector latest-release lookup failed ($_); using pinned $($script:VectorFallbackVersion)." -Warn
    }
    if (-not $zipUrl) {
        $v = $script:VectorFallbackVersion
        $zipUrl = "https://github.com/vectordotdev/vector/releases/download/v$v/vector-$v-x86_64-pc-windows-msvc.zip"
    }

    $zipPath     = Join-Path $env:TEMP 'vector-windows.zip'
    $extractBase = Join-Path $env:TEMP 'vector-extract'
    Invoke-WithRetry { Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing }
    if (Test-Path $extractBase) { Remove-Item $extractBase -Recurse -Force }
    Expand-Archive -Path $zipPath -DestinationPath $extractBase -Force
    $exe = Get-ChildItem $extractBase -Recurse -Filter 'vector.exe' | Select-Object -First 1
    if (-not $exe) { throw 'Vector installation failed: vector.exe not found in archive.' }
    New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    Copy-Item $exe.FullName -Destination $DestDir -Force
    Remove-Item $zipPath, $extractBase -Recurse -Force -ErrorAction SilentlyContinue
    $dest = Join-Path $DestDir 'vector.exe'
    if (-not (Test-Path $dest)) { throw 'Vector installation failed.' }
    Write-Step "Vector installed: $dest" -Success
    return $dest
}

function Write-VectorConfig {
    <#
    .SYNOPSIS
        Generates vector.toml: tails the four per-service log sub-dirs, tags each
        record with environment/service, merges multi-line Python tracebacks, and
        ships to OpenObserve's _json HTTP endpoint with basic auth + gzip.
    #>
    param(
        [string]$OutPath,
        [string]$LogDir,
        [string]$Environment,
        [string]$ViewerPort,
        [string]$Org      = 'default',
        [string]$Stream   = 'open_dateaubase',
        [string]$User,
        [string]$Password,
        [string]$DataDir  = ''
    )
    # Vector accepts forward slashes on Windows; avoids TOML escaping headaches.
    $logDirFwd = $LogDir.Replace('\', '/')
    if (-not $DataDir) { $DataDir = Join-Path (Split-Path $OutPath) 'data' }
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    $dataDirFwd = $DataDir.Replace('\', '/')

    $toml = @"
# Generated by Deploy-OpenDateaubase.ps1 -- do not edit by hand.
# Tails $logDirFwd/{api,app,nginx,importer}/*.log and ships to OpenObserve.
data_dir = "$dataDirFwd"

[sources.open_dateaubase_logs]
type = "file"
read_from = "beginning"
include = [
  "$logDirFwd/api/*.log",
  "$logDirFwd/app/*.log",
  "$logDirFwd/nginx/*.log",
  "$logDirFwd/importer/*.log",
]

# Merge continuation lines (Python tracebacks, etc.) into the preceding
# log entry: a new event starts only on a leading timestamp, nginx bracket/IP
# prefix, '{' (JSON perf records from the API and nginx), or a uvicorn/logging
# level prefix. The level prefixes are essential: without them a uvicorn
# "INFO: ... GET ... 200 OK" access line gets merged onto the preceding JSON
# perf line, corrupting it so parse_json fails and duration_ms is never hoisted.
[sources.open_dateaubase_logs.multiline]
start_pattern = '^(\d{4}-\d{2}-\d{2}|\[\d|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|\{|INFO:|WARNING:|ERROR:|DEBUG:|CRITICAL:)'
mode = "halt_before"
condition_pattern = '^(\d{4}-\d{2}-\d{2}|\[\d|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|\{|INFO:|WARNING:|ERROR:|DEBUG:|CRITICAL:)'
timeout_ms = 1000

[transforms.tag]
type = "remap"
inputs = ["open_dateaubase_logs"]
source = '''
.environment = "$Environment"
.service = "unknown"
matched = parse_regex(.file, r'[\\/](?P<svc>[^\\/]+)[\\/][^\\/]+$') ?? {}
if is_string(matched.svc) {
    .service = matched.svc
}
# Hoist structured JSON log lines (API request-timing records and nginx
# perf_json access logs) to top-level fields so duration_ms / request_time /
# status / route become queryable columns. Non-JSON lines pass through.
parsed = parse_json(.message) ?? null
if is_object(parsed) {
    . = merge(., object!(parsed))
}
'''

[sinks.openobserve]
type = "http"
inputs = ["tag"]
# ZO_BASE_URI=/logs relocates every OpenObserve route, including ingestion, under that prefix.
uri = "http://127.0.0.1:$ViewerPort/logs/api/$Org/$Stream/_json"
method = "post"
compression = "gzip"

[sinks.openobserve.encoding]
codec = "json"

[sinks.openobserve.request.headers]
Content-Type = "application/json"

[sinks.openobserve.auth]
strategy = "basic"
user = "$User"
password = "$Password"
"@

    New-Item -ItemType Directory -Path (Split-Path $OutPath) -Force | Out-Null
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    Set-Content -Path $OutPath -Value $toml -Encoding UTF8
    Write-Step "vector.toml written to $OutPath" -Success
}

# ---------------------------------------------------------------------------
# OpenObserve dashboard provisioning
# ---------------------------------------------------------------------------

function Publish-OpenObserveDashboard {
    <#
    .SYNOPSIS
        Creates or updates an OpenObserve dashboard from an exported dashboard
        JSON file (Dashboards > ... > Export in the OpenObserve UI). Matches
        existing dashboards by title so re-running is idempotent: updates in
        place rather than creating a duplicate.
    #>
    param(
        [string]$ViewerPort,
        [string]$User,
        [string]$Password,
        [string]$TemplatePath,
        [string]$Org = 'default'
    )
    if (-not (Test-Path $TemplatePath)) {
        throw "Dashboard template not found: $TemplatePath"
    }

    $cred = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("${User}:${Password}"))
    $headers = @{ Authorization = "Basic $cred"; 'Content-Type' = 'application/json' }
    $base = "http://127.0.0.1:$ViewerPort/logs/api/$Org/dashboards"

    $template = Get-Content $TemplatePath -Raw | ConvertFrom-Json
    $template.owner = $User
    $title = $template.title

    $existing = Invoke-RestMethod -Uri $base -Headers $headers -Method Get
    $match = $existing.dashboards | Where-Object { $_.v5.title -eq $title -or $_.v1.title -eq $title } | Select-Object -First 1

    $body = $template | ConvertTo-Json -Depth 30
    if ($match) {
        $dashId = if ($match.v5) { $match.v5.dashboardId } else { $match.v1.dashboardId }
        $current = Invoke-RestMethod -Uri "$base/$dashId" -Headers $headers -Method Get
        $hash = if ($current.v5) { $current.hash } else { $current.hash }
        Invoke-RestMethod -Uri "$base/$dashId`?hash=$hash" -Headers $headers -Method Put -Body $body | Out-Null
        Write-Step "Dashboard '$title' updated." -Success
    } else {
        Invoke-RestMethod -Uri $base -Headers $headers -Method Post -Body $body | Out-Null
        Write-Step "Dashboard '$title' created." -Success
    }
}

# ---------------------------------------------------------------------------
# Importer launcher
# ---------------------------------------------------------------------------

function Write-ImporterCmd {
    <#
    .SYNOPSIS
        Generates the run-importer.cmd wrapper used by Task Scheduler.
        Appends stdout/stderr to log files supplied via %LOG_STDOUT% / %LOG_STDERR%.

        $ImporterConfig may be a single YAML file (--config) or a directory of
        YAML files (--config-dir); the flag is chosen automatically.
    #>
    param(
        [string]$UvExe,
        [string]$InstallDir,
        [string]$ImporterConfig,
        [string]$OutPath,           # full path for the .cmd file
        [string]$ApiServiceToken = '',  # bearer token for the secured API
        [int]$MaxSeconds = 0          # importer self-timeout; 0 = no limit
    )
    # The API now requires auth; the importer authenticates with the shared
    # service token, passed via the environment of the Scheduled Task process.
    $tokenLine = if ($ApiServiceToken) { "set `"API_SERVICE_TOKEN=$ApiServiceToken`"" } else { '' }

    # Wall-clock budget so the importer stops gracefully *before* the Scheduled
    # Task ExecutionTimeLimit force-kills it (which leaves a zombie 'Running'
    # task). It ingests what it has and the next run resumes.
    $maxLine = if ($MaxSeconds -gt 0) { "set `"IMPORTER_MAX_SECONDS=$MaxSeconds`"" } else { '' }

    # Choose --config (file) or --config-dir (directory) automatically.
    $configFlag = if (Test-Path $ImporterConfig -PathType Container) { '--config-dir' } else { '--config' }

    $cmd = @"
@echo off
cd /d "$InstallDir"
$tokenLine
$maxLine
"$UvExe" run --package table-import python -m table_import import $configFlag "$ImporterConfig" >>%LOG_STDOUT% 2>>%LOG_STDERR%
"@
    New-Item -ItemType Directory -Path (Split-Path $OutPath) -Force | Out-Null
    Set-Content -Path $OutPath -Value $cmd -Encoding ASCII
    Write-Step "run-importer.cmd written to $OutPath ($configFlag)" -Success
}

# ---------------------------------------------------------------------------
# Log directory
# ---------------------------------------------------------------------------

function Initialize-LogStructure {
    param(
        [string]$LogDir,
        [string]$ServiceUser = 'LocalSystem'
    )
    Write-Step "Creating log directory structure under $LogDir..."
    $services = 'api', 'app', 'docs', 'nginx', 'importer', 'logviewer', 'logship'
    foreach ($svc in $services) {
        $dir = Join-Path $LogDir $svc
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        foreach ($f in 'stdout.log', 'stderr.log') {
            $file = Join-Path $dir $f
            if (-not (Test-Path $file)) { New-Item -ItemType File -Path $file -Force | Out-Null }
        }
    }
    # nginx also needs access.log and error.log pre-created
    foreach ($f in 'access.log', 'error.log') {
        $file = Join-Path $LogDir "nginx\$f"
        if (-not (Test-Path $file)) { New-Item -ItemType File -Path $file -Force | Out-Null }
    }

    # Grant Full Control to the service account
    $identity = if ($ServiceUser -eq 'LocalSystem') { 'NT AUTHORITY\SYSTEM' } else { $ServiceUser }
    try {
        $acl = Get-Acl $LogDir
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $identity,
            'FullControl',
            'ContainerInherit,ObjectInherit',
            'None',
            'Allow'
        )
        $acl.SetAccessRule($rule)
        Set-Acl -Path $LogDir -AclObject $acl
        Write-Step "ACL set: $identity has FullControl on $LogDir" -Success
    } catch {
        Write-Step "Could not set ACL on $LogDir (non-fatal): $_" -Warn
    }
}

# ---------------------------------------------------------------------------
# Task Scheduler: importer
# ---------------------------------------------------------------------------

function Test-ImporterTaskExists {
    param([string]$TaskName)
    return ($null -ne (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue))
}

function Register-ImporterTask {
    param(
        [string]$TaskName,
        [string]$CmdPath,
        [string]$InstallDir,
        [string]$LogDir,
        [int]$IntervalMinutes,
        # Max wall-clock time before the task is killed. Defaults to IntervalMinutes - 1
        # so a single-source run can never bleed into the next trigger. When using
        # --config-dir with many sources, pass a larger value (e.g. IntervalMinutes * 3).
        [int]$ExecutionTimeLimitMinutes = -1,
        [string]$ServiceUser     = 'LocalSystem',
        [string]$ServicePassword = ''
    )
    if ($ExecutionTimeLimitMinutes -lt 0) {
        $ExecutionTimeLimitMinutes = [Math]::Max(1, $IntervalMinutes - 1)
    }
    Write-Step "Registering scheduled task '$TaskName' (every $IntervalMinutes min, limit $ExecutionTimeLimitMinutes min)..."

    if (Test-ImporterTaskExists -TaskName $TaskName) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    $stdoutLog = "$LogDir\importer\stdout.log"
    $stderrLog = "$LogDir\importer\stderr.log"

    # Inject log paths as env vars into the cmd invocation via a wrapper argument
    $argument = "/c set LOG_STDOUT=$stdoutLog&& set LOG_STDERR=$stderrLog&& `"$CmdPath`""

    $action = New-ScheduledTaskAction `
        -Execute    'cmd.exe' `
        -Argument   $argument `
        -WorkingDirectory $InstallDir

    $trigger = New-ScheduledTaskTrigger `
        -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
        -Once `
        -At (Get-Date)

    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit  (New-TimeSpan -Minutes $ExecutionTimeLimitMinutes) `
        -MultipleInstances   IgnoreNew `
        -RestartCount        1 `
        -RestartInterval     (New-TimeSpan -Minutes 1) `
        -StartWhenAvailable

    $principal = if ($ServiceUser -eq 'LocalSystem') {
        New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    } else {
        New-ScheduledTaskPrincipal -UserId $ServiceUser -Password $ServicePassword -LogonType Password -RunLevel Highest
    }

    Register-ScheduledTask `
        -TaskName  $TaskName `
        -Action    $action `
        -Trigger   $trigger `
        -Settings  $settings `
        -Principal $principal `
        -Force -ErrorAction Stop | Out-Null

    Write-Step "Scheduled task '$TaskName' registered." -Success
}

function Remove-ImporterTask {
    param([string]$TaskName)
    if (Test-ImporterTaskExists -TaskName $TaskName) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Step "Scheduled task '$TaskName' removed."
    }
}

function Register-LogRotateTask {
    <#
    .SYNOPSIS
        Registers a daily 02:00 task that archives importer logs larger than 10 MB.
    #>
    param(
        [string]$LogDir,
        [string]$TaskName        = 'OpenDateaubase-LogRotate',
        [string]$ServiceUser     = 'LocalSystem',
        [string]$ServicePassword = ''
    )
    $taskName = $TaskName

    if (Test-ImporterTaskExists -TaskName $taskName) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }

    $rotateScript = @"
`$dir = '$LogDir\importer'
foreach (`$log in Get-ChildItem `$dir -Filter '*.log') {
    if (`$log.Length -gt 10MB) {
        `$archive = `$log.FullName + '.' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.gz'
        `$src = `$log.FullName; `$dst = `$archive
        try {
            `$in  = [IO.File]::OpenRead(`$src)
            `$out = [IO.File]::Create(`$dst)
            `$gz  = New-Object IO.Compression.GZipStream(`$out, [IO.Compression.CompressionMode]::Compress)
            `$in.CopyTo(`$gz)
            `$gz.Close(); `$out.Close(); `$in.Close()
            Clear-Content `$log.FullName
        } catch {}
    }
}
"@

    $encodedScript = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($rotateScript))
    $action = New-ScheduledTaskAction `
        -Execute   'powershell.exe' `
        -Argument  "-NoProfile -NonInteractive -EncodedCommand $encodedScript"

    $trigger = New-ScheduledTaskTrigger -Daily -At '02:00'

    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
        -MultipleInstances  IgnoreNew

    $principal = if ($ServiceUser -eq 'LocalSystem') {
        New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    } else {
        New-ScheduledTaskPrincipal -UserId $ServiceUser -Password $ServicePassword -LogonType Password -RunLevel Highest
    }

    Register-ScheduledTask `
        -TaskName  $taskName `
        -Action    $action `
        -Trigger   $trigger `
        -Settings  $settings `
        -Principal $principal `
        -Force -ErrorAction Stop | Out-Null

    Write-Step "Log-rotation task '$taskName' registered (daily 02:00)." -Success
}

# ---------------------------------------------------------------------------
# Windows Firewall
# ---------------------------------------------------------------------------

function Set-AppFirewallRule {
    <#
    .SYNOPSIS
        Ensures an inbound-allow firewall rule exists for the given TCP port,
        so LAN clients (not just localhost) can reach the nginx proxy.
    #>
    param(
        [string]$DisplayName,
        [int]$Port
    )
    if (Get-NetFirewallRule -DisplayName $DisplayName -ErrorAction SilentlyContinue) {
        Set-NetFirewallRule -DisplayName $DisplayName -Enabled True -Action Allow -Profile Any | Out-Null
        Write-Step "Firewall rule '$DisplayName' already present (TCP $Port) — ensured enabled." -Success
    } else {
        New-NetFirewallRule -DisplayName $DisplayName -Direction Inbound -Action Allow `
            -Protocol TCP -LocalPort $Port -Profile Any | Out-Null
        Write-Step "Firewall rule '$DisplayName' created (inbound TCP $Port)." -Success
    }
}

function Remove-AppFirewallRule {
    param([string]$DisplayName)
    if (Get-NetFirewallRule -DisplayName $DisplayName -ErrorAction SilentlyContinue) {
        Remove-NetFirewallRule -DisplayName $DisplayName
        Write-Step "Firewall rule '$DisplayName' removed."
    }
}

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

function Test-HttpEndpoint {
    param([string]$Url, [int]$TimeoutSec = 10, [switch]$SkipCertCheck)
    # Self-signed proxy cert: the deploy script's own health probe needs to
    # accept it. Scoped to this call only, restored in `finally` either way.
    $prevCallback = [Net.ServicePointManager]::ServerCertificateValidationCallback
    if ($SkipCertCheck) {
        [Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
    }
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
        return ($response.StatusCode -eq 200)
    } catch {
        return $false
    } finally {
        if ($SkipCertCheck) {
            [Net.ServicePointManager]::ServerCertificateValidationCallback = $prevCallback
        }
    }
}

function Assert-ServiceHealthy {
    param(
        [string]$Url,
        [int]$TimeoutSec  = 30,
        [int]$RetryDelaySec = 3,
        [switch]$SkipCertCheck
    )
    Write-Step "Health-checking $Url (up to ${TimeoutSec}s)..."
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpEndpoint -Url $Url -TimeoutSec 5 -SkipCertCheck:$SkipCertCheck) {
            Write-Step "$Url responded HTTP 200." -Success
            return
        }
        Start-Sleep -Seconds $RetryDelaySec
    }
    throw "Health check failed: $Url did not respond within ${TimeoutSec}s."
}

Export-ModuleMember -Function *
