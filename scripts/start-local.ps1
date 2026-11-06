param(
    [string]$JavaHome = 'D:\tool\java21',
    [string]$ApiUrl = 'http://127.0.0.1:8080',
    [switch]$UsePostgres,
    [switch]$NoBuild,
    [switch]$NoDesktop
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
$artifactDir = Join-Path $projectRoot 'artifacts'
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
if (!$NoBuild) { & (Join-Path $PSScriptRoot 'build.ps1') -JavaHome $JavaHome -SkipTests }
$desktop = Join-Path $projectRoot 'frontend\AcademicDesktop\bin\Release\net9.0-windows\AcademicDesktop.exe'
$jar = Join-Path $projectRoot 'backend\build\libs\academic-platform-api.jar'
if (!(Test-Path -LiteralPath $desktop) -or !(Test-Path -LiteralPath $jar)) { throw 'Build outputs are missing. Run scripts/build.ps1 first.' }
$healthy = $false
try { $null = Invoke-RestMethod "$ApiUrl/api/reference" -TimeoutSec 3; $healthy = $true } catch { }
if (!$healthy) {
    if ($ApiUrl -ne 'http://127.0.0.1:8080') { throw 'Remote API is unavailable. This script only starts a server for the default local address.' }
    $env:APP_DEMO = 'true'
    $env:DEMO_COUNT = '64'
    if ($UsePostgres) {
        if (!$env:DB_URL -or !$env:DB_USER -or !$env:DB_PASSWORD) { throw 'Set DB_URL, DB_USER and DB_PASSWORD before -UsePostgres.' }
    } else {
        $env:DB_URL = 'jdbc:h2:file:./data/academic;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DEFAULT_NULL_ORDERING=HIGH;NON_KEYWORDS=YEAR'
        $env:DB_USER = 'sa'; $env:DB_PASSWORD = ''
    }
    # Run an immutable copy: rebuilding a currently open executable jar can break lazy class loading.
    $runtimeDir = Join-Path $artifactDir 'runtime'
    New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
    $jarHash = (Get-FileHash -LiteralPath $jar -Algorithm SHA256).Hash.Substring(0, 16)
    $runtimeJar = Join-Path $runtimeDir "api-$jarHash.jar"
    if (!(Test-Path -LiteralPath $runtimeJar)) { Copy-Item -LiteralPath $jar -Destination $runtimeJar }
    $apiProcess = Start-Process -FilePath (Join-Path $JavaHome 'bin\java.exe') -ArgumentList @('-Xms128m','-Xmx512m','-jar', ('"' + $runtimeJar + '"')) -WorkingDirectory (Join-Path $projectRoot 'backend') -RedirectStandardOutput (Join-Path $artifactDir 'api.stdout.log') -RedirectStandardError (Join-Path $artifactDir 'api.stderr.log') -WindowStyle Hidden -PassThru
    $apiProcess.Id | Set-Content -LiteralPath (Join-Path $artifactDir 'local-api.pid')
    $deadline = (Get-Date).AddSeconds(90)
    do {
        Start-Sleep -Milliseconds 800
        if ($apiProcess.HasExited) { throw 'API exited. Inspect artifacts/api.stderr.log and artifacts/api.stdout.log.' }
        try { $health = Invoke-RestMethod 'http://127.0.0.1:8081/actuator/health/readiness' -TimeoutSec 2; $healthy = $health.status -eq 'UP' } catch { }
    } until ($healthy -or (Get-Date) -gt $deadline)
    if (!$healthy) { throw 'API readiness timed out. Inspect artifacts/api.stdout.log.' }
}
$env:ACADEMIC_API_URL = $ApiUrl
# The user invokes this script specifically to open the interactive desktop app.
if (!$NoDesktop) { Start-Process -FilePath $desktop }
Write-Host 'API ready. Local demo: admin / researcher / reader, password DemoPass2026!'
