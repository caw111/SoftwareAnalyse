using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace AcademicDesktop;

/// <summary>Owns an anonymous client until a successful login or explicit guest entry transfers it.</summary>
public partial class LoginWindow : Window
{
    private bool busy;
    private bool closed;
    private bool entered;
    private ApiClient? pendingClient;
    public ApiClient? Client { get; private set; }
    public JsonNode? Account { get; private set; }
    public string ServerUrl => ServerAddress.Text.Trim();

    public LoginWindow(string? address = null)
    {
        InitializeComponent();
        ServerAddress.Text = !string.IsNullOrWhiteSpace(address) ? address
            : Environment.GetEnvironmentVariable("ACADEMIC_API_URL") ?? "http://127.0.0.1:8080";
    }

    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        WindowPlacement.StartMaximized(this);
    }

    private void WindowLoaded(object sender, RoutedEventArgs e) => LoginUsername.Focus();

    private void AuthTabChanged(object sender, SelectionChangedEventArgs e)
    {
        if (LoginButton == null || RegisterButton == null || MessagePanel == null || e.Source != AuthTabs) return;
        LoginButton.IsDefault = AuthTabs.SelectedIndex == 0;
        RegisterButton.IsDefault = AuthTabs.SelectedIndex == 1;
        MessagePanel.Visibility = Visibility.Collapsed;
    }

    private void ShowMessage(string message, bool error = false)
    {
        MessageText.Text = message;
        MessageText.Foreground = new SolidColorBrush(error ? Color.FromRgb(160, 58, 58) : Color.FromRgb(54, 83, 93));
        MessagePanel.Background = new SolidColorBrush(error ? Color.FromRgb(255, 242, 240) : Color.FromRgb(240, 246, 245));
        MessagePanel.Visibility = Visibility.Visible;
        _ = Dispatcher.BeginInvoke(new Action(() => { if (!closed) MessagePanel.BringIntoView(); }));
    }

    private async Task Run(Func<ApiClient, Task> action)
    {
        if (busy) return;
        busy = true;
        FormPanel.IsEnabled = false;
        ShowMessage("正在连接，请稍候…");
        ApiClient? candidate = null;
        try
        {
            candidate = new ApiClient(ServerUrl);
            pendingClient = candidate;
            await action(candidate);
        }
        catch (Exception error)
        {
            if (!closed) ShowMessage(error.Message, true);
        }
        finally
        {
            if (!ReferenceEquals(Client, candidate)) candidate?.Dispose();
            pendingClient = null;
            busy = false;
            if (!closed) FormPanel.IsEnabled = true;
        }
    }

    private async void LoginClicked(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(LoginUsername.Text) || LoginPassword.Password.Length == 0)
        {
            ShowMessage("请输入用户名和密码。", true);
            return;
        }
        await Run(async client =>
        {
            var result = await client.Post("api/auth/login", new { username = LoginUsername.Text.Trim(), password = LoginPassword.Password });
            if (closed) return;
            string token = result.Text("token");
            var profile = result["user"];
            if (string.IsNullOrWhiteSpace(token) || profile == null) throw new InvalidOperationException("登录响应不完整，请稍后重试。");
            client.Token = token;
            LoginPassword.Clear();
            Complete(client, profile);
        });
    }

    private async void RegisterClicked(object sender, RoutedEventArgs e)
    {
        string username = RegisterUsername.Text.Trim();
        string displayName = RegisterDisplayName.Text.Trim();
        string password = RegisterPassword.Password;
        if (!Regex.IsMatch(username, @"\A[a-zA-Z0-9_.-]{3,40}\z"))
        {
            ShowMessage("用户名需为 3–40 位字母或数字，也可包含 _ . -。", true);
            return;
        }
        if (displayName.Length == 0)
        {
            ShowMessage("请填写姓名。", true);
            return;
        }
        if (password.Length < 12 || password.Length > 128)
        {
            ShowMessage("密码需为 12–128 位字符。", true);
            return;
        }
        if (password != RegisterConfirmation.Password)
        {
            ShowMessage("两次输入的密码不一致。", true);
            return;
        }
        await Run(async client =>
        {
            await client.Post("api/auth/register", new { username, password, displayName });
            if (closed) return;
            RegisterPassword.Clear();
            RegisterConfirmation.Clear();
            LoginUsername.Text = username;
            AuthTabs.SelectedIndex = 0;
            ShowMessage("注册成功。请登录后提交门户认证申请，审核通过后可申领成果。");
            // Focus after Run restores enabled controls.
            _ = Dispatcher.BeginInvoke(new Action(() => { if (!closed) LoginPassword.Focus(); }));
        });
    }

    private void GuestClicked(object sender, RoutedEventArgs e)
    {
        if (busy) return;
        try { Complete(new ApiClient(ServerUrl), null); }
        catch (Exception error) { ShowMessage(error.Message, true); }
    }

    private void Complete(ApiClient client, JsonNode? profile)
    {
        if (closed) { client.Dispose(); return; }
        Client = client;
        Account = profile;
        entered = true;
        DialogResult = true;
    }

    protected override void OnClosed(EventArgs e)
    {
        closed = true;
        if (!entered)
        {
            pendingClient?.Dispose();
            Client?.Dispose();
            Client = null;
        }
        LoginPassword.Clear();
        RegisterPassword.Clear();
        RegisterConfirmation.Clear();
        base.OnClosed(e);
    }
}
