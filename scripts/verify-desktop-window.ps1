param([string]$Exe = '', [string]$Output = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
if (!$Exe) { $Exe = Join-Path $projectRoot 'artifacts\windows-x64\AcademicDesktop.exe' }
if (!$Output) { $Output = Join-Path $projectRoot 'artifacts\window-controls.json' }
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class DesktopWindowCheck {
  [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left,Top,Right,Bottom; }
  [StructLayout(LayoutKind.Sequential)] public struct Point { public int X,Y; }
  [StructLayout(LayoutKind.Sequential)] public struct MonitorInfo { public int Size; public Rect Monitor,Work; public uint Flags; }
  [StructLayout(LayoutKind.Sequential)] public struct TitleInfo {
    public int Size; public Rect Title;
    [MarshalAs(UnmanagedType.ByValArray,SizeConst=6)] public uint[] States;
    [MarshalAs(UnmanagedType.ByValArray,SizeConst=6)] public Rect[] Buttons;
  }
  [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd,out Rect rect);
  [DllImport("user32.dll")] public static extern bool IsZoomed(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern uint GetDpiForWindow(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern IntPtr MonitorFromWindow(IntPtr hwnd,uint flags);
  [DllImport("user32.dll",CharSet=CharSet.Auto)] public static extern bool GetMonitorInfo(IntPtr monitor,ref MonitorInfo info);
  [DllImport("user32.dll",EntryPoint="GetWindowLongPtrW")] public static extern IntPtr GetWindowLongPtr(IntPtr hwnd,int index);
  [DllImport("user32.dll",EntryPoint="SendMessageW")] public static extern IntPtr Send(IntPtr hwnd,uint message,IntPtr wParam,IntPtr lParam);
  [DllImport("user32.dll",EntryPoint="SendMessageW")] public static extern IntPtr ReadTitle(IntPtr hwnd,uint message,IntPtr wParam,ref TitleInfo info);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hwnd,int command);
  [DllImport("user32.dll")] public static extern bool GetCursorPos(out Point point);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags,uint dx,uint dy,uint data,UIntPtr extra);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd,IntPtr dc,uint flags);
}
'@
function Wait-Until([scriptblock]$Condition, [string]$Failure) {
    $deadline = (Get-Date).AddSeconds(10)
    while (!( & $Condition )) {
        if ((Get-Date) -gt $deadline) { throw $Failure }
        Start-Sleep -Milliseconds 100
    }
}
function Read-Rect([IntPtr]$Handle) {
    $rect = [DesktopWindowCheck+Rect]::new()
    if (![DesktopWindowCheck]::GetWindowRect($Handle,[ref]$rect)) { throw 'Cannot read window bounds.' }
    return $rect
}
function Read-Title([IntPtr]$Handle) {
    $title = [DesktopWindowCheck+TitleInfo]::new()
    $title.Size = [Runtime.InteropServices.Marshal]::SizeOf($title)
    $title.States = [uint32[]]::new(6); $title.Buttons = [DesktopWindowCheck+Rect[]]::new(6)
    [void][DesktopWindowCheck]::ReadTitle($Handle,0x033F,[IntPtr]::Zero,[ref]$title)
    return $title
}
function Click-Point([int]$X,[int]$Y) {
    [void][DesktopWindowCheck]::SetCursorPos($X,$Y)
    [DesktopWindowCheck]::mouse_event(0x0002,0,0,0,[UIntPtr]::Zero)
    [DesktopWindowCheck]::mouse_event(0x0004,0,0,0,[UIntPtr]::Zero)
}
function Click-CaptionButton([IntPtr]$Handle,[int]$Index) {
    $title=Read-Title $Handle
    $rect=$title.Buttons[$Index]
    if (($title.States[$Index] -band 0x18001) -ne 0 -or $rect.Right -le $rect.Left) { throw "Native caption button $Index is unavailable." }
    Click-Point (($rect.Left+$rect.Right)/2) (($rect.Top+$rect.Bottom)/2)
}
function Save-NativeWindow([IntPtr]$Handle,[string]$Path) {
    $rect=Read-Rect $Handle
    $bitmap=[System.Drawing.Bitmap]::new($rect.Right-$rect.Left,$rect.Bottom-$rect.Top)
    $graphics=[System.Drawing.Graphics]::FromImage($bitmap)
    $dc=$graphics.GetHdc()
    try { if (![DesktopWindowCheck]::PrintWindow($Handle,$dc,2)) { throw 'Native window capture failed.' } }
    finally { $graphics.ReleaseHdc($dc); $graphics.Dispose() }
    try { $bitmap.Save($Path,[System.Drawing.Imaging.ImageFormat]::Png) } finally { $bitmap.Dispose() }
}

