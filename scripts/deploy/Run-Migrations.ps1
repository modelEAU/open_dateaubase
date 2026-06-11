#Requires -RunAsAdministrator
#Requires -Version 5.1
<#
.SYNOPSIS
    Apply pending schema migrations to an existing open_datEAUbase database.

.DESCRIPTION
    Reads the current schema version from the SchemaVersion table and applies
    any migration scripts that have not yet been run, up to $TargetVersion.

    The migration catalogue is defined inside this script (see $MigrationCatalogue).
    Add new entries there as future migrations are created.

    Re-running is safe: already-applied migrations are skipped automatically.

.PARAMETER ServerInstance
    SQL Server instance. Examples: "localhost", "DBSERVER2025\INST", "host,1433".

.PARAMETER DatabaseName
    Name of the existing database to migrate.

.PARAMETER DbUser
    SQL Server login. Defaults to 'SA'. Leave empty when using -WindowsAuth.

.PARAMETER DbPassword
    Password for $DbUser. Required unless -WindowsAuth is set.

.PARAMETER WindowsAuth
    Use Windows Integrated Authentication instead of SQL login.

.PARAMETER InstallDir
    Root directory of the cloned repository (contains the migrations\ folder).

.PARAMETER TargetVersion
    Schema version to migrate to. Defaults to the latest known version.
    Must match a version string in the migration catalogue.

.PARAMETER DryRun
    Show which migrations would be applied without executing them.

.PARAMETER SqlCmdPath
    Full path to sqlcmd.exe. Auto-detected if omitted.

.EXAMPLE
    # Apply all pending migrations
    .\Run-Migrations.ps1 `
        -ServerInstance "DBSERVER2025" `
        -DatabaseName   "open_dateaubase_prod" `
        -DbPassword     "Str0ngPr0ductionPwd!" `
        -InstallDir     "C:\open_dateaubase"

.EXAMPLE
    # Dry run — see what would be applied
    .\Run-Migrations.ps1 `
        -ServerInstance "DBSERVER2025" `
        -DatabaseName   "open_dateaubase_prod" `
        -DbPassword     "Str0ngPr0ductionPwd!" `
        -InstallDir     "C:\open_dateaubase" `
        -DryRun

.EXAMPLE
    # Migrate to a specific version (useful for staged rollouts)
    .\Run-Migrations.ps1 `
        -ServerInstance "DBSERVER2025" `
        -DatabaseName   "open_dateaubase_prod" `
        -DbPassword     "Str0ngPr0ductionPwd!" `
        -InstallDir     "C:\open_dateaubase" `
        -TargetVersion  "v2.1.0"

.NOTES
    Adding a new migration:
    Append an entry to $MigrationCatalogue in the format:
        @{ From = 'v2.0.0'; To = 'v2.1.0'; Script = 'migrations\v2.0.0_to_v2.1.0_mssql.sql' }
    The script paths are relative to $InstallDir.
    Fresh installations always start at v2.0.0 via Deploy-Database.ps1.

    Rollback scripts are NOT applied automatically. To roll back, run the
    corresponding *_rollback.sql script manually in SSMS after taking a backup.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$ServerInstance,

    [Parameter(Mandatory)]
    [string]$DatabaseName,

    [string]$DbUser      = 'SA',
    [string]$DbPassword  = '',
    [switch]$WindowsAuth,

    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path $_ -PathType Container })]
    [string]$InstallDir,

    [string]$TargetVersion = '',   # empty = latest
    [string]$SqlCmdPath    = '',
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDir 'DbHelpers.psm1') -Force

# ---------------------------------------------------------------------------
# Migration catalogue
# Add new migrations here as new schema versions are released.
# Order matters: entries must be sorted from oldest to newest.
# Each entry specifies the FROM version, the TO version, and the script
# path relative to $InstallDir.
# ---------------------------------------------------------------------------

