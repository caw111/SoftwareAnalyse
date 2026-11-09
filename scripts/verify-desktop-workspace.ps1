param(
    [string]$ApiUrl = 'http://127.0.0.1:8080',
    [string]$Exe = '',
    [switch]$CheckWindowControls
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
if (!$Exe) { $Exe = Join-Path $projectRoot 'artifacts\windows-x64\AcademicDesktop.exe' }
if (!(Test-Path -LiteralPath $Exe)) { throw 'Publish the desktop executable first: scripts/publish-desktop.ps1' }
$endpoint = [Uri]$ApiUrl
if (!$endpoint.IsAbsoluteUri -or !$endpoint.IsLoopback) { throw 'This functional check creates synthetic accounts and only permits a local demo API.' }
$null = Invoke-RestMethod "$ApiUrl/api/reference" -TimeoutSec 5
$outputDir = Join-Path $projectRoot 'artifacts\verification-v0.2'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$previousApi = $env:ACADEMIC_API_URL
$previousOutput = $env:ACADEMIC_SMOKE_OUTPUT
try {
    $env:ACADEMIC_API_URL = $ApiUrl
    foreach ($scenario in @(@{Name='public';Argument='--smoke'},@{Name='login';Argument='--login-smoke'},@{Name='workspace';Argument='--workspace-smoke'})) {
        $env:ACADEMIC_SMOKE_OUTPUT = Join-Path $outputDir ($scenario.Name + '.json')
        # These are real interactive WPF functional checks; all API requests are sequential.
        $started = Get-Date
        $checkProcess = Start-Process -FilePath $Exe -ArgumentList $scenario.Argument -PassThru
        if (!$checkProcess.WaitForExit(60000)) {
            [void]$checkProcess.CloseMainWindow()
            throw "$($scenario.Name) verification timed out. Inspect its window and API logs."
        }
        if ($checkProcess.ExitCode -ne 0 -or !(Test-Path -LiteralPath $env:ACADEMIC_SMOKE_OUTPUT)) { throw "$($scenario.Name) did not produce a verification result." }
        if ((Get-Item -LiteralPath $env:ACADEMIC_SMOKE_OUTPUT).LastWriteTime -lt $started) { throw 'Stale verification result.' }
        $result = Get-Content -LiteralPath $env:ACADEMIC_SMOKE_OUTPUT -Raw | ConvertFrom-Json
        if (!$result.ok) { throw ($result | ConvertTo-Json -Depth 8) }
        Write-Host "$($scenario.Name): PASS"
    }
    if ($CheckWindowControls) { & (Join-Path $PSScriptRoot 'verify-desktop-window.ps1') -Exe $Exe -Output (Join-Path $outputDir 'native-window.json') }
    Write-Host "Functional verification: $outputDir (no load test)."
} finally {
    [Environment]::SetEnvironmentVariable('ACADEMIC_API_URL', $previousApi, 'Process')
    [Environment]::SetEnvironmentVariable('ACADEMIC_SMOKE_OUTPUT', $previousOutput, 'Process')
}
