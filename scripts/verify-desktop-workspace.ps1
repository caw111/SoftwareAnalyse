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
if (!$endpoint.IsAbsoluteUri -or !$endpoint.IsLoopback -or $endpoint.Scheme -ne 'http' -or $endpoint.Port -ne 8080 -or $endpoint.AbsolutePath -ne '/' -or $endpoint.UserInfo -or $endpoint.Query -or $endpoint.Fragment) { throw 'Functional verification only permits the local HTTP demo API on port 8080; public servers and SSH production tunnels are not test targets.' }
$null = Invoke-RestMethod "$ApiUrl/api/reference" -TimeoutSec 5
$outputDir = Join-Path $projectRoot 'artifacts\verification-v0.5.1'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$previousApi = $env:ACADEMIC_API_URL
$previousOutput = $env:ACADEMIC_SMOKE_OUTPUT
try {
    $env:ACADEMIC_API_URL = $ApiUrl
    foreach ($scenario in @(@{Name='public';Argument='--smoke'},@{Name='login';Argument='--login-smoke'},@{Name='workspace';Argument='--workspace-smoke'},@{Name='crawl';Argument='--crawl-smoke'})) {
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
    if ($null -eq $previousApi) { Remove-Item Env:ACADEMIC_API_URL -ErrorAction SilentlyContinue } else { $env:ACADEMIC_API_URL = $previousApi }
    if ($null -eq $previousOutput) { Remove-Item Env:ACADEMIC_SMOKE_OUTPUT -ErrorAction SilentlyContinue } else { $env:ACADEMIC_SMOKE_OUTPUT = $previousOutput }
}
