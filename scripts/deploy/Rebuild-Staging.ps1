#Requires -RunAsAdministrator
#Requires -Version 5.1
<#
.SYNOPSIS
    Full clean rebuild of the staging environment from the regenerated v2.0.0
    baseline. DESTRUCTIVE: drops and recreates open_dateaubase_staging.

.DESCRIPTION
    One-shot orchestration for "rebuild from scratch" after schema/code changes
    (ManualLocation widening, ingest wiring ValidFrom backdate, deployment-delete
    fix). Runs the sanctioned sub-scripts in order:

      1. Stop the API + App services (clean drop window).
      2. Deploy-Database.ps1 -Force  -> drop + recreate + apply
         sql_generation_scripts\v2.0.0_create_mssql.sql + v2.0.0_seed_mssql.sql.
      3. Start API + App (now running the new code) and health-check the API.
      4. (Re)register the importer scheduled task, kick it once, and wait for it
         to finish loading all 5 pilEAUte sources (data ingested with the fixed
         backdated wiring).
      5. Run reconcile_pileaute.py (Steps A + B): master data + process units +
         sampling locations (unlinked), via `uv run --isolated`.
      6. Verify: schema version, row counts, ManualLocation max length, and the
         monEAU EquipmentWiringHistory.ValidFrom (should be ~min observation, not
         the ingest moment).

    Credentials (SA password, API_SERVICE_TOKEN) are read from .env.staging — no
    secrets on the command line.

.PARAMETER Force
    Required acknowledgement that the staging database will be dropped.

.PARAMETER SkipImporter
    Rebuild the DB + restart services but do not run the importer or reconcile.

.PARAMETER ImporterTimeoutMinutes
    How long to wait for the importer run to finish. Default 20.

.EXAMPLE
    # From an elevated PowerShell prompt:
    .\scripts\deploy\Rebuild-Staging.ps1 -Force
#>

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$SkipImporter,
    [int]$ImporterTimeoutMinutes = 20
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$installDir  = Split-Path -Parent (Split-Path -Parent $scriptDir)

Import-Module (Join-Path $scriptDir 'DbHelpers.psm1') -Force
Import-Module (Join-Path $scriptDir 'DeployHelpers.psm1') -Force

if (-not $Force) {
    throw "This DROPS the staging database. Re-run with -Force to proceed."
}

# ---------------------------------------------------------------------------
# Load environment + resolve tools
# ---------------------------------------------------------------------------

$envPath = Join-Path $installDir '.env.staging'
$envVars = Import-EnvFile -Path $envPath

foreach ($k in 'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_PASSWORD') {
    if (-not $envVars.Contains($k) -or [string]::IsNullOrWhiteSpace($envVars[$k])) {
        throw "$k missing from $envPath"
    }
}

