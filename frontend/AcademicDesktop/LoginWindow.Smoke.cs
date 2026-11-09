using System.IO;
using System.Text.Json.Nodes;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

namespace AcademicDesktop;

public partial class LoginWindow
{
    /// <summary>
    /// Explicit functional check of real modal entry windows and the configured API.
    /// Creates one uniquely named ordinary account; never runs automatically or generates load.
    /// App owns application shutdown after this method completes.
    /// </summary>
    public static async Task RunLoginSmoke(string address)
    {
        string output = Environment.GetEnvironmentVariable("ACADEMIC_SMOKE_OUTPUT")
            ?? Path.Combine(AppContext.BaseDirectory, "login-smoke.json");
        output = Path.GetFullPath(output);
        string loginImage = Path.ChangeExtension(output, ".login.png");
        string registerImage = Path.ChangeExtension(output, ".register.png");
        var report = new JsonObject
        {
            ["ok"] = false, ["framework"] = ".NET 9 WPF", ["api"] = address,
            ["loginImage"] = loginImage, ["registerImage"] = registerImage
        };
        LoginWindow? guestWindow = null;
        LoginWindow? registrationWindow = null;
        try
        {
            AssertEntrySmoke(Uri.TryCreate(address, UriKind.Absolute, out var endpoint) && endpoint.IsLoopback, "登录验收只允许本机 API。");
            Directory.CreateDirectory(Path.GetDirectoryName(output)!);
            guestWindow = new LoginWindow(address);
            await DriveEntrySmoke(guestWindow, async window =>
            {
                await window.Dispatcher.InvokeAsync(() => window.UpdateLayout(), DispatcherPriority.ContextIdle);
                CaptureEntrySmoke(window, loginImage);
                window.GuestButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                AssertEntrySmoke(window.entered && window.closed && window.Client != null,
                    "访客按钮未完成登录窗口的客户端交接。");
                AssertEntrySmoke(window.Client!.Token == null && window.Account == null,
                    "访客入口不应携带账号或访问令牌。");
            });
            report["guestEntry"] = true;

            // A successful registration after the mismatch check also proves that the
            // first click did not accidentally create this same account on the server.
            string username = "smoke_entry_" + DateTime.UtcNow.ToString("yyyyMMddHHmmss") + "_" + Guid.NewGuid().ToString("N")[..6];
            string password = "EntrySmoke!" + Guid.NewGuid().ToString("N");
            const string displayName = "登录界面功能测试";
            registrationWindow = new LoginWindow(address);
            await DriveEntrySmoke(registrationWindow, async window =>
            {
                window.AuthTabs.SelectedIndex = 1;
                await window.Dispatcher.InvokeAsync(() => window.UpdateLayout(), DispatcherPriority.ContextIdle);
                window.RegisterUsername.Text = username;
                window.RegisterDisplayName.Text = displayName;
                window.RegisterPassword.Password = password;
                window.RegisterConfirmation.Password = password + "-different";
                window.RegisterButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));

                // RegisterClicked returns synchronously before Run() for mismatches.
                // Check before yielding to any HTTP continuation on the dispatcher.
                AssertEntrySmoke(!window.busy && window.pendingClient == null && window.Client == null,
                    "确认密码不匹配时不应创建 HTTP 客户端或进入请求阶段。");
                AssertEntrySmoke(window.MessagePanel.Visibility == Visibility.Visible &&
                    window.MessageText.Text.Contains("两次输入的密码不一致", StringComparison.Ordinal),
                    "确认密码不匹配时未显示本地校验提示。");
                report["passwordMismatchRejectedLocally"] = true;

                window.RegisterConfirmation.Password = password;
                window.MessagePanel.Visibility = Visibility.Collapsed;
                window.UpdateLayout();
                CaptureEntrySmoke(window, registerImage);
                window.RegisterButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                await WaitEntrySmoke(() => !window.busy, "注册请求未在预期时间内完成。");
                AssertEntrySmoke(!window.closed && window.AuthTabs.SelectedIndex == 0 &&
                    window.MessageText.Text.Contains("注册成功", StringComparison.Ordinal),
                    "真实注册失败：" + window.MessageText.Text);
                AssertEntrySmoke(window.RegisterPassword.Password.Length == 0 &&
                    window.RegisterConfirmation.Password.Length == 0,
                    "注册成功后仍保留注册密码。");
                AssertEntrySmoke(window.LoginUsername.Text == username,
                    "注册成功后未将新用户名填入登录页。");
                report["registration"] = true;

                window.LoginPassword.Password = password;
                window.LoginButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
                await WaitEntrySmoke(() => !window.busy, "登录请求未在预期时间内完成。");
                AssertEntrySmoke(window.entered && window.closed && window.Client?.Token is { Length: > 0 } &&
                    window.Account != null, "新注册账号登录失败：" + window.MessageText.Text);
                AssertEntrySmoke(window.LoginPassword.Password.Length == 0,
                    "登录成功后仍保留登录密码。");
            });

