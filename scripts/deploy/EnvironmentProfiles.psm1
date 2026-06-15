#Requires -Version 5.1
<#
.SYNOPSIS
    Per-environment deployment defaults for open_datEAUbase.

.DESCRIPTION
    Single source of truth mapping an environment name to the defaults the
    deploy scripts derive from it: database name, Windows service-name tag,
    listening ports, and whether dev/demo seed data may be loaded.

    Both Deploy-Database.ps1 and Deploy-OpenDateaubase.ps1 import this module so
    the database tier and the application tier stay in lock-step for a given
    environment.

    Because every service name, task name, port, log directory and database
    name is namespaced by environment, staging and production can be deployed
    side by side on a single host without colliding. Separate hosts are still
    recommended; co-tenancy is supported, not encouraged.

    To add a new tier (e.g. 'dev' that is allowed to load seed data), add one
    entry below and update the ValidateSet attributes in the deploy scripts.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:EnvironmentProfiles = @{
    staging = [pscustomobject]@{
        Name          = 'staging'
        ServiceTag    = 'Staging'                  # → OpenDateaubase-Staging-API, etc.
        DatabaseName  = 'open_dateaubase_staging'
        ApiPort       = '8010'
        AppPort       = '8511'
        ProxyPort     = '8080'
        AllowSeedData = $false                     # dev/demo seed never loaded into staging
    }
    production = [pscustomobject]@{
        Name          = 'production'
        ServiceTag    = 'Production'               # → OpenDateaubase-Production-API, etc.
        DatabaseName  = 'open_dateaubase_production'
        ApiPort       = '8000'
        AppPort       = '8501'
        ProxyPort     = '80'
        AllowSeedData = $false                     # dev/demo seed never loaded into production
    }
}

function Get-EnvironmentProfile {
    <#
    .SYNOPSIS
        Returns the derived-defaults object for an environment name.
    #>
    param(
        [Parameter(Mandatory)]
        [ValidateSet('staging', 'production')]
        [string]$Environment
    )
    return $script:EnvironmentProfiles[$Environment]
}

function Get-KnownEnvironments {
    <#
    .SYNOPSIS
        Returns the list of recognised environment names.
    #>
    return @($script:EnvironmentProfiles.Keys | Sort-Object)
}

Export-ModuleMember -Function *
