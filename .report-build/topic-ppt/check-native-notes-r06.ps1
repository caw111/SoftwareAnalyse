param([string]$Revision='r06')
$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path -LiteralPath '.').Path
$taskPath=Join-Path $taskRoot ".report-build\topic-ppt\validated-$Revision\main.pptx"
$taskApp=$null
$taskPres=$null
try {
    $taskApp=New-Object -ComObject PowerPoint.Application
    $taskApp.DisplayAlerts=1
    $taskPres=$taskApp.Presentations.Open($taskPath,$true,$false,$false)
    if ($taskPres.Slides.Count -ne 13) {throw 'Unexpected slide count'}
    $taskCount=0
    foreach ($taskSlide in $taskPres.Slides) {
        $taskText=''
        foreach ($taskShape in $taskSlide.NotesPage.Shapes) {
            if ($taskShape.HasTextFrame -and $taskShape.TextFrame.HasText) {
                $taskText+=$taskShape.TextFrame.TextRange.Text
            }
        }
        if (-not $taskText.Contains('演讲稿')) {throw ('Missing speech on slide '+$taskSlide.SlideIndex)}
        $taskCount++
    }
    Write-Output ('Native PowerPoint opened and read speaker scripts on '+$taskCount+' slides.')
} finally {
    if ($null -ne $taskPres) {$taskPres.Close()}
    if ($null -ne $taskApp) {$taskApp.Quit()}
}