            var profile = await registrationWindow.Client!.Get("api/auth/me");
            AssertEntrySmoke(profile.Text("username") == username && profile.Text("displayName") == displayName,
                "认证后的 /api/auth/me 未返回刚注册并持久化的账号。");
            AssertEntrySmoke(profile.Text("role") == "USER",
                "新注册账号不应直接获得科研或管理员权限。");
            AssertEntrySmoke(profile.Text("id") == registrationWindow.Account!.Text("id"),
                "登录返回的账号与服务端当前会话不一致。");
            report["authenticatedProfile"] = true;
            report["registeredUsername"] = username;
            report["registeredUserId"] = profile.Text("id");
            report["registeredRole"] = profile.Text("role");
            report["ok"] = true;
        }
        catch (Exception error)
        {
            report["error"] = error.ToString();
        }
        finally
        {
            if (registrationWindow?.Client?.Token != null)
            {
                try { await registrationWindow.Client.Post("api/auth/logout", new { }); }
                catch (Exception error) { report["ok"] = false; report["logoutError"] = error.Message; }
                finally { registrationWindow.Client.Token = null; }
            }
            guestWindow?.Client?.Dispose();
            registrationWindow?.Client?.Dispose();
            report["finishedAt"] = DateTimeOffset.UtcNow.ToString("O");
            Directory.CreateDirectory(Path.GetDirectoryName(output)!);
            await File.WriteAllTextAsync(output, report.ToJsonString(new System.Text.Json.JsonSerializerOptions { WriteIndented = true }));
        }
    }

    private static async Task DriveEntrySmoke(LoginWindow window, Func<LoginWindow, Task> scenario)
    {
        var completion = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        _ = window.Dispatcher.BeginInvoke(new Action(async () =>
        {
            try
            {
                await scenario(window);
                completion.TrySetResult();
            }
            catch (Exception error)
            {
                completion.TrySetException(error);
            }
            finally
            {
                if (!window.closed) window.Close();
            }
        }), DispatcherPriority.ContextIdle);
        // Complete() sets DialogResult; exercise the real modal path.
        window.ShowDialog();
        await completion.Task;
    }

    private static async Task WaitEntrySmoke(Func<bool> completed, string failure)
    {
        var deadline = DateTime.UtcNow.AddSeconds(25);
        while (!completed())
        {
            if (DateTime.UtcNow >= deadline) throw new TimeoutException(failure);
            // Only waits for local UI state; this loop sends no API requests.
            await Task.Delay(25);
        }
    }

    private static void AssertEntrySmoke(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    private static void CaptureEntrySmoke(LoginWindow window, string path)
    {
        window.UpdateLayout();
        // Capture the complete scrollable form, including registration's submit button
        // on a 200%-DPI display or a short restored window.
        var content = window.Content is ScrollViewer scroll && scroll.Content is FrameworkElement form
            ? form : (FrameworkElement)window.Content;
        content.UpdateLayout();
        int width = Math.Max(1, (int)Math.Ceiling(content.ActualWidth));
        int height = Math.Max(1, (int)Math.Ceiling(content.ActualHeight));
        var bitmap = new RenderTargetBitmap(width, height, 96, 96, PixelFormats.Pbgra32);
        var canvas = new DrawingVisual();
        using (var drawing = canvas.RenderOpen())
        {
            drawing.DrawRectangle(Brushes.White, null, new Rect(0, 0, width, height));
            drawing.DrawRectangle(new VisualBrush(content) { Stretch = Stretch.Fill }, null, new Rect(0, 0, width, height));
        }
        bitmap.Render(canvas);
        var encoder = new PngBitmapEncoder();
        encoder.Frames.Add(BitmapFrame.Create(bitmap));
        using var stream = File.Create(path);
        encoder.Save(stream);
    }
}
