$ErrorActionPreference = 'Stop'
$taskBuildDir = Split-Path -Parent $PSCommandPath
$taskFiles = Get-Content -LiteralPath (Join-Path $taskBuildDir 'docx_outputs.json') -Raw | ConvertFrom-Json
$taskQaDir = Join-Path $taskBuildDir 'qa'
New-Item -ItemType Directory -Path $taskQaDir -Force | Out-Null
$taskWord = New-Object -ComObject Word.Application
try {
    $taskWord.Visible = $false
    $taskWord.DisplayAlerts = 0
    foreach ($taskFile in $taskFiles) {
        $taskDoc = $null
        try {
            $taskDoc = $taskWord.Documents.Open([string]$taskFile, $false, $true)
            $taskDoc.Repaginate()
            $taskPdf = Join-Path $taskQaDir (([System.IO.Path]::GetFileNameWithoutExtension($taskFile)) + '.pdf')
            $taskDoc.ExportAsFixedFormat($taskPdf, 17)
            Write-Output "Rendered $taskPdf"
        } finally {
            if ($null -ne $taskDoc) { $taskDoc.Close(0); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc) }
        }
    }
} finally {
    $taskWord.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskWord)
}
