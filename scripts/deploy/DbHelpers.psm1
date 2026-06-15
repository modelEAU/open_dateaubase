#Requires -Version 5.1
<#
.SYNOPSIS
    Shared database helper functions for Deploy-Database.ps1 and Run-Migrations.ps1.
    Requires sqlcmd (installed with SSMS or SQL Server tools).
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Sentinel: the database name baked into the checked-in SQL scripts.
# Substituted with the caller's $DatabaseName at deploy time.
$script:TEMPLATE_DB_NAME = 'open_dateaubase'

# ---------------------------------------------------------------------------
# Output helpers (mirrors DeployHelpers.psm1 style)
# ---------------------------------------------------------------------------

function Write-DbStep {
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

# ---------------------------------------------------------------------------
# sqlcmd discovery
# ---------------------------------------------------------------------------

function Find-SqlCmd {
    <#
    .SYNOPSIS
        Returns the full path to sqlcmd.exe.
        Searches common SSMS/SQL Server tools locations and PATH.
    #>
    param([string]$SqlCmdPath = '')

    if ($SqlCmdPath -and (Test-Path $SqlCmdPath)) { return $SqlCmdPath }

    # Check PATH first
    $inPath = Get-Command sqlcmd -ErrorAction SilentlyContinue
    if ($inPath) { return $inPath.Source }

    # Common SSMS / SQL Server Client Tools install locations
    $candidates = @(
        # SQL Server 2022 / 2025 client tools
        "${env:ProgramFiles}\Microsoft SQL Server\Client SDK\ODBC\170\Tools\Binn\sqlcmd.exe",
        "${env:ProgramFiles}\Microsoft SQL Server\Client SDK\ODBC\180\Tools\Binn\sqlcmd.exe",
        # SSMS bundled sqlcmd
        "${env:ProgramFiles(x86)}\Microsoft SQL Server Management Studio 20\Common7\IDE\sqlcmd.exe",
        "${env:ProgramFiles(x86)}\Microsoft SQL Server Management Studio 19\Common7\IDE\sqlcmd.exe",
        # Older SQL Server versions
        "${env:ProgramFiles}\Microsoft SQL Server\110\Tools\Binn\sqlcmd.exe",
        "${env:ProgramFiles}\Microsoft SQL Server\120\Tools\Binn\sqlcmd.exe",
        "${env:ProgramFiles}\Microsoft SQL Server\130\Tools\Binn\sqlcmd.exe",
        "${env:ProgramFiles}\Microsoft SQL Server\140\Tools\Binn\sqlcmd.exe",
        "${env:ProgramFiles}\Microsoft SQL Server\150\Tools\Binn\sqlcmd.exe",
        "${env:ProgramFiles}\Microsoft SQL Server\160\Tools\Binn\sqlcmd.exe"
    ) | Where-Object { $_ -and (Test-Path $_) }

    if ($candidates) { return $candidates[0] }
    return $null
}

# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------

function Resolve-SqlCredentials {
    <#
    .SYNOPSIS
        Validates and resolves SQL auth parameters.
        Returns a hashtable @{ User = ...; Password = ... }.
        User/Password are both empty string for Windows Authentication.
    #>
    param(
        [switch]$WindowsAuth,
        [string]$DbUser     = 'SA',
        [string]$DbPassword = ''
    )
    if (-not $WindowsAuth -and -not $DbPassword) {
        throw 'Provide -DbPassword or use -WindowsAuth for Windows Integrated Authentication.'
    }
    return @{
        User     = if ($WindowsAuth) { '' } else { $DbUser }
        Password = if ($WindowsAuth) { '' } else { $DbPassword }
    }
}

# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

function Split-ServerInstance {
    <#
    .SYNOPSIS
        Parses 'hostname' or 'hostname,port' into @{ Host = ...; Port = ... }.
    #>
    param([string]$ServerInstance)
    $parts = $ServerInstance -split ','
    return @{
        Host = $parts[0].Trim()
        Port = if ($parts.Count -gt 1) { $parts[1].Trim() } else { '1433' }
    }
}

function Get-SqlCmdArgs {
    <#
    .SYNOPSIS
        Returns common sqlcmd argument list for a given connection.
        Uses Windows Authentication if $DbUser is empty.
    #>
    param(
        [string]$ServerInstance,
        [string]$DatabaseName   = 'master',
        [string]$DbUser         = '',
        [string]$DbPassword     = ''
    )
    # -C trusts the server certificate. Modern sqlcmd (go-sqlcmd / ODBC Driver 18)
    # defaults to mandatory encryption with full cert validation, which fails against
    # a SQL Server using a self-signed cert. This matches the TrustServerCertificate=yes
    # used in the generated .env connection string (see Get-ConnectionString).
    $cmdArgs = @('-S', $ServerInstance, '-d', $DatabaseName, '-b', '-V', '1', '-C')
    if ($DbUser) {
        $cmdArgs += @('-U', $DbUser, '-P', $DbPassword)
    } else {
        $cmdArgs += '-E'   # Windows Authentication
    }
    return $cmdArgs
}

function Test-DatabaseConnection {
    <#
    .SYNOPSIS
        Verifies that sqlcmd can connect to the SQL Server instance.
        Retries up to $MaxAttempts times (useful right after service start).
    #>
    param(
        [string]$SqlCmdExe,
        [string]$ServerInstance,
        [string]$DbUser     = '',
        [string]$DbPassword = '',
        [int]$MaxAttempts   = 5,
        [int]$DelaySeconds  = 5
    )
    $baseArgs = Get-SqlCmdArgs -ServerInstance $ServerInstance -DbUser $DbUser -DbPassword $DbPassword
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        $output = & $SqlCmdExe @baseArgs -Q 'SELECT 1 AS connected' 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-DbStep "Connected to '$ServerInstance'." -Success
            return
        }
        Write-DbStep "Connection attempt $i/$MaxAttempts failed. Retrying in ${DelaySeconds}s..." -Warn
        Start-Sleep -Seconds $DelaySeconds
    }
    throw "Cannot connect to '$ServerInstance' after $MaxAttempts attempts. Output: $output"
}

