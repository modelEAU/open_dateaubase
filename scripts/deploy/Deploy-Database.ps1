#Requires -RunAsAdministrator
#Requires -Version 5.1
<#
.SYNOPSIS
    Provision a new open_datEAUbase SQL Server database from scratch.

.DESCRIPTION
    Creates a new SQL Server 2025 database with the name you choose, applies the
    v2.0.0 full baseline schema and vocabulary seed, and optionally loads demo
    seed data and installs SQL Agent backup jobs.

    Re-running is safe: the script exits early if the database already exists
    unless -Force is specified.

    Requirements:
    - SQL Server 2025 (Standard or Enterprise for backup jobs; Express also works
      for schema-only deploy)
    - sqlcmd.exe in PATH or discoverable via common SSMS install locations
    - ODBC Driver 18 for SQL Server installed (bundled with SSMS)

.PARAMETER ServerInstance
    SQL Server instance to connect to. Use 'hostname' or 'hostname\instance'
    or 'hostname,port' for a non-default port.
    Examples: "localhost", "DBSERVER2025", "DBSERVER2025\SQLEXPRESS", "192.168.1.10,1433"

.PARAMETER Environment
    Target environment: 'staging' or 'production'. Drives the default database
    name and gates dev/demo seed data (which is blocked for both tiers).

.PARAMETER DatabaseName
    Name for the new database. Defaults to the environment profile's name
    (e.g. open_dateaubase_production). Pass a value to override.
    The name is substituted throughout the schema scripts automatically.

.PARAMETER DbUser
    SQL Server login for deployment. Defaults to 'SA'.
    Leave empty to use Windows Authentication (-WindowsAuth).

.PARAMETER DbPassword
    Password for $DbUser. Required unless -WindowsAuth is set.

.PARAMETER WindowsAuth
    Use Windows Integrated Authentication instead of SQL login.

.PARAMETER InstallDir
    Root directory of the cloned open_datEAUbase repository.
    Used to locate SQL scripts under migrations/ and sql/.

.PARAMETER BackupDir
    Base directory for SQL Agent backup jobs.
    Subdirectories <DatabaseName>\full\, diff\, log\ are created automatically.
    Default: C:\Backups

.PARAMETER WithSeedData
    Load dev/demo seed data after schema creation:
    - sql/seed_fixtures.sql  (sample procedures, TEST_ watershed + lab)
    - sql/seed_demo.sql      (TEST_ site, process units, campaigns, lab panels)
    Intended for local Docker dev only. BLOCKED for both -Environment staging
    and production (the script throws if this flag is combined with them).

.PARAMETER WithBackupJobs
    Install SQL Agent backup jobs (weekly full, daily diff, 4-hour log, daily cleanup).
    Requires SQL Server Standard or Enterprise (SQL Agent not available in Express).

.PARAMETER SqlCmdPath
    Full path to sqlcmd.exe. Auto-detected if omitted.

.PARAMETER Force
    Drop and recreate the database if it already exists.
    WARNING: ALL DATA IN THE EXISTING DATABASE WILL BE LOST.

.EXAMPLE
    # Minimal production deploy (database name derived: open_dateaubase_production)
    .\Deploy-Database.ps1 `
        -ServerInstance "DBSERVER2025" `
        -Environment    production `
        -DbPassword     "Str0ngPr0ductionPwd!" `
        -InstallDir     "C:\open_dateaubase"

.EXAMPLE
    # Staging deploy with backup jobs (database name derived: open_dateaubase_staging)
    .\Deploy-Database.ps1 `
        -ServerInstance "DBSERVER2025" `
        -Environment    staging `
        -DbPassword     "StagingPwd123!" `
        -InstallDir     "C:\open_dateaubase" `
        -WithBackupJobs `
        -BackupDir      "D:\Backups"