# go-sqlcmd (C:\Program Files\SqlCmd) builds a sqlserver:// URL and rejects a
# backslash instance name combined with a port ("invalid URL escape %5C"). The
# instance listens on a static port, so connect by machine,port and drop the
# \INSTANCE suffix from DB_HOST.
$dbMachine      = $envVars['DB_HOST'].Split('\')[0]
$serverInstance = "$dbMachine,$($envVars['DB_PORT'])"
$dbName         = $envVars['DB_NAME']
$dbPassword     = $envVars['DB_PASSWORD']
$dbUser         = if ($envVars.Contains('DB_USER') -and $envVars['DB_USER']) { $envVars['DB_USER'] } else { 'SA' }

$nssm = Find-Nssm
if (-not $nssm) { throw "nssm.exe not found." }
$sqlcmd = Find-SqlCmd
if (-not $sqlcmd) { throw "sqlcmd.exe not found." }

$SVC_API = 'OpenDateaubase-Staging-API'
$SVC_APP = 'OpenDateaubase-Staging-App'
$TASK_IMPORT = 'OpenDateaubase-Staging-Importer'
$apiHealth = 'http://127.0.0.1:8010/api/v1/health'

Write-Step "Rebuild target: $dbName on $serverInstance" -Success

# ---------------------------------------------------------------------------
# 1. Stop services for a clean drop window
# ---------------------------------------------------------------------------

Write-Step "Stopping services..."
Stop-ManagedService -NssmExe $nssm -ServiceName $SVC_APP
Stop-ManagedService -NssmExe $nssm -ServiceName $SVC_API

# ---------------------------------------------------------------------------
# 2. Drop + recreate the database from the regenerated baseline
# ---------------------------------------------------------------------------

Write-Step "Rebuilding database (Deploy-Database.ps1 -Force)..."
& (Join-Path $scriptDir 'Deploy-Database.ps1') `
    -ServerInstance $serverInstance `
    -Environment    staging `
    -DatabaseName   $dbName `
    -DbUser         $dbUser `
    -DbPassword     $dbPassword `
    -InstallDir     $installDir `
    -Force
# Deploy-Database.ps1 runs with ErrorActionPreference=Stop and throws on failure,
# which propagates here — no exit-code check needed.

Write-Step "Applying schema migrations to the latest version (Run-Migrations.ps1)..."
& (Join-Path $scriptDir 'Run-Migrations.ps1') `
    -ServerInstance $serverInstance `
    -Environment    staging `
    -DatabaseName   $dbName `
    -DbUser         $dbUser `
    -DbPassword     $dbPassword `
    -InstallDir     $installDir
# Run-Migrations.ps1 exits with a non-zero code (rather than throwing) on
# failure, so it does not propagate through & automatically — check explicitly.
if ($LASTEXITCODE -ne 0) { throw "Run-Migrations.ps1 failed (exit $LASTEXITCODE)." }

# ---------------------------------------------------------------------------
# 3. Start services (new code) + health check
# ---------------------------------------------------------------------------

Write-Step "Starting services..."
Start-ManagedService -NssmExe $nssm -ServiceName $SVC_API
Start-ManagedService -NssmExe $nssm -ServiceName $SVC_APP
Assert-ServiceHealthy -Url $apiHealth -TimeoutSec 60

if ($SkipImporter) {
    Write-Step "SkipImporter set — DB rebuilt and services up. Stopping here." -Warn
    return
}

# ---------------------------------------------------------------------------
# 4. (Re)register + run the importer, wait for completion
# ---------------------------------------------------------------------------

Write-Step "Ensuring importer task is registered..."
& (Join-Path $installDir 'pileaute-config\update-scheduled-tasks.ps1')

Write-Step "Starting importer task '$TASK_IMPORT'..."
Start-ScheduledTask -TaskName $TASK_IMPORT
Start-Sleep -Seconds 5

$deadline = (Get-Date).AddMinutes($ImporterTimeoutMinutes)
do {
    Start-Sleep -Seconds 15
    $info  = Get-ScheduledTaskInfo -TaskName $TASK_IMPORT
    $state = (Get-ScheduledTask -TaskName $TASK_IMPORT).State
    Write-Host "  importer state=$state lastResult=$($info.LastTaskResult)"
} while ($state -eq 'Running' -and (Get-Date) -lt $deadline)

if ($state -eq 'Running') {
    Write-Step "Importer still running after $ImporterTimeoutMinutes min — it may need another pass. Continuing to reconcile." -Warn
} else {
    Write-Step "Importer finished (LastTaskResult=$($info.LastTaskResult))." -Success
}

# ---------------------------------------------------------------------------
# 5. Reconcile master data + process units + sampling locations (Steps A & B)
# ---------------------------------------------------------------------------

Write-Step "Running reconcile_pileaute.py (master data + process units + sampling locations)..."
$uv = Find-Uv
if (-not $uv) { throw "uv.exe not found." }
& $uv run --isolated --with openpyxl python C:\source\pileaute-ops\reconcile_pileaute.py
if ($LASTEXITCODE -ne 0) { throw "reconcile_pileaute.py failed (exit $LASTEXITCODE)." }

# ---------------------------------------------------------------------------
# 6. Verify
# ---------------------------------------------------------------------------

Write-Step "Verifying..."
$verifyQuery = @'
SET NOCOUNT ON;
SELECT 'schema_version' AS k, CONVERT(varchar(50), MAX(Version)) AS v FROM dbo.SchemaVersion
UNION ALL SELECT 'channels',            CONVERT(varchar(50), COUNT(*)) FROM dbo.Channel
UNION ALL SELECT 'equipment',           CONVERT(varchar(50), COUNT(*)) FROM dbo.Equipment
UNION ALL SELECT 'equipment_models',    CONVERT(varchar(50), COUNT(*)) FROM dbo.EquipmentModel
UNION ALL SELECT 'wiring_rows',         CONVERT(varchar(50), COUNT(*)) FROM dbo.EquipmentWiringHistory
UNION ALL SELECT 'sampling_points',     CONVERT(varchar(50), COUNT(*)) FROM dbo.SamplingPoint
UNION ALL SELECT 'process_units',       CONVERT(varchar(50), COUNT(*)) FROM dbo.ProcessUnit
UNION ALL SELECT 'manualloc_maxlen',    CONVERT(varchar(50), MAX(LEN(ManualLocation))) FROM dbo.EquipmentModel
UNION ALL SELECT 'wiring_validfrom_min',CONVERT(varchar(50), MIN(ValidFrom)) FROM dbo.EquipmentWiringHistory
UNION ALL SELECT 'wiring_validfrom_max',CONVERT(varchar(50), MAX(ValidFrom)) FROM dbo.EquipmentWiringHistory;
'@
$rows = Invoke-SqlQuery -SqlCmdExe $sqlcmd -ServerInstance $serverInstance -DatabaseName $dbName `
    -DbUser $dbUser -DbPassword $dbPassword -Query $verifyQuery
$rows | ForEach-Object { Write-Host "  $_" }

Write-Host ''
Write-Step "Rebuild complete. Next: plant visit (Step D) -> fill commissioning_worksheet.xlsx -> commission_pileaute.py --apply (Step E)." -Success
