package cn.edu.group2.academic;

import java.io.ByteArrayOutputStream;
import java.net.URI;
import java.net.http.*;
import java.nio.ByteBuffer;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
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
    public Response get(URI uri,Map<String,String> headers) {
        if(!CrawlSourceCatalog.allows(uri)) throw new CrawlFailure("UNREGISTERED_ENDPOINT","地址不在登记的公告及 robots 路径内",false);
        var builder=HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(20)).GET();headers.forEach(builder::header);
        var pending=client.sendAsync(builder.build(),info->new LimitedBody());
        try {var response=pending.get(25,TimeUnit.SECONDS);return new Response(response.statusCode(),response.headers().map(),response.body());}
        catch(InterruptedException e) {pending.cancel(true);Thread.currentThread().interrupt();throw new CrawlFailure("INTERRUPTED","来源请求已中断",true);}
        catch(TimeoutException e) {pending.cancel(true);throw new CrawlFailure("NETWORK_ERROR","来源响应整体超过 25 秒",true);}
        catch(ExecutionException e) {
            Throwable cause=e.getCause();while(cause.getCause()!=null&&!(cause instanceof CrawlFailure)) cause=cause.getCause();
            if(cause instanceof CrawlFailure failure) throw failure;
            throw new CrawlFailure("NETWORK_ERROR","公告来源网络请求失败",true);
        }
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
