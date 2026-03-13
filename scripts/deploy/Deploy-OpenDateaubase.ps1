#Requires -RunAsAdministrator
#Requires -Version 5.1
<#
.SYNOPSIS
    Deploy open_datEAUbase on a Windows Server.

.DESCRIPTION
    Installs Python 3.13 via uv, sets up the REST API and Streamlit app as
    auto-starting Windows Services (via NSSM), the table importer as a Windows
    Scheduled Task, and nginx as a reverse proxy service.

    Re-running the script is safe: existing services are reconfigured in place.

.PARAMETER InstallDir
    Root directory of the cloned repository (e.g. C:\open_dateaubase).

.PARAMETER LogDir
    Centralised log directory (e.g. C:\Logs\open_dateaubase).
    Created automatically if it does not exist.

.PARAMETER EnvFile
    Absolute path to the .env file containing DB_HOST, DB_PORT, DB_NAME,
    DB_USER, DB_PASSWORD, DB_DRIVER (and optionally API_BASE_URL).

.PARAMETER ImporterConfig
    Absolute path to the importer YAML config file.

.PARAMETER ImporterIntervalMinutes
    How often the importer Scheduled Task runs (default: 5).

.PARAMETER UvPath
    Full path to uv.exe. Auto-detected if omitted.

.PARAMETER NssmPath
    Full path to nssm.exe. Auto-detected or installed if omitted.

.PARAMETER NginxPath
    Full path to nginx.exe. Auto-detected or installed if omitted.

.PARAMETER ApiPort
    Port for the FastAPI/uvicorn service (default: 8000).

.PARAMETER AppPort
    Port for the Streamlit app (default: 8501).

.PARAMETER ProxyPort
    Port nginx listens on for browser traffic (default: 80).

.PARAMETER ServiceUser
    Windows account to run services under (default: LocalSystem).

.PARAMETER ServicePassword
    Password for ServiceUser. Leave empty for LocalSystem.

.PARAMETER SkipApi
    Do not deploy/update the API service.

.PARAMETER SkipApp
    Do not deploy/update the Streamlit app service.

.PARAMETER SkipImporter
    Do not register/update the importer Scheduled Task.

.PARAMETER SkipProxy
    Do not deploy/update the nginx proxy service.

.PARAMETER Uninstall
    Stop and remove all services and scheduled tasks.

.EXAMPLE
    .\Deploy-OpenDateaubase.ps1 `
        -InstallDir   C:\open_dateaubase `
        -LogDir       C:\Logs\open_dateaubase `
        -EnvFile      C:\open_dateaubase\.env.production `
        -ImporterConfig C:\open_dateaubase\config\import.yaml

.EXAMPLE
    # Redeploy only the API after a code update:
    .\Deploy-OpenDateaubase.ps1 -InstallDir C:\open_dateaubase -LogDir C:\Logs\open_dateaubase `
        -EnvFile C:\open_dateaubase\.env.production -ImporterConfig C:\open_dateaubase\config\import.yaml `
        -SkipApp -SkipImporter -SkipProxy

.EXAMPLE
    # Tear everything down:
    .\Deploy-OpenDateaubase.ps1 -InstallDir C:\open_dateaubase -LogDir C:\Logs\open_dateaubase `
        -EnvFile C:\open_dateaubase\.env.production -ImporterConfig C:\open_dateaubase\config\import.yaml `
        -Uninstall
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path $_ -PathType Container })]
    [string]$InstallDir,

    [Parameter(Mandatory)]
    [string]$LogDir,

    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path $_ -PathType Leaf })]
    [string]$EnvFile,

    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path $_ -PathType Leaf })]
    [string]$ImporterConfig,

    [ValidateRange(1, 1440)]
    [int]$ImporterIntervalMinutes = 5,

    [string]$UvPath          = '',
    [string]$NssmPath        = '',
    [string]$NginxPath       = '',

    [string]$ApiPort         = '8000',
    [string]$AppPort         = '8501',
    [string]$ProxyPort       = '80',

    [string]$ServiceUser     = 'LocalSystem',
    [string]$ServicePassword = '',

    [switch]$SkipApi,
    [switch]$SkipApp,
    [switch]$SkipImporter,
    [switch]$SkipProxy,
    [switch]$Uninstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

# Ensure log dir exists before starting transcript
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$transcriptPath = Join-Path $LogDir "deploy-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
Start-Transcript -Path $transcriptPath -Append | Out-Null

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDir 'DeployHelpers.psm1') -Force

Write-Step '================================================='
Write-Step ' open_datEAUbase Windows Deployment'
Write-Step "  InstallDir : $InstallDir"
Write-Step "  LogDir     : $LogDir"
Write-Step "  EnvFile    : $EnvFile"
Write-Step "  Importer   : $ImporterConfig (every $ImporterIntervalMinutes min)"
Write-Step '================================================='