.EXAMPLE
    # Override the derived database name (e.g. a second staging slot)
    .\Deploy-Database.ps1 `
        -ServerInstance "DBSERVER2025" `
        -Environment    staging `
        -DatabaseName   "open_dateaubase_staging_qa" `
        -DbPassword     "StagingPwd123!" `
        -InstallDir     "C:\open_dateaubase"
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [string]$ServerInstance,

    [Parameter(Mandatory)]
    [ValidateSet('staging', 'production')]
    [string]$Environment,

    # Defaults to the environment profile's database name (e.g. open_dateaubase_production).
    [string]$DatabaseName = '',

    [string]$DbUser     = 'SA',
    [string]$DbPassword = '',
    [switch]$WindowsAuth,

    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path $_ -PathType Container })]
    [string]$InstallDir,

    [string]$BackupDir   = 'C:\Backups',
    [string]$SqlCmdPath  = '',

    [switch]$WithSeedData,
    [switch]$WithBackupJobs,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDir 'DbHelpers.psm1') -Force
Import-Module (Join-Path $scriptDir 'EnvironmentProfiles.psm1') -Force

# ---------------------------------------------------------------------------
# Resolve environment profile and derive defaults
# ---------------------------------------------------------------------------

$envProfile = Get-EnvironmentProfile -Environment $Environment
if ([string]::IsNullOrWhiteSpace($DatabaseName)) {
    $DatabaseName = $envProfile.DatabaseName
}

# Guard: dev/demo seed data is never loaded into a staging or production tier.
# The TEST_ watershed, demo site, sample procedures and lab panels are for the
# local Docker dev environment only.
if ($WithSeedData -and -not $envProfile.AllowSeedData) {
    throw @"
Refusing to load dev/demo seed data into the '$Environment' environment.
Seed data (sql\seed_fixtures.sql, sql\seed_demo.sql — TEST_ watershed, demo
site, sample panels) is for local Docker dev only.
Re-run without -WithSeedData.
"@
}

# ---------------------------------------------------------------------------
# Validate / resolve credentials
# ---------------------------------------------------------------------------

$cred     = Resolve-SqlCredentials -WindowsAuth:$WindowsAuth -DbUser $DbUser -DbPassword $DbPassword
$authUser = $cred.User
$authPwd  = $cred.Password

# ---------------------------------------------------------------------------
# Locate sqlcmd
# ---------------------------------------------------------------------------

Write-DbStep 'Locating sqlcmd...'
$sqlcmd = Find-SqlCmd -SqlCmdPath $SqlCmdPath
if (-not $sqlcmd) {
    throw @'
sqlcmd.exe not found. Install one of:
  - SQL Server Management Studio (SSMS) 20+
  - SQL Server command-line tools from https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-utility
  - winget install Microsoft.SqlServer.CmdLineUtils
'@
}
Write-DbStep "sqlcmd found: $sqlcmd" -Success

# ---------------------------------------------------------------------------
# Test connection
# ---------------------------------------------------------------------------

Test-DatabaseConnection `
    -SqlCmdExe      $sqlcmd `
    -ServerInstance $ServerInstance `
    -DbUser         $authUser `
    -DbPassword     $authPwd

# ---------------------------------------------------------------------------
# Check if database already exists
# ---------------------------------------------------------------------------

Write-DbStep "Checking if database '$DatabaseName' exists..."
$exists = Test-DatabaseExists `
    -SqlCmdExe      $sqlcmd `
    -ServerInstance $ServerInstance `
    -DatabaseName   $DatabaseName `
    -DbUser         $authUser `
    -DbPassword     $authPwd

if ($exists) {
    if ($Force) {
        Write-DbStep "Database '$DatabaseName' exists. -Force specified — dropping..." -Warn
        Invoke-SqlQuery `
            -SqlCmdExe      $sqlcmd `
            -ServerInstance $ServerInstance `
            -DatabaseName   'master' `
            -Query          "ALTER DATABASE [$DatabaseName] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [$DatabaseName];" `
            -DbUser         $authUser `
            -DbPassword     $authPwd | Out-Null
        Write-DbStep "Existing database '$DatabaseName' dropped." -Warn
    } else {
        Write-Host ''
        Write-Host "Database '$DatabaseName' already exists on '$ServerInstance'." -ForegroundColor Yellow
        Write-Host 'To apply pending migrations, use Run-Migrations.ps1.' -ForegroundColor Yellow
        Write-Host 'To drop and recreate, re-run with -Force (ALL DATA WILL BE LOST).' -ForegroundColor Red
        Write-Host ''
        exit 0
    }
}

