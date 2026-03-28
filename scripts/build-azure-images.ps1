param(
    [switch]$SkipCommunityWheelhouse,
    [switch]$SkipServer3,
    [switch]$SkipCommunity
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$communityRoot = Join-Path $repoRoot "FASTAPI_COMMUNITY"
$communityWheelhouse = Join-Path $communityRoot ".docker-wheelhouse"
$communityRequirements = Join-Path $communityRoot "requirements.prod.txt"

function Invoke-Step {
    param(
        [string]$Message,
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host "==> $Message"
    & $Action
}

if (-not $SkipCommunity) {
    if (-not $SkipCommunityWheelhouse) {
        Invoke-Step "Preparing FASTAPI_COMMUNITY wheelhouse" {
            if (Test-Path $communityWheelhouse) {
                Get-ChildItem -Path $communityWheelhouse -Force |
                    Where-Object { $_.Name -ne ".gitkeep" } |
                    Remove-Item -Recurse -Force
            } else {
                New-Item -ItemType Directory -Path $communityWheelhouse | Out-Null
            }

            docker run --rm `
                -v "${communityRoot}:/workspace/FASTAPI_COMMUNITY" `
                -v "${communityWheelhouse}:/wheelhouse" `
                python:3.11-slim `
                sh -c "python -m pip wheel --wheel-dir /wheelhouse -r /workspace/FASTAPI_COMMUNITY/requirements.prod.txt"
        }
    }

    Invoke-Step "Building FASTAPI_COMMUNITY Azure image" {
        docker build `
            -f FASTAPI_COMMUNITY/app/Dockerfile `
            -t barise_communtiy_server_2:latest `
            -t chatmessagefastapicom.azurecr.io/barise_communtiy_server_2:latest `
            $repoRoot
    }
}

if (-not $SkipServer3) {
    Invoke-Step "Building server3 Azure image" {
        docker build `
            -f server3/Dockerfile `
            -t generateddocker/server3-chat_messaging:latest `
            -t chatmessagefastapicom.azurecr.io/generateddocker/server3-chat_messaging:latest `
            $repoRoot
    }
}

Write-Host ""
Write-Host "Build workflow completed."