$MigrationCatalogue = @(
    # Fresh installs start at v2.0.0 via Deploy-Database.ps1 (full create script).
    # This catalogue covers incremental upgrades from that baseline.
    # Add new entries here as each future release ships a migration script.
    # @{
    #     From           = 'v2.0.0'
    #     To             = 'v2.1.0'
    #     Script         = 'migrations\v2.0.0_to_v2.1.0_mssql.sql'
    #     Description    = 'Migration v2.0.0 → v2.1.0'
    #     RollbackScript = 'migrations\v2.0.0_to_v2.1.0_mssql_rollback.sql'
    # }
)

$LatestVersion = if ($MigrationCatalogue.Count -gt 0) { $MigrationCatalogue[-1].To } else { 'v2.0.0' }

# ---------------------------------------------------------------------------
# Validate credentials
# ---------------------------------------------------------------------------

$cred     = Resolve-SqlCredentials -WindowsAuth:$WindowsAuth -DbUser $DbUser -DbPassword $DbPassword
$authUser = $cred.User
$authPwd  = $cred.Password

$target = if ($TargetVersion) { $TargetVersion } else { $LatestVersion }

# Validate target version is in the catalogue (always accept the baseline even with an empty catalogue)
$knownVersions = @('v2.0.0') + ($MigrationCatalogue | ForEach-Object { $_.From; $_.To } | Select-Object -Unique)
if ($target -notin $knownVersions) {
    throw "Unknown target version '$target'. Known versions: $($knownVersions -join ', ')"
}

# ---------------------------------------------------------------------------
# Locate sqlcmd
# ---------------------------------------------------------------------------

Write-DbStep 'Locating sqlcmd...'
$sqlcmd = Find-SqlCmd -SqlCmdPath $SqlCmdPath
if (-not $sqlcmd) {
    throw 'sqlcmd.exe not found. Install SSMS or the SQL Server command-line tools.'
}
Write-DbStep "sqlcmd found: $sqlcmd" -Success

# ---------------------------------------------------------------------------
# Test connection and verify database exists
# ---------------------------------------------------------------------------

Test-DatabaseConnection `
    -SqlCmdExe      $sqlcmd `
    -ServerInstance $ServerInstance `
    -DbUser         $authUser `
    -DbPassword     $authPwd

$exists = Test-DatabaseExists `
    -SqlCmdExe      $sqlcmd `
    -ServerInstance $ServerInstance `
    -DatabaseName   $DatabaseName `
    -DbUser         $authUser `
    -DbPassword     $authPwd

if (-not $exists) {
    throw "Database '$DatabaseName' does not exist on '$ServerInstance'. Use Deploy-Database.ps1 to create it."
}

# ---------------------------------------------------------------------------
# Determine current schema version
# ---------------------------------------------------------------------------

Write-DbStep "Reading current schema version from '$DatabaseName'..."
$currentVersion = Get-SchemaVersion `
    -SqlCmdExe      $sqlcmd `
    -ServerInstance $ServerInstance `
    -DatabaseName   $DatabaseName `
    -DbUser         $authUser `
    -DbPassword     $authPwd

if ($null -eq $currentVersion) {
    # SchemaVersion table doesn't exist → assume this is a v1.0.0 baseline
    Write-DbStep "SchemaVersion table not found — assuming baseline v1.0.0." -Warn
    $currentVersion = 'v1.0.0'
} else {
    Write-DbStep "Current version: $currentVersion" -Success
}

if ($currentVersion -eq $target) {
    Write-Host ''
    Write-Host "Database '$DatabaseName' is already at version $target. No migrations needed." -ForegroundColor Green
    Write-Host ''
    exit 0
}

# ---------------------------------------------------------------------------
# Build the ordered list of migrations to apply
# ---------------------------------------------------------------------------

$pending = [System.Collections.Generic.List[hashtable]]::new()
$cursor  = $currentVersion

foreach ($migration in $MigrationCatalogue) {
    if ($migration.From -eq $cursor) {
        $pending.Add($migration)
        $cursor = $migration.To
        if ($cursor -eq $target) { break }
    }
}

if ($pending.Count -eq 0) {
    Write-DbStep "No migration path found from '$currentVersion' to '$target'." -Warn
    Write-DbStep "The migration catalogue may need to be updated." -Warn
    exit 1
}

# ---------------------------------------------------------------------------
# Show pending migrations (single pass — resolve paths and existence once)
# ---------------------------------------------------------------------------

