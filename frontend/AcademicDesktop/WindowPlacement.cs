using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace AcademicDesktop;

/// <summary>Keep both the initial maximized window and its restore bounds on the current monitor.</summary>
internal static class WindowPlacement
{
    public static void StartMaximized(Window window)
    {
        var handle = new WindowInteropHelper(window).Handle;
        var monitor = MonitorFromWindow(handle, 2); // MONITOR_DEFAULTTONEAREST
        var info = new MonitorInfo { Size = Marshal.SizeOf<MonitorInfo>() };
        if (GetMonitorInfo(monitor, ref info))
        {
            var dpi = GetDpiForWindow(handle);
            double scale = dpi > 0 ? dpi / 96d : 1d;
            int workWidth = info.Work.Right - info.Work.Left;
            int workHeight = info.Work.Bottom - info.Work.Top;
            // These are outer-window bounds: native caption, borders and taskbar space count too.
            int width = Math.Max(1, (int)Math.Min(1440 * scale, workWidth * .92));
            int height = Math.Max(1, (int)Math.Min(920 * scale, workHeight * .90));
            window.MinWidth = Math.Min(960, width / scale);
            window.MinHeight = Math.Min(560, height / scale);
            window.Width = width / scale;
            window.Height = height / scale;
            SetWindowPos(handle, IntPtr.Zero,
                info.Work.Left + (workWidth - width) / 2,
                info.Work.Top + (workHeight - height) / 2,
                width, height, 0x0004 | 0x0010); // SWP_NOZORDER | SWP_NOACTIVATE
        }
        // Maximize, not borderless fullscreen: Windows owns drag, resize, system menu and buttons.
        window.WindowState = WindowState.Maximized;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct NativeRect { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)]
    private struct MonitorInfo { public int Size; public NativeRect Monitor, Work; public uint Flags; }
    [DllImport("user32.dll")]
    private static extern IntPtr MonitorFromWindow(IntPtr hwnd, uint flags);
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetMonitorInfo(IntPtr monitor, ref MonitorInfo info);
    [DllImport("user32.dll")]
    private static extern uint GetDpiForWindow(IntPtr hwnd);
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetWindowPos(IntPtr hwnd, IntPtr after, int x, int y, int width, int height, uint flags);
}