function Test-DatabaseExists {
    <#
    .SYNOPSIS
        Returns $true if the named database already exists on the server.
    #>
    param(
        [string]$SqlCmdExe,
        [string]$ServerInstance,
        [string]$DatabaseName,
        [string]$DbUser     = '',
        [string]$DbPassword = ''
    )
    $baseArgs  = Get-SqlCmdArgs -ServerInstance $ServerInstance -DbUser $DbUser -DbPassword $DbPassword
    $safeName  = $DatabaseName.Replace("'", "''")
    $query     = "SELECT name FROM sys.databases WHERE name = N'$safeName'"
    $output    = & $SqlCmdExe @baseArgs -Q $query -h -1 2>&1 | Where-Object { $_ -match '\S' }
    return ($output -join '' -match [regex]::Escape($DatabaseName))
}

# ---------------------------------------------------------------------------
# SQL script execution with database-name substitution
# ---------------------------------------------------------------------------

function Invoke-SqlScript {
    <#
    .SYNOPSIS
        Executes a .sql file against the given server/database.

        When -SubstituteName is set, the hardcoded template DB name (defined by
        $script:TEMPLATE_DB_NAME) is replaced with $DatabaseName in memory before
        execution. The original file is never modified; a temp file is used and
        cleaned up automatically.

        -ExtraSubstitutions accepts a hashtable of additional literal-string
        replacements applied after the DB name substitution. Useful for
        substituting paths embedded in maintenance scripts.
        Example: @{ 'C:\Backups' = $BackupDir }
    #>
    param(
        [string]$SqlCmdExe,
        [string]$ServerInstance,
        [string]$DatabaseName,
        [string]$ScriptPath,
        [string]$DbUser             = '',
        [string]$DbPassword         = '',
        [string]$Description        = '',
        [switch]$SubstituteName,
        [hashtable]$ExtraSubstitutions = @{}
    )

    if (-not (Test-Path $ScriptPath)) {
        throw "SQL script not found: $ScriptPath"
    }

    $label = if ($Description) { $Description } else { Split-Path -Leaf $ScriptPath }
    Write-DbStep "Executing: $label..."

    $tempFile = $null
    try {
        $needsSubstitution = ($SubstituteName -and $DatabaseName -ne $script:TEMPLATE_DB_NAME) -or $ExtraSubstitutions.Count -gt 0

        if ($needsSubstitution) {
            $sql = Get-Content $ScriptPath -Raw

            if ($SubstituteName -and $DatabaseName -ne $script:TEMPLATE_DB_NAME) {
                $sql = $sql -replace "\[$script:TEMPLATE_DB_NAME\]", "[$DatabaseName]"
                $sql = $sql -replace "(?<![_\w])$([regex]::Escape($script:TEMPLATE_DB_NAME))(?![_\w])", $DatabaseName
            }

            foreach ($find in $ExtraSubstitutions.Keys) {
                $sql = $sql -replace [regex]::Escape($find), $ExtraSubstitutions[$find]
            }

            $tempFile = [IO.Path]::Combine($env:TEMP, "sqlscript_$(New-Guid).sql")
            Set-Content -Path $tempFile -Value $sql -Encoding UTF8
            $scriptToRun = $tempFile
        } else {
            $scriptToRun = $ScriptPath
        }

        $baseArgs = Get-SqlCmdArgs -ServerInstance $ServerInstance -DatabaseName $DatabaseName `
                                   -DbUser $DbUser -DbPassword $DbPassword
        $output = & $SqlCmdExe @baseArgs -i $scriptToRun 2>&1
        if ($LASTEXITCODE -ne 0) {
            $msg = $output | Out-String
            throw "Script '$label' failed (exit $LASTEXITCODE):`n$msg"
        }
        Write-DbStep "$label applied successfully." -Success
    } finally {
        if ($tempFile -and (Test-Path $tempFile)) { Remove-Item $tempFile -Force }
    }
}