$pendingResolved = $pending | ForEach-Object {
    $p = Join-Path $InstallDir $_.Script
    [pscustomobject]@{
        Migration = $_
        Path      = $p
        Exists    = (Test-Path $p)
    }
}

Write-Host ''
Write-Host "Pending migrations ($($pending.Count)):" -ForegroundColor Cyan
foreach ($item in $pendingResolved) {
    $scriptStatus = if ($item.Exists) { 'OK' } else { 'MISSING' }
    $color        = if ($item.Exists) { 'White' } else { 'Red' }
    Write-Host "  $($item.Migration.From) -> $($item.Migration.To)  [$scriptStatus]  $($item.Migration.Description)" -ForegroundColor $color
}
Write-Host ''

# Abort if any script file is missing
$missingItems = $pendingResolved | Where-Object { -not $_.Exists }
if ($missingItems) {
    $list = $missingItems | ForEach-Object { "  $($_.Path)" }
    throw "Missing migration script(s):`n$($list -join "`n")`nEnsure your repository is up to date."
}

if ($DryRun) {
    Write-Host 'DRY RUN: no changes applied.' -ForegroundColor Yellow
    exit 0
}

# ---------------------------------------------------------------------------
# Confirm with user
# ---------------------------------------------------------------------------

$response = Read-Host "Apply $($pending.Count) migration(s) to '$DatabaseName'? This cannot be undone without a backup. [y/N]"
if ($response -notmatch '^[yY]') {
    Write-Host 'Aborted.' -ForegroundColor Yellow
    exit 0
}

# ---------------------------------------------------------------------------
# Apply each migration
# ---------------------------------------------------------------------------

$commonParams = @{
    SqlCmdExe      = $sqlcmd
    ServerInstance = $ServerInstance
    DatabaseName   = $DatabaseName
    DbUser         = $authUser
    DbPassword     = $authPwd
    SubstituteName = $true
}

$applied = 0
foreach ($item in $pendingResolved) {
    Write-DbStep "Applying: $($item.Migration.From) → $($item.Migration.To) — $($item.Migration.Description)"

    Invoke-SqlScript @commonParams `
        -ScriptPath  $item.Path `
        -Description $item.Migration.Description

    $applied++
    Write-DbStep "Migration $($item.Migration.To) applied ($applied / $($pending.Count))." -Success
}

# ---------------------------------------------------------------------------
# Verify final version
# ---------------------------------------------------------------------------

Write-DbStep 'Verifying final schema version...'
$finalVersion = Get-SchemaVersion `
    -SqlCmdExe      $sqlcmd `
    -ServerInstance $ServerInstance `
    -DatabaseName   $DatabaseName `
    -DbUser         $authUser `
    -DbPassword     $authPwd

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host ''
Write-Host '=================================================================' -ForegroundColor White
Write-Host ' Migration Complete' -ForegroundColor White
Write-Host '=================================================================' -ForegroundColor White
Write-Host ''
Write-Host "  Server        : $ServerInstance"  -ForegroundColor Cyan
Write-Host "  Database      : $DatabaseName"    -ForegroundColor Cyan
Write-Host "  From version  : $currentVersion"  -ForegroundColor Cyan
Write-Host "  To version    : $finalVersion"    -ForegroundColor Cyan
Write-Host "  Migrations    : $applied applied"  -ForegroundColor Cyan
Write-Host ''

if ($finalVersion -ne $target) {
    Write-Host "WARNING: expected version $target but SchemaVersion reports $finalVersion." -ForegroundColor Red
    Write-Host 'Check the migration script for a missing SchemaVersion INSERT.' -ForegroundColor Red
} else {
    Write-Host 'Schema is up to date.' -ForegroundColor Green
}

Write-Host ''
Write-Host 'Rollback note:' -ForegroundColor Yellow
foreach ($item in $pendingResolved) {
    $rb = Join-Path $InstallDir $item.Migration.RollbackScript
    if (Test-Path $rb) {
        Write-Host "  To revert $($item.Migration.To) -> $($item.Migration.From): run $rb in SSMS (after a backup)." -ForegroundColor Yellow
    }
}
Write-Host ''
