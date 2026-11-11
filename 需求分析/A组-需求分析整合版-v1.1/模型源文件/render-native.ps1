param(
    [string]$Version = 'v1.0',
    [string]$OutputName = 'report.pdf'
)
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath '.').Path
$taskDocPath = Join-Path $taskRoot "需求分析\A组-需求分析整合版-$Version\本组-需求分析报告.docx"
$taskPdfPath = Join-Path $taskRoot ".report-build\analysis-complete\render\$OutputName"
$taskWord = $null
$taskDocument = $null
try {
    $taskWord = New-Object -ComObject Word.Application
    $taskWord.Visible = $false
    $taskWord.DisplayAlerts = 0
    $taskDocument = $taskWord.Documents.Open($taskDocPath, $false, $true)
    $taskDocument.Repaginate()
    $taskDocument.ExportAsFixedFormat($taskPdfPath, 17)
    Write-Output "Native Word-compatible PDF exported: $taskPdfPath"
} finally {
    if ($null -ne $taskDocument) { $taskDocument.Close(0) }
    if ($null -ne $taskWord) { $taskWord.Quit() }
}
