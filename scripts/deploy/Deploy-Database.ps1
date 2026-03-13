#Requires -RunAsAdministrator
#Requires -Version 5.1
<#
.SYNOPSIS
    Provision a new open_datEAUbase SQL Server database from scratch.

.DESCRIPTION
    Creates a new SQL Server 2025 database with the name you choose, applies the
    v1.0.0 baseline schema, runs the consolidated v1.0.0 → v2.1.0 migration,
    and optionally loads seed data and installs SQL Agent backup jobs.

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

.PARAMETER DatabaseName
    Name for the new database (e.g., "open_dateaubase_prod", "waterquality_2025").
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
    Load seed data after schema creation:
    - sql/seed_v2.1.0.sql  (reference equipment, parameters, units, sites)
    - sql/seed_importer_fixtures.sql  (importer-compatible lookup entries)
    Intended for dev and staging environments.

.PARAMETER WithBackupJobs
    Install SQL Agent backup jobs (weekly full, daily diff, 4-hour log, daily cleanup).
    Requires SQL Server Standard or Enterprise (SQL Agent not available in Express).

.PARAMETER SqlCmdPath
    Full path to sqlcmd.exe. Auto-detected if omitted.

.PARAMETER Force
    Drop and recreate the database if it already exists.
    WARNING: ALL DATA IN THE EXISTING DATABASE WILL BE LOST.

.EXAMPLE
    # Minimal production deploy
    .\Deploy-Database.ps1 `
        -ServerInstance "DBSERVER2025" `
        -DatabaseName   "open_dateaubase_prod" `
        -DbPassword     "Str0ngPr0ductionPwd!" `
        -InstallDir     "C:\open_dateaubase"

.EXAMPLE
    # Staging deploy with seed data and backup jobs
    .\Deploy-Database.ps1 `
        -ServerInstance "DBSERVER2025" `
        -DatabaseName   "open_dateaubase_staging" `
        -DbPassword     "StagingPwd123!" `
        -InstallDir     "C:\open_dateaubase" `
        -WithSeedData `
        -WithBackupJobs `
        -BackupDir      "D:\Backups"

.EXAMPLE
    # Dev deploy using Windows Authentication
    .\Deploy-Database.ps1 `
        -ServerInstance "localhost\SQLEXPRESS" `
        -DatabaseName   "open_dateaubase_dev" `
        -WindowsAuth `
        -InstallDir     "C:\open_dateaubase" `
        -WithSeedData
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [string]$ServerInstance,

    [Parameter(Mandatory)]
    [string]$DatabaseName,

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
# Apply baseline schema (v1.0.0)
# ---------------------------------------------------------------------------

Invoke-SqlScript @invokeParams `
    -ScriptPath  (Join-Path $InstallDir 'migrations\v1.0.0_create_mssql.sql') `
    -Description 'Baseline schema v1.0.0'

# ---------------------------------------------------------------------------
# Apply consolidated migration (v1.0.0 → v2.1.0)
# ---------------------------------------------------------------------------

Invoke-SqlScript @invokeParams `
    -ScriptPath  (Join-Path $InstallDir 'migrations\v1.0.0_to_v2.1.0_mssql.sql') `
    -Description 'Migration v1.0.0 → v2.1.0'

# ---------------------------------------------------------------------------
# Optional: seed data
# ---------------------------------------------------------------------------

if ($WithSeedData) {
    Write-DbStep 'Loading seed data...'
    Invoke-SqlScript @invokeParams `
        -ScriptPath  (Join-Path $InstallDir 'sql\seed_v2.1.0.sql') `
        -Description 'Seed data (reference equipment, parameters, sites)'

    Invoke-SqlScript @invokeParams `
        -ScriptPath  (Join-Path $InstallDir 'sql\seed_importer_fixtures.sql') `
        -Description 'Seed data (importer fixtures)'
}

# ---------------------------------------------------------------------------
# Set recovery model to FULL and seed the log chain
# ---------------------------------------------------------------------------

Write-DbStep "Setting recovery model to FULL for '$DatabaseName'..."
$recoveryScript = Join-Path $InstallDir 'scripts\maintenance\01_set_full_recovery.sql'
if (Test-Path $recoveryScript) {
    Invoke-SqlScript @invokeParams `
        -ScriptPath  $recoveryScript `
        -Description 'Set FULL recovery model + initial backup'
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

        # Ensure backup directories exist (under the actual database name, not the template)
        foreach ($sub in 'full', 'diff', 'log') {
            New-Item -ItemType Directory -Path (Join-Path $BackupDir "$DatabaseName\$sub") -Force | Out-Null
        }

        # Run the maintenance script against msdb, substituting both the DB name and backup path
        Invoke-SqlScript `
            -SqlCmdExe          $sqlcmd `
            -ServerInstance     $ServerInstance `
            -DatabaseName       'msdb' `
            -ScriptPath         $backupScript `
            -DbUser             $authUser `
            -DbPassword         $authPwd `
            -Description        'SQL Agent backup jobs' `
            -SubstituteName `
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
