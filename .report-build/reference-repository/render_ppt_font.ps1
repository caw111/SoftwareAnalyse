param([string]$Path, [string]$OutputDir)
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$taskPowerPoint=New-Object -ComObject PowerPoint.Application
$taskPresentation=$null
try {
    $taskPresentation=$taskPowerPoint.Presentations.Open($Path,$true,$false,$false)
    foreach ($taskSlide in $taskPresentation.Slides) {
        $taskSlide.Export((Join-Path $OutputDir ("slide-"+$taskSlide.SlideIndex+".png")),"PNG",1600,900)
    }
    Write-Output ("RENDERED "+$taskPresentation.Slides.Count+" slides")
} finally {
    if ($taskPresentation) { $taskPresentation.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskPresentation) }
    $taskPowerPoint.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskPowerPoint)
}
