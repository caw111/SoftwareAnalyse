$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path '.').Path
$taskApp=$null
$taskDeck=$null
try {
 $taskApp=New-Object -ComObject PowerPoint.Application
 $taskDeck=$taskApp.Presentations.Open((Join-Path $taskRoot 'Submit\第9组-第三次作业-需求分析\汇报材料\02-需求分析汇报.pptx'),$true,$false,$false)
 $taskDeck.SaveAs((Join-Path $taskRoot '.report-build\third-submit\deck-native.pdf'),32)
 Write-Output ('Slides: '+$taskDeck.Slides.Count)
} finally {
 if($null -ne $taskDeck){$taskDeck.Close()}
 if($null -ne $taskApp){$taskApp.Quit()}
}
