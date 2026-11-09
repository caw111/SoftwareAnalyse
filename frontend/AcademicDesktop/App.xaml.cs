using System.Windows;
namespace AcademicDesktop;
public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        Dispatcher.BeginInvoke(async () =>
        {
            string address = Environment.GetEnvironmentVariable("ACADEMIC_API_URL") ?? "http://127.0.0.1:8080";
            if (e.Args.Contains("--login-smoke")) { await LoginWindow.RunLoginSmoke(address); Shutdown(); return; }
            if (e.Args.Contains("--smoke") || e.Args.Contains("--workspace-smoke"))
            {
                var workspace = new MainWindow(new ApiClient(address), null, address);
                MainWindow = workspace; workspace.Show();
            }
            else OpenEntry(address);
        });
    }
    public void OpenEntry(string? address = null)
    {
        var login = new LoginWindow(address);
        MainWindow = login;
        if (login.ShowDialog() != true || login.Client == null) { Shutdown(); return; }
        var workspace = new MainWindow(login.Client, login.Account, login.ServerUrl);
        MainWindow = workspace; workspace.Show();
    }
}
