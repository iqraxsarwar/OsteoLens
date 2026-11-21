param(
    [string]$Python = (Join-Path $env:USERPROFILE 'OsteoLens-rag-env\Scripts\python.exe'),
    [string]$Cloudflared = (Join-Path $PSScriptRoot '..\..\OsteoLens-work\tools\cloudflared.exe')
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Python environment not found. Supply -Python with the configured environment executable.' }
if (-not (Test-Path -LiteralPath $Cloudflared)) { throw 'Download the official Cloudflare helper and supply its path with -Cloudflared. See DEPLOYMENT.md.' }
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
& $Python (Join-Path $PSScriptRoot 'start_public_demo.py') --cloudflared $Cloudflared