# ---------------------------------------------------------------------------
# Create database
# ---------------------------------------------------------------------------

Write-DbStep "Creating database '$DatabaseName'..."
Invoke-SqlQuery `
    -SqlCmdExe      $sqlcmd `
    -ServerInstance $ServerInstance `
    -DatabaseName   'master' `
    -Query          "CREATE DATABASE [$DatabaseName];" `
    -DbUser         $authUser `
    -DbPassword     $authPwd | Out-Null
Write-DbStep "Database '$DatabaseName' created." -Success

# Common invocation params (reused for all script steps below)
$invokeParams = @{
    SqlCmdExe      = $sqlcmd
    ServerInstance = $ServerInstance
    DatabaseName   = $DatabaseName
    DbUser         = $authUser
    DbPassword     = $authPwd
    SubstituteName = $true    # replace template DB name literals with $DatabaseName
}

# ---------------------------------------------------------------------------
# Apply full baseline schema (v2.0.0)
# ---------------------------------------------------------------------------

Invoke-SqlScript @invokeParams `
    -ScriptPath  (Join-Path $InstallDir 'sql_generation_scripts\v2.0.0_create_mssql.sql') `
    -Description 'Full schema v2.0.0'

# ---------------------------------------------------------------------------
# Apply vocabulary seed (generated from YAML seed_data fields)
# ---------------------------------------------------------------------------

Invoke-SqlScript @invokeParams `
    -ScriptPath  (Join-Path $InstallDir 'sql_generation_scripts\v2.0.0_seed_mssql.sql') `
    -Description 'Vocabulary seed v2.0.0'

# ---------------------------------------------------------------------------
# Optional: dev/demo seed data (local dev only; omit for staging + production)
# ---------------------------------------------------------------------------

if ($WithSeedData) {
    Write-DbStep 'Loading dev seed data...'
    Invoke-SqlScript @invokeParams `
        -ScriptPath  (Join-Path $InstallDir 'sql\seed_fixtures.sql') `
        -Description 'Fixture seed (procedures, TEST_ watershed + lab)'

    Invoke-SqlScript @invokeParams `
        -ScriptPath  (Join-Path $InstallDir 'sql\seed_demo.sql') `
        -Description 'Demo seed (TEST_ site, process units, campaigns, lab panels)'
}

# ---------------------------------------------------------------------------
# Set recovery model to FULL and seed the log chain
# ---------------------------------------------------------------------------

Write-DbStep "Setting recovery model to FULL for '$DatabaseName'..."

# The recovery script seeds an initial full backup, and the optional Agent jobs
# write here too. Create the backup subdirs (under the actual database name) up
# front so the seed backup below does not fail on a missing path.
foreach ($sub in 'full', 'diff', 'log') {
    New-Item -ItemType Directory -Path (Join-Path $BackupDir "$DatabaseName\$sub") -Force | Out-Null
}

