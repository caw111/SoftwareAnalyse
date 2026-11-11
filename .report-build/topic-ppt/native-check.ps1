param([string]$Revision='r02')
$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path -LiteralPath '.').Path
$taskDeck=Join-Path $taskRoot ".report-build\topic-ppt\validated-$Revision\main.pptx"
$taskPdf=Join-Path $taskRoot ".report-build\topic-ppt\$Revision\main-native.pdf"
$taskApp=$null
$taskPresentation=$null
try {
    $taskApp=New-Object -ComObject PowerPoint.Application
    $taskApp.DisplayAlerts=1
    $taskPresentation=$taskApp.Presentations.Open($taskDeck,$true,$false,$false)
    Write-Output ('Native presentation opened; slides='+$taskPresentation.Slides.Count)
    $taskPresentation.SaveAs($taskPdf,32)
    Write-Output ('Native PDF exported: '+$taskPdf)
} finally {
    if ($null -ne $taskPresentation) {$taskPresentation.Close()}
    if ($null -ne $taskApp) {$taskApp.Quit()}
}
