param(
    [string]$JavaHome,
    [string]$Gradle,
    [switch]$SkipTests
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
$javaArguments = @{ Tool = 'Java' }
if ($JavaHome) { $javaArguments.Executable = Join-Path $JavaHome 'bin/java.exe' }
$java = & (Join-Path $PSScriptRoot 'resolve-tool.ps1') @javaArguments
$env:JAVA_HOME = Split-Path (Split-Path $java)
$dotnet = & (Join-Path $PSScriptRoot 'resolve-tool.ps1') -Tool Dotnet
$env:GRADLE_USER_HOME = Join-Path $projectRoot '.gradle-user-home'
$env:DOTNET_CLI_HOME = Join-Path $projectRoot '.dotnet-home'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
if (!$Gradle) { $Gradle = Join-Path $projectRoot 'backend\gradlew.bat' }
if (!(Test-Path -LiteralPath $Gradle)) { throw "Gradle executable does not exist: $Gradle" }
Push-Location (Join-Path $projectRoot 'backend')
try {
    $tasks = @('bootJar')
    if (!$SkipTests) { $tasks += 'test' }
    & $Gradle @tasks
    if ($LASTEXITCODE -ne 0) { throw 'Backend build failed.' }
} finally { Pop-Location }
& $dotnet build (Join-Path $projectRoot 'frontend\AcademicDesktop\AcademicDesktop.csproj') -c Release --nologo
if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed.' }
Write-Host 'Build completed. No load test was executed.'
