# Deterministically render the hand-drawn SVG to PNG and a multi-resolution Windows ICO.
# This renderer intentionally supports the rect/path/circle subset used by zhihui.svg.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationCore,WindowsBase
$assetDir = Join-Path (Split-Path $PSScriptRoot) 'frontend\AcademicDesktop\Assets'
[xml]$svg = Get-Content -LiteralPath (Join-Path $assetDir 'zhihui.svg') -Raw
$visual = [System.Windows.Media.DrawingVisual]::new()
$context = $visual.RenderOpen()
foreach ($shape in $svg.DocumentElement.ChildNodes) {
    if ($shape -isnot [System.Xml.XmlElement]) { continue }
    $fill = $null
    if ($shape.GetAttribute('fill') -notin @('', 'none')) { $fill = [System.Windows.Media.BrushConverter]::new().ConvertFromString($shape.GetAttribute('fill')) }
    $pen = $null
    if ($shape.HasAttribute('stroke')) {
        $pen = [System.Windows.Media.Pen]::new([System.Windows.Media.BrushConverter]::new().ConvertFromString($shape.GetAttribute('stroke')), [double]$shape.GetAttribute('stroke-width'))
        $pen.StartLineCap = $pen.EndLineCap = [System.Windows.Media.PenLineCap]::Round
        $pen.LineJoin = [System.Windows.Media.PenLineJoin]::Round
    }
    switch ($shape.LocalName) {
        'rect' {
            $rect = [System.Windows.Rect]::new([double]$shape.GetAttribute('x'),[double]$shape.GetAttribute('y'),[double]$shape.GetAttribute('width'),[double]$shape.GetAttribute('height'))
            $context.DrawRoundedRectangle($fill,$pen,$rect,[double]$shape.GetAttribute('rx'),[double]$shape.GetAttribute('rx'))
        }
        'path' { $context.DrawGeometry($fill,$pen,[System.Windows.Media.Geometry]::Parse($shape.GetAttribute('d'))) }
        'circle' {
            $center = [System.Windows.Point]::new([double]$shape.GetAttribute('cx'),[double]$shape.GetAttribute('cy'))
            $context.DrawEllipse($fill,$pen,$center,[double]$shape.GetAttribute('r'),[double]$shape.GetAttribute('r'))
        }
        default { throw "Unsupported SVG element: $($shape.LocalName)" }
    }
}
$context.Close()
$sizes = @(16,20,24,32,40,48,64,128,256)
$frames = @()
foreach ($size in $sizes) {
    $scaledVisual = [System.Windows.Media.DrawingVisual]::new()
    $scaledContext = $scaledVisual.RenderOpen()
    $scaledContext.PushTransform([System.Windows.Media.ScaleTransform]::new($size/256.0,$size/256.0))
    $scaledContext.DrawDrawing($visual.Drawing)
    $scaledContext.Pop()
    $scaledContext.Close()
    $bitmap = [System.Windows.Media.Imaging.RenderTargetBitmap]::new($size,$size,96,96,[System.Windows.Media.PixelFormats]::Pbgra32)
    $bitmap.Render($scaledVisual)
    $encoder = [System.Windows.Media.Imaging.PngBitmapEncoder]::new()
    $encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
    $stream = [System.IO.MemoryStream]::new()
    $encoder.Save($stream)
    $frames += ,$stream.ToArray()
    $stream.Dispose()
}
[System.IO.File]::WriteAllBytes((Join-Path $assetDir 'zhihui.png'),$frames[-1])
$iconStream = [System.IO.File]::Create((Join-Path $assetDir 'zhihui.ico'))
$writer = [System.IO.BinaryWriter]::new($iconStream)
try {
    $writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]$sizes.Count)
    $offset = 6 + 16 * $sizes.Count
    for ($i=0; $i -lt $sizes.Count; $i++) {
        $side = if ($sizes[$i] -eq 256) { 0 } else { $sizes[$i] }
        $writer.Write([byte]$side); $writer.Write([byte]$side); $writer.Write([byte]0); $writer.Write([byte]0)
        $writer.Write([uint16]1); $writer.Write([uint16]32)
        $writer.Write([uint32]$frames[$i].Length); $writer.Write([uint32]$offset)
        $offset += $frames[$i].Length
    }
    foreach ($frame in $frames) { $writer.Write([byte[]]$frame) }
} finally { $writer.Dispose(); $iconStream.Dispose() }
Write-Host "Icon generated: $assetDir (16, 20, 24, 32, 40, 48, 64, 128, 256 px)"
