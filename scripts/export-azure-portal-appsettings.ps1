param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('server2', 'fastapi_community', 'server3')]
    [string]$Service,

    [Parameter(Mandatory = $false)]
    [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    return Split-Path -Parent $scriptDir
}

function Get-ServiceEnvPath([string]$repoRoot, [string]$service) {
    switch ($service) {
        'server2' { return Join-Path $repoRoot 'server2/.env' }
        'fastapi_community' { return Join-Path $repoRoot 'FASTAPI_COMMUNITY/.env' }
        'server3' { return Join-Path $repoRoot 'server3/.env' }
        default { throw "Unsupported service: $service" }
    }
}

function Parse-EnvFile([string]$envPath) {
    if (-not (Test-Path $envPath)) {
        throw "Env file not found: $envPath"
    }

    $settings = [ordered]@{}
    $lines = Get-Content -Path $envPath

    foreach ($rawLine in $lines) {
        $line = $rawLine.Trim()
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        if ($line.StartsWith('#')) { continue }

        $idx = $line.IndexOf('=')
        if ($idx -lt 1) { continue }

        $key = $line.Substring(0, $idx).Trim()
        $value = $line.Substring($idx + 1)

        if ([string]::IsNullOrWhiteSpace($key)) { continue }
        $settings[$key] = $value
    }

    return $settings
}

$repoRoot = Get-RepoRoot
$envPath = Get-ServiceEnvPath -repoRoot $repoRoot -service $Service
$settings = Parse-EnvFile -envPath $envPath

# Azure Portal App Settings Advanced Edit format:
# [
#   {"name":"KEY","value":"VALUE","slotSetting":false},
#   ...
# ]
$portalArray = @()
foreach ($k in $settings.Keys) {
    $portalArray += [PSCustomObject]@{
        name = $k
        value = $settings[$k]
        slotSetting = $false
    }
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot ("deploy/azure/{0}.portal-appsettings.json" -f $Service)
}

$outDir = Split-Path -Parent $OutputPath
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$portalArray | ConvertTo-Json -Depth 6 | Set-Content -Path $OutputPath -Encoding UTF8
Write-Output "Exported Azure Portal app settings JSON for $Service to: $OutputPath"