# Service names (constants)
$SVC_API      = 'OpenDateaubase-API'
$SVC_APP      = 'OpenDateaubase-App'
$SVC_PROXY    = 'OpenDateaubase-Proxy'
$TASK_IMPORT  = 'OpenDateaubase-Importer'
$CMD_PATH     = Join-Path $scriptDir 'run-importer.cmd'

# ---------------------------------------------------------------------------
# Uninstall mode
# ---------------------------------------------------------------------------

if ($Uninstall) {
    Write-Step 'Uninstall mode — removing all services and tasks...'
    $nssmExe = Find-Nssm -NssmPath $NssmPath -InstallDir $InstallDir
    if ($nssmExe) {
        Remove-NssmService -NssmExe $nssmExe -ServiceName $SVC_PROXY
        Remove-NssmService -NssmExe $nssmExe -ServiceName $SVC_APP
        Remove-NssmService -NssmExe $nssmExe -ServiceName $SVC_API
    }
    Remove-ImporterTask -TaskName $TASK_IMPORT
    Remove-ImporterTask -TaskName 'OpenDateaubase-LogRotate'
    Write-Step 'Uninstall complete.' -Success
    Stop-Transcript | Out-Null
    exit 0
}

# ---------------------------------------------------------------------------
# Step 1: Locate / install uv
# ---------------------------------------------------------------------------

Write-Step 'Locating uv...'
$uvExe = Find-Uv -UvPath $UvPath
if (-not $uvExe) {
    $uvExe = Install-Uv
}
Write-Step "uv found: $uvExe" -Success

# ---------------------------------------------------------------------------
# Step 2: Verify Python 3.13
# ---------------------------------------------------------------------------

Assert-PythonVersion -UvExe $uvExe -InstallDir $InstallDir

# ---------------------------------------------------------------------------
# Step 3: Install Python dependencies
# ---------------------------------------------------------------------------

Invoke-UvSync -UvExe $uvExe -InstallDir $InstallDir

# ---------------------------------------------------------------------------
# Step 4: Locate / install NSSM
# ---------------------------------------------------------------------------

Write-Step 'Locating NSSM...'
$nssmExe = Find-Nssm -NssmPath $NssmPath -InstallDir $InstallDir
if (-not $nssmExe) {
    $nssmExe = Install-Nssm -InstallDir $InstallDir
}
Write-Step "NSSM found: $nssmExe" -Success

# ---------------------------------------------------------------------------
# Step 5: Locate / install nginx
# ---------------------------------------------------------------------------

if (-not $SkipProxy) {
    Write-Step 'Locating nginx...'
    $nginxExe = Find-Nginx -NginxPath $NginxPath -InstallDir $InstallDir
    if (-not $nginxExe) {
        $nginxExe = Install-Nginx -InstallDir $InstallDir
    }
    Write-Step "nginx found: $nginxExe" -Success
}

# ---------------------------------------------------------------------------
# Step 6: Create log directory structure
# ---------------------------------------------------------------------------

Initialize-LogStructure -LogDir $LogDir -ServiceUser $ServiceUser

# ---------------------------------------------------------------------------
# Step 7: Deploy REST API service
# ---------------------------------------------------------------------------

if (-not $SkipApi) {
    Write-Step 'Deploying API service...'
    $envVars = Import-EnvFile -Path $EnvFile
    $envVars['PYTHONUNBUFFERED'] = '1'

    Install-NssmService `
        -NssmExe         $nssmExe `
        -ServiceName     $SVC_API `
        -Application     $uvExe `
        -AppParameters   "run uvicorn api.main:app --host 0.0.0.0 --port $ApiPort" `
        -AppDirectory    $InstallDir `
        -DisplayName     'open_datEAUbase REST API' `
        -Description     'FastAPI/uvicorn REST API for open_datEAUbase' `
        -StdoutLog       (Join-Path $LogDir 'api\stdout.log') `
        -StderrLog       (Join-Path $LogDir 'api\stderr.log') `
        -ServiceUser     $ServiceUser `
        -ServicePassword $ServicePassword `
        -AppEnvironment  $envVars

    Start-ManagedService -NssmExe $nssmExe -ServiceName $SVC_API
    Assert-ServiceHealthy -Url "http://localhost:$ApiPort/" -TimeoutSec 30
}

# ---------------------------------------------------------------------------
# Step 8: Deploy Streamlit app service
# ---------------------------------------------------------------------------

if (-not $SkipApp) {
    Write-Step 'Deploying Streamlit app service...'
    $appEnv = [ordered]@{
        API_BASE_URL     = "http://localhost:$ApiPort/api/v1"
        PYTHONUNBUFFERED = '1'
    }

    Install-NssmService `
        -NssmExe         $nssmExe `
        -ServiceName     $SVC_APP `
        -Application     $uvExe `
        -AppParameters   "run streamlit run app/Home.py --server.port=$AppPort --server.address=0.0.0.0 --server.headless=true" `
        -AppDirectory    $InstallDir `
        -DisplayName     'open_datEAUbase Web App' `
        -Description     'Streamlit web UI for open_datEAUbase' `
        -StdoutLog       (Join-Path $LogDir 'app\stdout.log') `
        -StderrLog       (Join-Path $LogDir 'app\stderr.log') `
        -ServiceUser     $ServiceUser `
        -ServicePassword $ServicePassword `
        -AppEnvironment  $appEnv

    Start-ManagedService -NssmExe $nssmExe -ServiceName $SVC_APP
    # Streamlit can take a moment to bind; give it a softer check
    Write-Step "Streamlit app started (access via http://localhost:$AppPort once proxy is up)." -Success
}