function Invoke-SqlQuery {
    <#
    .SYNOPSIS
        Executes an inline SQL query and returns the raw output lines.
    #>
    param(
        [string]$SqlCmdExe,
        [string]$ServerInstance,
        [string]$DatabaseName,
        [string]$Query,
        [string]$DbUser     = '',
        [string]$DbPassword = ''
    )
    $baseArgs = Get-SqlCmdArgs -ServerInstance $ServerInstance -DatabaseName $DatabaseName `
                               -DbUser $DbUser -DbPassword $DbPassword
    $output = & $SqlCmdExe @baseArgs -Q $Query -h -1 2>&1
    if ($LASTEXITCODE -ne 0) {
        $msg = $output | Out-String
        throw "Query failed (exit $LASTEXITCODE):`n$msg"
    }
    return $output | Where-Object { $_ -match '\S' }   # strip blank lines
}

# ---------------------------------------------------------------------------
# Schema version management
# ---------------------------------------------------------------------------

function Get-SchemaVersion {
    <#
    .SYNOPSIS
        Returns the current schema version string from the SchemaVersion table,
        or $null if the table does not exist yet.
        Uses a single SQL round-trip with a conditional expression.
    #>
    param(
        [string]$SqlCmdExe,
        [string]$ServerInstance,
        [string]$DatabaseName,
        [string]$DbUser     = '',
        [string]$DbPassword = ''
    )
    $query = @'
SELECT CASE
    WHEN OBJECT_ID(N'dbo.SchemaVersion') IS NULL THEN NULL
    ELSE (SELECT TOP 1 Version FROM dbo.SchemaVersion ORDER BY AppliedAt DESC)
END AS Version
'@
    $rows = Invoke-SqlQuery `
        -SqlCmdExe      $SqlCmdExe `
        -ServerInstance $ServerInstance `
        -DatabaseName   $DatabaseName `
        -Query          $query `
        -DbUser         $DbUser `
        -DbPassword     $DbPassword
    if (-not $rows) { return $null }
    $value = ($rows[0]).Trim()
    return if ($value -eq 'NULL') { $null } else { $value }
}

# ---------------------------------------------------------------------------
# Connection string generator (for .env output)
# ---------------------------------------------------------------------------

function Get-ConnectionString {
    param(
        [string]$ServerInstance,
        [string]$DatabaseName,
        [string]$DbUser,
        [string]$DbPassword,
        [string]$Driver = 'ODBC Driver 18 for SQL Server'
    )
    $addr = Split-ServerInstance $ServerInstance
    return "DRIVER={$Driver};SERVER=$($addr.Host),$($addr.Port);DATABASE=$DatabaseName;UID=$DbUser;PWD=$DbPassword;Encrypt=no;TrustServerCertificate=yes;Connection Timeout=10;"
}

Export-ModuleMember -Function * -Variable TEMPLATE_DB_NAME
