param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('server2', 'fastapi_community', 'server3')]
    [string]$Service,

    [Parameter(Mandatory = $false)]
    [string]$OutputPath = '',

    [Parameter(Mandatory = $false)]
    [switch]$AsJson,

    [Parameter(Mandatory = $false)]
    [switch]$AsCliArgs
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

        # Keep exact value as written in .env (do not strip inline comments/secrets)
        $settings[$key] = $value
    }

    return $settings
}

$repoRoot = Get-RepoRoot
$envPath = Get-ServiceEnvPath -repoRoot $repoRoot -service $Service
$settings = Parse-EnvFile -envPath $envPath

if ($settings.Count -eq 0) {
    throw "No settings found in $envPath"
}

if (-not $AsJson -and -not $AsCliArgs) {
    $AsJson = $true
}

if ($AsJson) {
    $json = $settings | ConvertTo-Json -Depth 5
    if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        $OutputPath = Join-Path $repoRoot ("deploy/azure/{0}.appsettings.json" -f $Service)
    }

    $outDir = Split-Path -Parent $OutputPath
    if (-not (Test-Path $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }

    Set-Content -Path $OutputPath -Value $json -Encoding UTF8
    Write-Output "Exported JSON app settings for $Service to: $OutputPath"
}

if ($AsCliArgs) {
    $pairs = @()
    foreach ($k in $settings.Keys) {
        $pairs += ('{0}={1}' -f $k, $settings[$k])
    }

    $singleLine = $pairs -join ' '
    if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        Write-Output $singleLine
    } else {
        Set-Content -Path $OutputPath -Value $singleLine -Encoding UTF8
        Write-Output "Exported CLI settings args for $Service to: $OutputPath"
    }
}
