using System.IO;
using System.Net.Http;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;

namespace AcademicDesktop;

internal static class ServerCertificateTrust
{
    private static readonly Lazy<X509Certificate2> Root = new(LoadBundledRoot);

    internal static bool AppliesTo(Uri uri) => uri.Scheme == Uri.UriSchemeHttps &&
        uri.Host == "49.233.93.248" && uri.Port == 8080;

    internal static void Configure(SocketsHttpHandler handler, Uri uri)
    {
        if (!AppliesTo(uri)) return; // Manually selected other HTTPS services retain the OS trust policy.
        var policy = new X509ChainPolicy
        {
            TrustMode = X509ChainTrustMode.CustomRootTrust,
            VerificationFlags = X509VerificationFlags.NoFlag,
            DisableCertificateDownloads = true,
            // This dedicated private CA has no revocation endpoint. Name, signature, EKU and dates remain checked.
            RevocationMode = X509RevocationMode.NoCheck
        };
        policy.CustomTrustStore.Add(Root.Value);
        policy.ApplicationPolicy.Add(new Oid("1.3.6.1.5.5.7.3.1")); // TLS server authentication.
        handler.SslOptions.CertificateChainPolicy = policy;
        // No validation callback: SslStream still rejects SAN/hostname mismatches and invalid chains.
    }

    internal static string RootSha256 => Root.Value.GetCertHashString(HashAlgorithmName.SHA256);

    private static X509Certificate2 LoadBundledRoot()
    {
        using var stream = typeof(ServerCertificateTrust).Assembly.GetManifestResourceStream("AcademicDesktop.ServerCa.pem")
            ?? throw new InvalidOperationException("客户端缺少服务器 CA 证书，请使用完整发布包。");
        using var reader = new StreamReader(stream);
        var root = X509Certificate2.CreateFromPem(reader.ReadToEnd());
        if (root.HasPrivateKey || !root.Extensions.OfType<X509BasicConstraintsExtension>().Any(extension => extension.CertificateAuthority))
        {
            root.Dispose();
            throw new InvalidOperationException("客户端内置的服务器 CA 证书无效。");
        }
        return root;
    }
}
