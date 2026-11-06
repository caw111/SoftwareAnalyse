param(
    [string]$JavaHome = 'D:\tool\java21',
    [string]$Gradle = 'D:\tool\gradle\gradle-9.8.0\bin\gradle.bat',
    [switch]$SkipTests
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
$env:JAVA_HOME = $JavaHome
$env:GRADLE_USER_HOME = Join-Path $projectRoot '.gradle-user-home'
$env:DOTNET_CLI_HOME = Join-Path $projectRoot '.dotnet-home'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
if (!(Test-Path -LiteralPath $Gradle)) { $Gradle = Join-Path $projectRoot 'backend\gradlew.bat' }
Push-Location (Join-Path $projectRoot 'backend')
try {
    $tasks = @('bootJar')
    if (!$SkipTests) { $tasks += 'test' }
    & $Gradle @tasks
    if ($LASTEXITCODE -ne 0) { throw 'Backend build failed.' }
} finally { Pop-Location }
& dotnet build (Join-Path $projectRoot 'frontend\AcademicDesktop\AcademicDesktop.csproj') -c Release --nologo
if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed.' }
Write-Host 'Build completed. No load test was executed.'
