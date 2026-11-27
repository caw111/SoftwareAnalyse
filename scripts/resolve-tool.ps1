param(
    [Parameter(Mandatory)][ValidateSet('Java', 'Dotnet')][string]$Tool,
    [string]$Executable
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
$candidates = @()
if ($Executable) {
    $candidates = @($Executable)
} elseif ($Tool -eq 'Java') {
    if ($env:JAVA_HOME) { $candidates += Join-Path $env:JAVA_HOME 'bin/java.exe' }
    $command = Get-Command java -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }
    $candidates += 'D:/tool/java21/bin/java.exe'
} else {
    $command = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }
    if ($env:DOTNET_ROOT) { $candidates += Join-Path $env:DOTNET_ROOT 'dotnet.exe' }
    $candidates += Get-ChildItem -Path (Join-Path $projectRoot '.dotnet-home/sdk-*/dotnet.exe') -File -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -ExpandProperty FullName
}
foreach ($candidate in ($candidates | Select-Object -Unique)) {
    if (!(Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
    if ($Tool -eq 'Java') {
        $version = & $candidate --version 2>&1 | Out-String
        $compatible = $LASTEXITCODE -eq 0 -and $version -match '(?m)^(openjdk|java) 21\.'
    } else {
        $version = & $candidate --list-sdks 2>&1 | Out-String
        $compatible = $LASTEXITCODE -eq 0 -and $version -match '(?m)^9\.0\.'
    }
    if ($compatible) { return (Resolve-Path -LiteralPath $candidate).Path }
}
if ($Tool -eq 'Java') { throw 'Java 21 JDK was not found. Set JAVA_HOME or pass -JavaHome to the build/start script.' }
throw '.NET 9 SDK was not found. Install the SDK, set DOTNET_ROOT, or extract it under .dotnet-home/sdk-<version>. A runtime alone cannot build the desktop application.'