# ---------------------------------------------------------------------------
# Step 9: Register importer Scheduled Task
# ---------------------------------------------------------------------------

if (-not $SkipImporter) {
    Write-Step 'Setting up table importer Scheduled Task...'

    Write-ImporterCmd `
        -UvExe         $uvExe `
        -InstallDir    $InstallDir `
        -ImporterConfig $ImporterConfig `
        -OutPath       $CMD_PATH

    Register-ImporterTask `
        -TaskName        $TASK_IMPORT `
        -CmdPath         $CMD_PATH `
        -InstallDir      $InstallDir `
        -LogDir          $LogDir `
        -IntervalMinutes $ImporterIntervalMinutes `
        -ServiceUser     $ServiceUser `
        -ServicePassword $ServicePassword

    Register-LogRotateTask `
        -LogDir          $LogDir `
        -ServiceUser     $ServiceUser `
        -ServicePassword $ServicePassword
}

# ---------------------------------------------------------------------------
# Step 10: Deploy nginx reverse proxy service
# ---------------------------------------------------------------------------

if (-not $SkipProxy) {
    Write-Step 'Deploying nginx reverse proxy...'
    $nginxDir = Split-Path -Parent $nginxExe

    Write-NginxConf `
        -NginxDir  $nginxDir `
        -ApiPort   $ApiPort `
        -AppPort   $AppPort `
        -ProxyPort $ProxyPort `
        -LogDir    $LogDir

    Install-NssmService `
        -NssmExe         $nssmExe `
        -ServiceName     $SVC_PROXY `
        -Application     $nginxExe `
        -AppParameters   "-p `"$nginxDir`"" `
        -AppDirectory    $nginxDir `
        -DisplayName     'open_datEAUbase Proxy (nginx)' `
        -Description     'nginx reverse proxy for open_datEAUbase (port 80 → Streamlit / API)' `
        -StdoutLog       (Join-Path $LogDir 'nginx\stdout.log') `
        -StderrLog       (Join-Path $LogDir 'nginx\stderr.log') `
        -ServiceUser     $ServiceUser `
        -ServicePassword $ServicePassword

    Start-ManagedService -NssmExe $nssmExe -ServiceName $SVC_PROXY
    Assert-ServiceHealthy -Url "http://localhost:$ProxyPort/" -TimeoutSec 15
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host ''
Write-Host '=================================================================' -ForegroundColor White
Write-Host ' Deployment Summary' -ForegroundColor White
Write-Host '=================================================================' -ForegroundColor White

$rows = @()
if (-not $SkipApi) {
    $s = Get-Service $SVC_API -ErrorAction SilentlyContinue
    $rows += [pscustomobject]@{ Component='API';      Type='Windows Service';     Name=$SVC_API;     Status=$s?.Status; URL="http://localhost:$ApiPort/" }
}
if (-not $SkipApp) {
    $s = Get-Service $SVC_APP -ErrorAction SilentlyContinue
    $rows += [pscustomobject]@{ Component='App';      Type='Windows Service';     Name=$SVC_APP;     Status=$s?.Status; URL="http://localhost:$AppPort/" }
}
if (-not $SkipProxy) {
    $s = Get-Service $SVC_PROXY -ErrorAction SilentlyContinue
    $rows += [pscustomobject]@{ Component='Proxy';    Type='Windows Service';     Name=$SVC_PROXY;   Status=$s?.Status; URL="http://localhost:$ProxyPort/" }
}
if (-not $SkipImporter) {
    $t = Get-ScheduledTask $TASK_IMPORT -ErrorAction SilentlyContinue
    $rows += [pscustomobject]@{ Component='Importer'; Type='Scheduled Task';      Name=$TASK_IMPORT; Status=$t?.State;  URL="(every $ImporterIntervalMinutes min)" }
}

$rows | Format-Table -AutoSize

Write-Host ''
Write-Host "  Log directory : $LogDir" -ForegroundColor Cyan
Write-Host "  Deploy log    : $transcriptPath" -ForegroundColor Cyan
if (-not $SkipProxy) {
    Write-Host ''
    Write-Host "  Open in browser: http://$(hostname)/" -ForegroundColor Green
}
Write-Host ''
Write-Host 'To manually trigger the importer:' -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$TASK_IMPORT'" -ForegroundColor Yellow
Write-Host ''

Stop-Transcript | Out-Null
