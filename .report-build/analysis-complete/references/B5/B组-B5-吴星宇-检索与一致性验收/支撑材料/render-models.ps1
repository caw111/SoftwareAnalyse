param([Parameter(Mandatory=$true)][string]$PlantUmlJar)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$jarPath = (Resolve-Path -LiteralPath $PlantUmlJar).Path
Push-Location -LiteralPath $taskRoot
try {
    & java '-Djava.awt.headless=true' -jar $jarPath -charset UTF-8 -tpng -o '..' '07-建模源文件/*.puml'
    if ($LASTEXITCODE -ne 0) { throw 'PlantUML rendering failed.' }
} finally {
    Pop-Location
}
