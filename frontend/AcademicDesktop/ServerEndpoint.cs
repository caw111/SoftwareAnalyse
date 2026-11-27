namespace AcademicDesktop;

internal static class ServerEndpoint
{
    internal const string PublicApiUrl = "https://49.233.93.248:8080";
    internal const string LocalDemoUrl = "http://127.0.0.1:8080";

    internal static string Resolve(string? address = null)
    {
        if (!string.IsNullOrWhiteSpace(address)) return address.Trim();
        string? configured = Environment.GetEnvironmentVariable("ACADEMIC_API_URL");
        return string.IsNullOrWhiteSpace(configured) ? LocalDemoUrl : configured.Trim();
    }

    internal static bool IsLocalDemo(string address) => Uri.TryCreate(address, UriKind.Absolute, out var uri) &&
        uri.Scheme == Uri.UriSchemeHttp && uri.IsLoopback && uri.Port == 8080 && uri.AbsolutePath == "/" &&
        string.IsNullOrEmpty(uri.UserInfo) && string.IsNullOrEmpty(uri.Query) && string.IsNullOrEmpty(uri.Fragment);

    internal static string ResolveSmoke()
    {
        string? configured = Environment.GetEnvironmentVariable("ACADEMIC_API_URL");
        string address = string.IsNullOrWhiteSpace(configured) ? LocalDemoUrl : configured.Trim();
        if (!IsLocalDemo(address)) throw new InvalidOperationException("功能验收仅允许 http://127.0.0.1:8080 本机演示 API；不得连接公网服务或 18080 SSH 隧道。");
        return address;
    }
}
