$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path '.').Path
$taskOut=Join-Path $taskRoot 'Submit\第9组-第三次作业-需求分析'
$taskWord=$null
$taskDocument=$null
try {
 $taskWord=New-Object -ComObject Word.Application
 $taskWord.Visible=$false
 $taskWord.DisplayAlerts=0
 $taskDocument=$taskWord.Documents.Open((Join-Path $taskOut '01-需求分析报告.docx'),$false,$true)
 $taskDocument.Repaginate()
 $taskDocument.ExportAsFixedFormat((Join-Path $taskOut '01-需求分析报告.pdf'),17)
 Write-Output ('Word pages: '+$taskDocument.ComputeStatistics(2))
} finally {
 if($null -ne $taskDocument){$taskDocument.Close(0)}
 if($null -ne $taskWord){$taskWord.Quit()}
}
