package cn.edu.group2.academic;

import java.io.*;
import java.security.*;
import java.security.cert.*;
import java.util.*;
import javax.net.ssl.*;

/** One reviewed trust anchor, confined to the registered NSFC HTTP client. */
final class NsfcTls {
    static final String ROOT_SHA256="5CC3D78E4E1D5E45547A04E6873E64F90CF9536D1CCC2EF800F355C4C5FD70FD";
    private static final X509Certificate ROOT=loadRoot();
    static X509Certificate rootCertificate() {return ROOT;}
    static void checkRootValidity() {
        try {ROOT.checkValidity();}
        catch(CertificateException expired) {throw new CrawlFailure("TLS_VALIDATION_FAILED","NSFC 专用信任根已失效，需人工核验证书并更新应用",false);}
    }
    static SSLContext context() {
        try {
            // Keep the platform's default anchors and standard PKIX checks, without altering global state.
            TrustManagerFactory defaults=TrustManagerFactory.getInstance("PKIX");defaults.init((KeyStore)null);
            KeyStore roots=KeyStore.getInstance(KeyStore.getDefaultType());roots.load(null,null);
            for(TrustManager manager:defaults.getTrustManagers()) if(manager instanceof X509TrustManager trusted) {
                for(X509Certificate certificate:trusted.getAcceptedIssuers()) roots.setCertificateEntry(fingerprint(certificate),certificate);
            }
            roots.setCertificateEntry(ROOT_SHA256,ROOT);
            TrustManagerFactory scoped=TrustManagerFactory.getInstance("PKIX");scoped.init(roots);
            SSLContext context=SSLContext.getInstance("TLS");context.init(null,scoped.getTrustManagers(),null);return context;
        } catch(GeneralSecurityException | IOException failure) {throw new IllegalStateException("Cannot initialize reviewed NSFC PKIX trust configuration",failure);}
    }
    static String fingerprint(X509Certificate certificate) throws GeneralSecurityException {
        return HexFormat.of().withUpperCase().formatHex(MessageDigest.getInstance("SHA-256").digest(certificate.getEncoded()));
    }
    private static X509Certificate loadRoot() {
        try(InputStream input=NsfcTls.class.getResourceAsStream("/tls/cfca-ev-root.pem")) {
            if(input==null) throw new IOException("Missing audited root resource");
            X509Certificate certificate=(X509Certificate)CertificateFactory.getInstance("X.509").generateCertificate(input);
            if(!ROOT_SHA256.equals(fingerprint(certificate))||certificate.getBasicConstraints()<0||!certificate.getSubjectX500Principal().equals(certificate.getIssuerX500Principal())) throw new CertificateException("Audited root fingerprint or CA constraints changed");
            certificate.verify(certificate.getPublicKey());return certificate;
        } catch(GeneralSecurityException | IOException failure) {throw new IllegalStateException("Cannot load audited NSFC trust anchor",failure);}
    }
    private NsfcTls() {}
}
