param([string]$Match = '', [switch]$RevisedOnly, [switch]$FinalLayoutOnly)
$ErrorActionPreference = 'Stop'
$taskBuildDir = Split-Path -Parent $PSCommandPath
$taskFiles = Get-Content -LiteralPath (Join-Path $taskBuildDir 'outputs.json') -Encoding UTF8 | ConvertFrom-Json
if ($Match) { $taskFiles = @($taskFiles | Where-Object { $_ -like "*$Match*" }) }
if ($RevisedOnly) { $taskFiles = @($taskFiles | Where-Object { $_ -like '*SPEC*' -or $_ -like '*需求条目*' -or $_ -like '*数据源*' }) }
if ($FinalLayoutOnly) { $taskFiles = @($taskFiles | Where-Object { $_ -like '*SPEC*' -or $_ -like '*SRS*' -or $_ -like '*修改说明*' -or $_ -like '*自查清单*' }) }
$taskQaDir = Join-Path $taskBuildDir 'qa'
New-Item -ItemType Directory -Path $taskQaDir -Force | Out-Null
$taskWord = New-Object -ComObject Word.Application
$taskWord.Visible = $false
$taskWord.DisplayAlerts = 0
$taskWord.Options.UpdateLinksAtOpen = $false
try {
    foreach ($taskFile in $taskFiles) {
        $taskDoc = $null
        try {
            $taskDoc = $taskWord.Documents.Open($taskFile, $false, $false)
            $taskDoc.Fields.Update() | Out-Null
            foreach ($taskToc in $taskDoc.TablesOfContents) { $taskToc.Update() }
            $taskDoc.Repaginate()
            foreach ($taskToc in $taskDoc.TablesOfContents) { $taskToc.UpdatePageNumbers() }
            $taskDoc.Save()
            $taskPdf = Join-Path $taskQaDir ([System.IO.Path]::GetFileNameWithoutExtension($taskFile) + '.pdf')
            $taskDoc.ExportAsFixedFormat($taskPdf, 17)
            Write-Output ("FINALIZED " + [System.IO.Path]::GetFileName($taskFile) + " pages=" + $taskDoc.ComputeStatistics(2))
        } finally {
            if ($taskDoc) { $taskDoc.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc) }
        }
    }
} finally {
    $taskWord.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskWord)
}
