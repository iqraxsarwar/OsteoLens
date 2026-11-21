$ErrorActionPreference = 'Stop'
$statePath = Join-Path $PSScriptRoot 'runtime\public-demo.json'
if (-not (Test-Path -LiteralPath $statePath)) { Write-Output 'No public demo state was found.'; exit }
$demoState = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
if (-not $demoState.launcher_pid) { Write-Output 'Public demo is already stopped.'; exit }
$demoProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$demoState.launcher_pid)"
if ($demoProcess) {
    if ($demoProcess.CommandLine -notmatch 'deploy[/\\]start_public_demo\.py') {
        throw 'Process identity does not match the public demo launcher; no process was stopped.'
    }
    # Stop only the verified launcher and the API/tunnel children it owns.
    & taskkill /PID ([string]$demoState.launcher_pid) /T /F
    if ($LASTEXITCODE -ne 0) { throw 'The public demo could not be stopped.' }
}
@{status='stopped'} | ConvertTo-Json | Set-Content -LiteralPath $statePath
Write-Output 'Public demo stopped. The separate local backend and Ollama were not stopped.'