$oldDpi=[DesktopWindowCheck]::SetThreadDpiAwarenessContext([IntPtr](-4))
$oldCursor=[DesktopWindowCheck+Point]::new()
[void][DesktopWindowCheck]::GetCursorPos([ref]$oldCursor)
$windowProcess=$null
try {
    # This explicitly tests a visible interactive app: native title buttons and real mouse dragging.
    $windowProcess=Start-Process -FilePath $Exe -PassThru
    Wait-Until { $windowProcess.Refresh(); $windowProcess.MainWindowHandle -ne [IntPtr]::Zero } 'No main window appeared.'
    $handle=$windowProcess.MainWindowHandle
    $windowDpi=[DesktopWindowCheck]::GetDpiForWindow($handle)
    [void][DesktopWindowCheck]::SetForegroundWindow($handle)
    Wait-Until { [DesktopWindowCheck]::IsZoomed($handle) } 'Startup did not maximize the window.'
    $monitor=[DesktopWindowCheck+MonitorInfo]::new(); $monitor.Size=[Runtime.InteropServices.Marshal]::SizeOf($monitor)
    [void][DesktopWindowCheck]::GetMonitorInfo([DesktopWindowCheck]::MonitorFromWindow($handle,2),[ref]$monitor)
    $style=[DesktopWindowCheck]::GetWindowLongPtr($handle,-16).ToInt64()
    if (($style -band 0xCF0000) -ne 0xCF0000) { throw 'Missing native caption, resize frame or system buttons.' }
    $title=Read-Title $handle
    foreach ($index in @(2,3,5)) {
        $button=$title.Buttons[$index]
        if (($title.States[$index] -band 0x18001) -ne 0 -or $button.Right -le $button.Left -or $button.Top -lt $monitor.Work.Top -or $button.Bottom -gt $monitor.Work.Bottom -or $button.Left -lt $monitor.Work.Left -or $button.Right -gt $monitor.Work.Right) { throw "Caption button $index is not visible inside the work area." }
    }
    Click-CaptionButton $handle 3
    Wait-Until { ![DesktopWindowCheck]::IsZoomed($handle) } 'Restore button did not restore the window.'
    $restored=Read-Rect $handle
    if ($restored.Left -lt $monitor.Work.Left -or $restored.Top -lt $monitor.Work.Top -or $restored.Right -gt $monitor.Work.Right -or $restored.Bottom -gt $monitor.Work.Bottom) { throw 'Restored window extends outside the work area.' }

    $title=Read-Title $handle
    $captionX=$title.Title.Left+200; $captionY=[int](($title.Title.Top+$title.Title.Bottom)/2)
    $packed=[IntPtr](($captionY -shl 16) -bor ($captionX -band 0xffff))
    $hit=[DesktopWindowCheck]::Send($handle,0x0084,[IntPtr]::Zero,$packed).ToInt32()
    if ($hit -ne 2) { throw "Caption hit test returned $hit instead of HTCAPTION." }
    [void][DesktopWindowCheck]::SetCursorPos($captionX,$captionY)
    [DesktopWindowCheck]::mouse_event(0x0002,0,0,0,[UIntPtr]::Zero)
    Start-Sleep -Milliseconds 120
    [void][DesktopWindowCheck]::SetCursorPos(($captionX+40),($captionY+24))
    Start-Sleep -Milliseconds 150
    [DesktopWindowCheck]::mouse_event(0x0004,0,0,0,[UIntPtr]::Zero)
    Wait-Until { $moved=Read-Rect $handle; $moved.Left -ne $restored.Left -or $moved.Top -ne $restored.Top } 'Dragging the native title bar did not move the window.'
    $moved=Read-Rect $handle

    Click-CaptionButton $handle 3
    Wait-Until { [DesktopWindowCheck]::IsZoomed($handle) } 'Maximize button did not maximize the window.'
    Click-CaptionButton $handle 2
    Wait-Until { [DesktopWindowCheck]::IsIconic($handle) } 'Minimize button did not minimize the window.'
    [void][DesktopWindowCheck]::ShowWindow($handle,9)
    [void][DesktopWindowCheck]::SetForegroundWindow($handle)
    Wait-Until { ![DesktopWindowCheck]::IsIconic($handle) } 'Could not restore minimized window.'
    if (![DesktopWindowCheck]::IsZoomed($handle)) { Click-CaptionButton $handle 3 }
    Wait-Until { [DesktopWindowCheck]::IsZoomed($handle) } 'Final window is not maximized.'
    Start-Sleep -Milliseconds 300
    Save-NativeWindow $handle ([IO.Path]::ChangeExtension($Output,'.png'))
    $icon=[DesktopWindowCheck]::Send($handle,0x007F,[IntPtr]1,[IntPtr]::Zero)
    if ($icon -eq [IntPtr]::Zero) { throw 'Window icon is missing.' }
    Click-CaptionButton $handle 5
    Wait-Until { $windowProcess.Refresh(); $windowProcess.HasExited } 'Close button did not exit the application.'
    $result=[ordered]@{
        ok=$true; dpi=$windowDpi; workArea=$monitor.Work;
        startupMaximized=$true; nativeStyle=('0x{0:X}' -f $style);
        captionButtonsVisible=$true; restoreBounds=$restored; dragBounds=$moved;
        dragPassed=$true; maximizePassed=$true; minimizePassed=$true; closePassed=$true;
        iconPresent=$true; version=(Get-Item -LiteralPath $Exe).VersionInfo.FileVersion;
        tests='Real titlebar mouse drag and native caption button clicks; no API load test.'
    }
    $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Output -Encoding utf8
    $result | ConvertTo-Json -Depth 6
} finally {
    [DesktopWindowCheck]::mouse_event(0x0004,0,0,0,[UIntPtr]::Zero)
    [void][DesktopWindowCheck]::SetCursorPos($oldCursor.X,$oldCursor.Y)
    [void][DesktopWindowCheck]::SetThreadDpiAwarenessContext($oldDpi)
    if ($windowProcess -and !$windowProcess.HasExited) { [void]$windowProcess.CloseMainWindow() }
}
