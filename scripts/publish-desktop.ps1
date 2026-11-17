param(
  [switch]$FrameworkDependent,
  [string]$NuGetConfig,
  [switch]$IsolateNuGetSettings,
  [switch]$Offline
)
$ErrorActionPreference = 'Stop'
if ($Offline -and $NuGetConfig) { throw 'Use either -Offline or -NuGetConfig.' }
$projectRoot = Split-Path $PSScriptRoot
$projectFile = Join-Path $projectRoot 'frontend\AcademicDesktop\AcademicDesktop.csproj'
$outputDir = Join-Path $projectRoot 'artifacts\windows-x64'
$selfContained = if ($FrameworkDependent) { 'false' } else { 'true' }
$environmentNames = @('DOTNET_CLI_HOME', 'DOTNET_CLI_TELEMETRY_OPTOUT', 'APPDATA', 'NUGET_PACKAGES')
$previousEnvironment = @{}
foreach ($name in $environmentNames) { $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
try {
  $env:DOTNET_CLI_HOME = Join-Path $projectRoot '.dotnet-home'
  $env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
  if ($Offline) {
    $NuGetConfig = Join-Path $projectRoot 'artifacts\nuget-offline.config'
    New-Item -ItemType Directory -Path (Split-Path $NuGetConfig) -Force | Out-Null
    [IO.File]::WriteAllText($NuGetConfig, '<?xml version="1.0" encoding="utf-8"?><configuration><packageSources><clear/></packageSources><fallbackPackageFolders><clear/></fallbackPackageFolders></configuration>', [Text.UTF8Encoding]::new($false))
  }
  if ($NuGetConfig) { $NuGetConfig = (Resolve-Path -LiteralPath $NuGetConfig).Path }
  if ($IsolateNuGetSettings) {
    # NuGet's proxy loader reads APPDATA even when RestoreConfigFile is explicit.
    # Scope this redirect to the publishing process; never edit the user's configuration.
    $publishRoaming = Join-Path $projectRoot 'artifacts\publish-user\Roaming'
    $publishSettings = Join-Path $publishRoaming 'NuGet\NuGet.Config'
    New-Item -ItemType Directory -Path (Split-Path $publishSettings) -Force | Out-Null
    if ($NuGetConfig) {
      if ([IO.Path]::GetFullPath($NuGetConfig) -ne [IO.Path]::GetFullPath($publishSettings)) {
        Copy-Item -LiteralPath $NuGetConfig -Destination $publishSettings -Force
      }
    } else {
      [IO.File]::WriteAllText($publishSettings, '<?xml version="1.0" encoding="utf-8"?><configuration><packageSources><clear/><add key="nuget.org" value="https://api.nuget.org/v3/index.json"/></packageSources></configuration>', [Text.UTF8Encoding]::new($false))
      $NuGetConfig = $publishSettings
    }
    $env:APPDATA = $publishRoaming
    $env:NUGET_PACKAGES = Join-Path $projectRoot '.dotnet-home\.nuget\packages'
  }
  $restoreArguments = @('restore', $projectFile, '-r', 'win-x64', "-p:SelfContained=$selfContained", '-p:PublishSingleFile=true', '--nologo')
  if ($NuGetConfig) { $restoreArguments += @('--configfile', $NuGetConfig) }
  if ($Offline) { $restoreArguments += @('-p:NuGetAudit=false', '--disable-parallel') }
  & dotnet @restoreArguments
  if ($LASTEXITCODE -ne 0) { throw 'Desktop restore failed.' }
  & dotnet publish $projectFile -c Release -r win-x64 --self-contained $selfContained --no-restore -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o $outputDir --nologo
  if ($LASTEXITCODE -ne 0) { throw 'Desktop publish failed.' }
  Write-Host "Windows build: $outputDir\AcademicDesktop.exe"
} finally {
  foreach ($name in $environmentNames) {
    if ($null -eq $previousEnvironment[$name]) { Remove-Item -LiteralPath ('Env:' + $name) -ErrorAction SilentlyContinue }
    else { [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process') }
  }
}
