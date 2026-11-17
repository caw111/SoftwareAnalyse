# NSFC scoped trust anchor

`cfca-ev-root.pem` is a **public CA certificate**, not a private key or server certificate. It was exported on 2026-11-17 from the development machine's Windows `LocalMachine\Root` certificate store, then matched byte-for-byte by DER SHA-256 against the CFCA EV ROOT entry in Mozilla's official [CCADB included CA certificate report](https://ccadb.my.salesforce-sites.com/mozilla/includedcacertificatereport). CFCA also documents this hierarchy in its [official certificate deployment manual](https://www.cfca.com.cn/upload/20160316.pdf).

- Subject/issuer: `CN=CFCA EV ROOT, O=China Financial Certification Authority, C=CN`
- Serial: `184ACCD6`
- DER SHA-256: `5CC3D78E4E1D5E45547A04E6873E64F90CF9536D1CCC2EF800F355C4C5FD70FD`
- Validity: `2012-08-08T03:07:01Z` through `2029-12-31T03:07:01Z`
- Observed NSFC chain: `*.nsfc.gov.cn` → `CFCA OV OCA` → `CFCA EV ROOT`.

The tested Java 21 installation did not contain this root. `NsfcTls` verifies the bundled fingerprint, self-signature and CA constraints before constructing an **in-memory, client-local PKIX** trust configuration containing the JDK's default trust anchors plus this root. Only the exact, registered HTTPS `www.nsfc.gov.cn` batch and robots URLs use that HTTP client. Other sources keep the default client. Hostname verification (`HTTPS`), standard certificate path/algorithm/expiry checks and redirect rejection remain enabled. The supplemental root's own validity is checked before each NSFC request.

There is no trust-all verifier, automatic AIA download, global SSLContext replacement, or modification of Windows/JDK trust stores. TLS validation errors are terminal `TLS_VALIDATION_FAILED` failures and are not eligible for automatic or manual task retry; an administrator must fix/review the trust configuration and create a new task.

Maintenance: review the official CCADB trust status on runtime upgrades and before **2029-10-01**, or immediately on a publisher chain change or TLS failure. Do not replace the file merely to make a failing handshake pass. A replacement requires an independently checked official fingerprint/CA status, updated code pin and tests, and a reviewed release. After `2029-12-31T03:07:01Z` the current supplemental configuration fails closed for NSFC until it is reviewed. Source publication fields must never be used as TLS trust evidence.
