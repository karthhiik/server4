param(
    [Parameter(Mandatory = $false)]
    [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    return Split-Path -Parent $scriptDir
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
$serviceFiles = [ordered]@{
    server2 = Join-Path $repoRoot 'server2/.env'
    fastapi_community = Join-Path $repoRoot 'FASTAPI_COMMUNITY/.env'
    server3 = Join-Path $repoRoot 'server3/.env'
}

$manifest = [ordered]@{}
foreach ($service in $serviceFiles.Keys) {
    $manifest[$service] = Parse-EnvFile -envPath $serviceFiles[$service]
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot 'deploy/azure/combined-services.env.json'
}

$outDir = Split-Path -Parent $OutputPath
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$manifest | ConvertTo-Json -Depth 8 | Set-Content -Path $OutputPath -Encoding UTF8
Write-Output "Exported combined env manifest to: $OutputPath"
