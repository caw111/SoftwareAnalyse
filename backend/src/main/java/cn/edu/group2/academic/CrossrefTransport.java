package cn.edu.group2.academic;

import java.io.*;
import java.net.*;
import java.net.http.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.nio.ByteBuffer;
import org.springframework.stereotype.Component;

interface CrossrefTransport {
    record Response(int status,Map<String,List<String>> headers,String body) {
        String header(String name) {return headers.entrySet().stream().filter(e->e.getKey().equalsIgnoreCase(name)).findFirst().map(e->e.getValue().getFirst()).orElse("");}
    }
    Response get(URI uri,Map<String,String> headers);
}
@Component
class CrossrefHttpTransport implements CrossrefTransport {
    private final HttpClient client=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(8))
        .followRedirects(HttpClient.Redirect.NEVER).build();
    public Response get(URI uri,Map<String,String> headers) {
        // This is a fixed API adapter, never an arbitrary-URL fetch proxy.
        if(!"https".equals(uri.getScheme())||!"api.crossref.org".equals(uri.getHost())||uri.getPort()!=-1
            ||uri.getUserInfo()!=null||!(uri.getPath().equals("/robots.txt")||uri.getPath().equals("/works")||uri.getPath().startsWith("/works/")))
            throw new CrawlFailure("UNREGISTERED_ENDPOINT","来源地址未登记",false);
        var request=HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(20)).GET();
        headers.forEach(request::header);
        var pending=client.sendAsync(request.build(),info->new LimitedBody());
        try {
            var response=pending.get(25,TimeUnit.SECONDS);
            return new Response(response.statusCode(),response.headers().map(),new String(response.body(),java.nio.charset.StandardCharsets.UTF_8));
        } catch(InterruptedException e) {
            pending.cancel(true);Thread.currentThread().interrupt();throw new CrawlFailure("INTERRUPTED","采集请求被中断",true);
        } catch(TimeoutException e) {pending.cancel(true);throw new CrawlFailure("NETWORK_ERROR","来源响应整体超过 25 秒",true);}
        catch(ExecutionException e) {
            if(e.getCause() instanceof CrawlFailure failure) throw failure;
            throw new CrawlFailure("NETWORK_ERROR","来源网络请求失败或超时",true);
        }
    }
    private static final class LimitedBody implements HttpResponse.BodySubscriber<byte[]> {
        private final ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        private final CompletableFuture<byte[]> result=new CompletableFuture<>();
        private Flow.Subscription subscription;
        public CompletionStage<byte[]> getBody() {return result;}
        public void onSubscribe(Flow.Subscription value) {subscription=value;value.request(1);}
        public void onNext(List<ByteBuffer> buffers) {
            for(var buffer:buffers) {
                if((long)bytes.size()+buffer.remaining()>2*1024*1024) {
                    subscription.cancel();result.completeExceptionally(new CrawlFailure("RESPONSE_TOO_LARGE","来源响应超过 2 MiB，请缩小每页数量",false));return;
                }
                byte[] part=new byte[buffer.remaining()];buffer.get(part);bytes.writeBytes(part);
            }
            subscription.request(1);
        }
        public void onError(Throwable error) {result.completeExceptionally(error);}
        public void onComplete() {result.complete(bytes.toByteArray());}
    }
}
