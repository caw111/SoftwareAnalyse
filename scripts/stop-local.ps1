$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
$pidFile = Join-Path $projectRoot 'artifacts\local-api.pid'
if (!(Test-Path -LiteralPath $pidFile)) { Write-Host 'No API process started by start-local.ps1 was recorded.'; return }
$apiProcessId = [int](Get-Content -LiteralPath $pidFile)
$apiProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$apiProcessId"
if (!$apiProcess) { Write-Host 'Recorded API process has already exited.'; return }
$expectedRuntime = Join-Path $projectRoot 'artifacts\runtime\api-'
if ($apiProcess.Name -ne 'java.exe' -or !$apiProcess.CommandLine.Contains($expectedRuntime)) { throw 'PID no longer matches this project runtime; refusing to stop another process.' }
Stop-Process -Id $apiProcessId
Write-Host 'Local API stopped. Database files and Docker containers were preserved.'
