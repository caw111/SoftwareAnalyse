package cn.edu.group2.academic;

import static org.junit.jupiter.api.Assertions.*;
import java.net.*;
import java.security.cert.*;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ExecutionException;
import javax.net.ssl.*;
import org.junit.jupiter.api.Test;

class RegisteredSourceTransportTest {
    @Test void packagedRootMatchesIndependentlyAuditedFingerprintAndValidity() throws Exception {
        var root=NsfcTls.rootCertificate();
        assertEquals("5CC3D78E4E1D5E45547A04E6873E64F90CF9536D1CCC2EF800F355C4C5FD70FD",NsfcTls.fingerprint(root));
        assertEquals("184accd6",root.getSerialNumber().toString(16));assertTrue(root.getBasicConstraints()>=0);
        assertEquals(root.getSubjectX500Principal(),root.getIssuerX500Principal());root.verify(root.getPublicKey());
        assertEquals(Instant.parse("2029-12-31T03:07:01Z"),root.getNotAfter().toInstant());
        root.checkValidity(Date.from(Instant.parse("2026-11-17T00:00:00Z")));
        assertThrows(CertificateExpiredException.class,()->root.checkValidity(Date.from(Instant.parse("2030-01-01T00:00:00Z"))));
    }
    @Test void extraAnchorIsConfinedToRegisteredNsfcRequestsAndHostnameValidationRemainsEnabled() throws Exception {
        SSLContext originalDefault=SSLContext.getDefault();var transport=new RegisteredSourceHttpTransport();
        var standard=transport.clientFor(URI.create(CrawlSourceCatalog.source("most-awards").batches().getFirst().url()));
        var nsfc=transport.clientFor(URI.create(CrawlSourceCatalog.source("nsfc-projects").batches().getFirst().url()));
        try {
            assertNotSame(standard,nsfc);assertNotSame(standard.sslContext(),nsfc.sslContext());assertSame(originalDefault,SSLContext.getDefault());
            assertEquals("HTTPS",nsfc.sslParameters().getEndpointIdentificationAlgorithm());
            assertEquals(java.net.http.HttpClient.Redirect.NEVER,nsfc.followRedirects());
            assertSame(nsfc,transport.clientFor(URI.create("https://www.nsfc.gov.cn/robots.txt")));
            for(String url:List.of("https://www.nsfc.gov.cn.evil.example/robots.txt","https://other.nsfc.gov.cn/robots.txt",
                "http://www.nsfc.gov.cn/robots.txt","https://www.nsfc.gov.cn:444/robots.txt","https://www.nsfc.gov.cn/private",
                "https://attacker@www.nsfc.gov.cn/robots.txt")) {
                URI uri=URI.create(url);assertSame(standard,transport.clientFor(uri));
                assertEquals("UNREGISTERED_ENDPOINT",assertThrows(CrawlFailure.class,()->transport.get(uri,Map.of())).code);
            }
        } finally {standard.close();nsfc.close();}
    }
    @Test void handshakeAndCertificatePathErrorsArePermanentWhileNetworkErrorsRemainRetryable() {
        for(Exception cause:List.of(new SSLHandshakeException("handshake"),new SSLPeerUnverifiedException("hostname"),
            new CertPathValidatorException("expired intermediate"),new CertPathBuilderException("missing anchor"),new CertificateExpiredException("expired"))) {
            var result=RegisteredSourceHttpTransport.requestFailure(new ExecutionException(new RuntimeException(cause)));
            assertEquals("TLS_VALIDATION_FAILED",result.code);assertFalse(result.retryable);
        }
        var timeout=RegisteredSourceHttpTransport.requestFailure(new ExecutionException(new SocketTimeoutException("read")));
        assertEquals("NETWORK_ERROR",timeout.code);assertTrue(timeout.retryable);
        var bounded=new CrawlFailure("RESPONSE_TOO_LARGE","bounded",false);
        assertSame(bounded,RegisteredSourceHttpTransport.requestFailure(new ExecutionException(bounded)));
    }
}
