using System.IO;
using System.Text.Json.Nodes;
using System.Windows;
namespace AcademicDesktop;
public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        Dispatcher.BeginInvoke(async () =>
        {
            if (e.Args.Contains("--connection-check")) { Shutdown(await RunConnectionCheck()); return; }
            bool smoke = e.Args.Any(argument => argument is "--login-smoke" or "--smoke" or "--workspace-smoke" or "--crawl-smoke");
            string address;
            try { address = smoke ? ServerEndpoint.ResolveSmoke() : ServerEndpoint.Resolve(); }
            catch (InvalidOperationException error)
            {
                string? output = Environment.GetEnvironmentVariable("ACADEMIC_SMOKE_OUTPUT");
                if (!string.IsNullOrWhiteSpace(output))
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
                    await File.WriteAllTextAsync(output, new JsonObject { ["ok"] = false, ["error"] = error.Message, ["requestsSent"] = 0 }.ToJsonString());
                }
                Shutdown(1); return;
            }
            if (e.Args.Contains("--login-smoke")) { await LoginWindow.RunLoginSmoke(address); Shutdown(); return; }
            if (smoke)
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

    // Explicit read-only connectivity probe through the exact packaged ApiClient and embedded CA.
    private static async Task<int> RunConnectionCheck()
    {
        string address = ServerEndpoint.Resolve();
        string output = Environment.GetEnvironmentVariable("ACADEMIC_CONNECTION_OUTPUT")
            ?? Path.Combine(AppContext.BaseDirectory, "connection-check.json");
        var report = new JsonObject { ["ok"] = false, ["api"] = address, ["method"] = "GET", ["path"] = "api/reference", ["authenticated"] = false };
        try
        {
            using var client = new ApiClient(address);
            var reference = await client.Get("api/reference");
            report["ok"] = true; report["milliseconds"] = client.LastMilliseconds;
            report["institutionCount"] = reference["institutions"] is JsonArray institutions ? institutions.Count : 0;
            report["fieldCount"] = reference["fields"] is JsonArray fields ? fields.Count : 0;
            report["trust"] = ServerCertificateTrust.AppliesTo(new Uri(address)) ? "application-private-ca" : "system-default";
            if (ServerCertificateTrust.AppliesTo(new Uri(address))) report["rootSha256"] = ServerCertificateTrust.RootSha256;
        }
        catch (Exception error) { report["error"] = error.Message; }
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
        await File.WriteAllTextAsync(output, report.ToJsonString(new System.Text.Json.JsonSerializerOptions { WriteIndented = true }));
        return report["ok"]!.GetValue<bool>() ? 0 : 1;
    }
}
