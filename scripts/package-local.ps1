param([string]$JavaHome)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
$javaArguments = @{ Tool = 'Java' }
if ($JavaHome) { $javaArguments.Executable = Join-Path $JavaHome 'bin/java.exe' }
$java = & (Join-Path $PSScriptRoot 'resolve-tool.ps1') @javaArguments
$jlink = Join-Path (Split-Path $java) 'jlink.exe'
if (!(Test-Path -LiteralPath $jlink)) { throw 'Creating the local package requires a Java 21 JDK with jlink.' }
$jar = Join-Path $projectRoot 'backend/build/libs/academic-platform-api.jar'
$desktop = Join-Path $projectRoot 'artifacts/windows-x64/AcademicDesktop.exe'
if (!(Test-Path -LiteralPath $jar) -or !(Test-Path -LiteralPath $desktop)) { throw 'Build the API and publish the self-contained desktop application first.' }
$stage = Join-Path $projectRoot ('artifacts/local-package/' + [Guid]::NewGuid().ToString('N'))
$apiDirectory = Join-Path $stage 'backend/build/libs'
$desktopDirectory = Join-Path $stage 'frontend/AcademicDesktop/bin/Release/net9.0-windows'
$scriptsDirectory = Join-Path $stage 'scripts'
New-Item -ItemType Directory -Force -Path $apiDirectory,$desktopDirectory,$scriptsDirectory | Out-Null
Copy-Item -LiteralPath $jar -Destination $apiDirectory
Copy-Item -LiteralPath $desktop -Destination $desktopDirectory
foreach ($name in @('start-local.ps1','stop-local.ps1','resolve-tool.ps1')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination $scriptsDirectory
}
& $jlink --add-modules java.se,jdk.crypto.ec,jdk.unsupported,jdk.charsets,jdk.zipfs --strip-debug --no-header-files --no-man-pages --compress=2 --output (Join-Path $stage 'runtime')
if ($LASTEXITCODE -ne 0) { throw 'Bundled Java runtime creation failed.' }
$start = '@echo off' + "`r`n" + 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-local.ps1" -NoBuild -JavaHome "%~dp0runtime" -ApiUrl http://127.0.0.1:18082 -ManagementPort 18083' + "`r`n" + 'if errorlevel 1 pause' + "`r`n"
$stop = '@echo off' + "`r`n" + 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-local.ps1"' + "`r`n" + 'if errorlevel 1 pause' + "`r`n"
[IO.File]::WriteAllText((Join-Path $stage 'Start.cmd'), $start, [Text.Encoding]::ASCII)
[IO.File]::WriteAllText((Join-Path $stage 'Stop.cmd'), $stop, [Text.Encoding]::ASCII)
$instructions = @'
Academic Platform - local Windows x64 package

Extract the entire ZIP to a writable folder, then double-click Start.cmd.
The package includes the WPF desktop, Java API and Java runtime.
No SDK, Java installation, Docker or cloud server is required.
The local API uses 127.0.0.1:18082 and management uses 127.0.0.1:18083.
Use Stop.cmd to stop the local API after closing the desktop.
Keep backend/data to preserve your local database across restarts.

Local demonstration accounts: admin / researcher / reader
Password: DemoPass2026!
The initial 64 records are explicitly marked synthetic data.
'@
[IO.File]::WriteAllText((Join-Path $stage 'README.txt'), $instructions, [Text.Encoding]::UTF8)
$archive = Join-Path $projectRoot 'artifacts/AcademicPlatform-local-windows-x64.zip'
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $archive -Force
$hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText(($archive + '.sha256'), "$hash  AcademicPlatform-local-windows-x64.zip`n", [Text.Encoding]::ASCII)
Write-Host "Standalone local package: $archive"