$recoveryScript = Join-Path $InstallDir 'scripts\maintenance\01_set_full_recovery.sql'
if (Test-Path $recoveryScript) {
    # Substitute the backup path too, so the seed backup honors -BackupDir
    # (the script hardcodes C:\Backups).
    Invoke-SqlScript @invokeParams `
        -ScriptPath         $recoveryScript `
        -Description        'Set FULL recovery model + initial backup' `
        -ExtraSubstitutions @{ 'C:\Backups' = $BackupDir }
} else {
    # Inline fallback if the maintenance script is absent
    Invoke-SqlQuery `
        -SqlCmdExe      $sqlcmd `
        -ServerInstance $ServerInstance `
        -DatabaseName   $DatabaseName `
        -DbUser         $authUser `
        -DbPassword     $authPwd `
        -Query          "ALTER DATABASE [$DatabaseName] SET RECOVERY FULL;" | Out-Null
    Write-DbStep 'Recovery model set to FULL (inline; no initial backup taken).' -Warn
}

# ---------------------------------------------------------------------------
# Optional: SQL Agent backup jobs
# ---------------------------------------------------------------------------

if ($WithBackupJobs) {
    $backupScript = Join-Path $InstallDir 'scripts\maintenance\02_install_backup_jobs.sql'
    if (-not (Test-Path $backupScript)) {
        Write-DbStep 'Backup job script not found; skipping.' -Warn
    } else {
        Write-DbStep 'Installing SQL Agent backup jobs...'

        # Backup directories were already created before the recovery step above.
        # Run the maintenance script against msdb, substituting both the DB name and backup path
        # Connect to msdb (where Agent jobs live), but substitute the real
        # deployment database name into the script, not 'msdb'.
        Invoke-SqlScript `
            -SqlCmdExe          $sqlcmd `
            -ServerInstance     $ServerInstance `
            -DatabaseName       'msdb' `
            -ScriptPath         $backupScript `
            -DbUser             $authUser `
            -DbPassword         $authPwd `
            -Description        'SQL Agent backup jobs' `
            -SubstituteName `
            -SubstituteValue    $DatabaseName `
            -ExtraSubstitutions @{ 'C:\Backups' = $BackupDir }
    }
}

# ---------------------------------------------------------------------------
# Verify: query SchemaVersion
# ---------------------------------------------------------------------------

Write-DbStep 'Verifying schema version...'
$version = Get-SchemaVersion `
    -SqlCmdExe      $sqlcmd `
    -ServerInstance $ServerInstance `
    -DatabaseName   $DatabaseName `
    -DbUser         $authUser `
    -DbPassword     $authPwd
Write-DbStep "Schema version: $version" -Success

# Row counts across value tables
$countQuery = @'
SELECT
    'Value'       AS [Table], COUNT(*) AS [Rows] FROM dbo.Value        UNION ALL
SELECT 'ValueVector',                              COUNT(*)             FROM dbo.ValueVector    UNION ALL
SELECT 'ValueMatrix',                              COUNT(*)             FROM dbo.ValueMatrix    UNION ALL
SELECT 'ValueImage',                               COUNT(*)             FROM dbo.ValueImage     UNION ALL
SELECT 'Channel',                                  COUNT(*)             FROM dbo.Channel        UNION ALL
SELECT 'Equipment',                                COUNT(*)             FROM dbo.Equipment
'@
$rows = Invoke-SqlQuery `
    -SqlCmdExe      $sqlcmd `
    -ServerInstance $ServerInstance `
    -DatabaseName   $DatabaseName `
    -Query          $countQuery `
    -DbUser         $authUser `
    -DbPassword     $authPwd
$rows | ForEach-Object { Write-Host "  $_" }

# ---------------------------------------------------------------------------
# Print .env snippet for the application
# ---------------------------------------------------------------------------

$addr = Split-ServerInstance $ServerInstance

Write-Host ''
Write-Host '=================================================================' -ForegroundColor White
Write-Host ' Database Deployment Complete' -ForegroundColor White
Write-Host '=================================================================' -ForegroundColor White
Write-Host ''
Write-Host "  Server   : $ServerInstance" -ForegroundColor Cyan
Write-Host "  Database : $DatabaseName" -ForegroundColor Cyan
Write-Host "  Version  : $version" -ForegroundColor Cyan
if ($WithBackupJobs) {
    Write-Host "  Backups  : $BackupDir\$DatabaseName\" -ForegroundColor Cyan
}
Write-Host ''
Write-Host '.env snippet for Deploy-OpenDateaubase.ps1:' -ForegroundColor Yellow
Write-Host ''
Write-Host "DB_HOST=$($addr.Host)"
Write-Host "DB_PORT=$($addr.Port)"
Write-Host "DB_NAME=$DatabaseName"
Write-Host "DB_USER=$DbUser"
Write-Host "DB_PASSWORD=<your-password>"
Write-Host 'DB_DRIVER=ODBC Driver 18 for SQL Server'
Write-Host ''
Write-Host 'To run pending migrations in future:' -ForegroundColor Yellow
Write-Host "  .\Run-Migrations.ps1 -ServerInstance '$ServerInstance' -DatabaseName '$DatabaseName' ..." -ForegroundColor Yellow
Write-Host ''
