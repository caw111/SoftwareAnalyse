param([switch]$FrameworkDependent)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
$env:DOTNET_CLI_HOME = Join-Path $projectRoot '.dotnet-home'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$outputDir = Join-Path $projectRoot 'artifacts\windows-x64'
$selfContained = if ($FrameworkDependent) { 'false' } else { 'true' }
& dotnet publish (Join-Path $projectRoot 'frontend\AcademicDesktop\AcademicDesktop.csproj') -c Release -r win-x64 --self-contained $selfContained -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o $outputDir --nologo
if ($LASTEXITCODE -ne 0) { throw 'Desktop publish failed.' }
Write-Host "Windows build: $outputDir\AcademicDesktop.exe"
