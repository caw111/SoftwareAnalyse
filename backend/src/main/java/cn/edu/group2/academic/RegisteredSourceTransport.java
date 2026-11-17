package cn.edu.group2.academic;

import java.io.ByteArrayOutputStream;
import java.net.URI;
import java.net.http.*;
import java.nio.ByteBuffer;
import java.security.cert.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import javax.net.ssl.*;
import org.springframework.stereotype.Component;

interface RegisteredSourceTransport {
    int MAX_BYTES=8*1024*1024;
    record Response(int status,Map<String,List<String>> headers,byte[] body) {
        String header(String key) {return headers.entrySet().stream().filter(e->e.getKey().equalsIgnoreCase(key)).findFirst().map(e->e.getValue().getFirst()).orElse("");}
    }
    Response get(URI uri,Map<String,String> headers);
}

@Component
class RegisteredSourceHttpTransport implements RegisteredSourceTransport {
    private final HttpClient client=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(8)).followRedirects(HttpClient.Redirect.NEVER).build();
    private final HttpClient nsfcClient;
    RegisteredSourceHttpTransport() {
        var parameters=new SSLParameters();parameters.setEndpointIdentificationAlgorithm("HTTPS");
        nsfcClient=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(8)).followRedirects(HttpClient.Redirect.NEVER)
            .sslContext(NsfcTls.context()).sslParameters(parameters).build();
    }
    HttpClient clientFor(URI uri) {
        if(CrawlSourceCatalog.allows(uri)&&"www.nsfc.gov.cn".equals(uri.getHost())) {NsfcTls.checkRootValidity();return nsfcClient;}
        return client;
    }
    public Response get(URI uri,Map<String,String> headers) {
        if(!CrawlSourceCatalog.allows(uri)) throw new CrawlFailure("UNREGISTERED_ENDPOINT","地址不在登记的公告及 robots 路径内",false);
        var builder=HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(20)).GET();headers.forEach(builder::header);
        var pending=clientFor(uri).sendAsync(builder.build(),info->new LimitedBody());
        try {var response=pending.get(25,TimeUnit.SECONDS);return new Response(response.statusCode(),response.headers().map(),response.body());}
        catch(InterruptedException e) {pending.cancel(true);Thread.currentThread().interrupt();throw new CrawlFailure("INTERRUPTED","来源请求已中断",true);}
        catch(TimeoutException e) {pending.cancel(true);throw new CrawlFailure("NETWORK_ERROR","来源响应整体超过 25 秒",true);}
        catch(ExecutionException e) {throw requestFailure(e);}
    }
    static CrawlFailure requestFailure(Throwable error) {
        Set<Throwable> seen=Collections.newSetFromMap(new IdentityHashMap<>());
        for(Throwable cause=error;cause!=null&&seen.add(cause);cause=cause.getCause()) {
            if(cause instanceof CrawlFailure failure) return failure;
            if(cause instanceof SSLHandshakeException||cause instanceof SSLPeerUnverifiedException||cause instanceof CertificateException
                ||cause instanceof CertPathValidatorException||cause instanceof CertPathBuilderException) {
                return new CrawlFailure("TLS_VALIDATION_FAILED","公告来源 TLS 证书校验失败，需人工核验证书链、有效期及主机名",false);
            }
        }
        return new CrawlFailure("NETWORK_ERROR","公告来源网络请求失败",true);
    }
    private static final class LimitedBody implements HttpResponse.BodySubscriber<byte[]> {
        final ByteArrayOutputStream bytes=new ByteArrayOutputStream();final CompletableFuture<byte[]> result=new CompletableFuture<>();Flow.Subscription subscription;
        public CompletionStage<byte[]> getBody() {return result;}
        public void onSubscribe(Flow.Subscription value) {subscription=value;value.request(1);}
        public void onNext(List<ByteBuffer> buffers) {
            for(var buffer:buffers) {
                if((long)bytes.size()+buffer.remaining()>MAX_BYTES) {subscription.cancel();result.completeExceptionally(new CrawlFailure("RESPONSE_TOO_LARGE","登记公告超过 8 MiB 上限，需复核来源",false));return;}
                byte[] part=new byte[buffer.remaining()];buffer.get(part);bytes.writeBytes(part);
            }
            subscription.request(1);
        }
        public void onComplete() {result.complete(bytes.toByteArray());}
        public void onError(Throwable e) {result.completeExceptionally(e);}
    }
}
