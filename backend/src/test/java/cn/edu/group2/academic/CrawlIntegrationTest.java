package cn.edu.group2.academic;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import tools.jackson.databind.ObjectMapper;

@SpringBootTest(properties={
    "spring.datasource.url=${TEST_DB_URL:jdbc:h2:mem:crawltasks;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DEFAULT_NULL_ORDERING=HIGH;NON_KEYWORDS=YEAR;DB_CLOSE_DELAY=-1}",
    "spring.datasource.username=${TEST_DB_USER:sa}","spring.datasource.password=${TEST_DB_PASSWORD:}",
    "app.demo=true","app.demo-count=64","management.server.port=0","app.crawl.worker-enabled=false"})
class CrawlIntegrationTest {
    @Autowired Db db;@Autowired CrawlStore store;@Autowired CrawlRunner runner;@Autowired CrossrefClient crossref;
    @Autowired ObjectMapper json;
    @MockitoBean CrossrefTransport transport;
    AuthService.Actor admin;
    HttpServer server;
    final Queue<Reply> replies=new ConcurrentLinkedQueue<>();
    final List<String> requests=new CopyOnWriteArrayList<>();
    final List<Map<String,List<String>>> requestHeaders=new CopyOnWriteArrayList<>();
    record Reply(int status,String type,String body,Map<String,String> headers) {}
    @BeforeEach void setup() throws Exception {
        // An isolated test database only. A few sequential fixture pages exercise correctness, never load.
        db.update("DELETE FROM crawl_page");db.update("DELETE FROM crawl_task_log");db.update("DELETE FROM crawl_checkpoint");db.update("DELETE FROM crawl_task");db.update("DELETE FROM crawl_http_cache");
        db.update("UPDATE crawl_source SET enabled=TRUE,config_version=0,min_interval_ms=1,next_request_at=0,lease_token=NULL,lease_until=NULL,schedule_enabled=FALSE,schedule_user_id=NULL");
        var user=db.one("SELECT * FROM app_user WHERE username='admin'");admin=new AuthService.Actor(user.get("id").toString(),"admin","Admin","ADMIN");
        replies.clear();requests.clear();requestHeaders.clear();reset(transport);
        server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
        server.createContext("/",exchange->{
            Reply reply;
            if(exchange.getRequestURI().getPath().equals("/robots.txt")) reply=new Reply(200,"text/plain","User-agent: *\nAllow: /\n",Map.of());
            else {
                requests.add(exchange.getRequestURI().toString());requestHeaders.add(new LinkedHashMap<>(exchange.getRequestHeaders()));
                reply=replies.poll();if(reply==null) reply=new Reply(500,"application/json","{}",Map.of());
            }
            exchange.getResponseHeaders().set("Content-Type",reply.type());
            reply.headers().forEach((name,value)->exchange.getResponseHeaders().set(name,value));
            byte[] body=reply.body().getBytes(StandardCharsets.UTF_8);
            if(reply.status()==304) exchange.sendResponseHeaders(304,-1);
            else {exchange.sendResponseHeaders(reply.status(),body.length);exchange.getResponseBody().write(body);}
            exchange.close();
        });server.start();
        HttpClient client=HttpClient.newHttpClient();
        when(transport.get(any(URI.class),anyMap())).thenAnswer(invocation->{
            URI registered=invocation.getArgument(0);assertEquals("api.crossref.org",registered.getHost());
            var local=URI.create("http://127.0.0.1:"+server.getAddress().getPort()+registered.getRawPath()+(registered.getRawQuery()==null?"":"?"+registered.getRawQuery()));
            var builder=HttpRequest.newBuilder(local).GET();Map<String,String> headers=invocation.getArgument(1);headers.forEach(builder::header);
            var response=client.send(builder.build(),HttpResponse.BodyHandlers.ofString());
            return new CrossrefTransport.Response(response.statusCode(),response.headers().map(),response.body());
        });
    }
    @AfterEach void cleanup() {if(server!=null) server.stop(0);}
    @SuppressWarnings("unchecked") Map<String,Object> task(String mode,int pageSize,int maxPages,int maxRecords) {
        return (Map<String,Object>)store.create(new CrawlStore.Create("crossref","0098-5589","","","2025-01-01","2025-01-02",pageSize,maxPages,null,mode,maxRecords,null,null),admin);
    }
    @SuppressWarnings("unchecked") Map<String,Object> start(Map<String,Object> task) {
        return (Map<String,Object>)store.action(task.get("id").toString(),new CrawlStore.Action(((Number)task.get("version")).intValue(),"START"),admin);
    }
    Map<String,Object> state(Map<String,Object> task) {return store.detail(task.get("id").toString());}
    void runPage() {db.update("UPDATE crawl_source SET next_request_at=0");assertTrue(runner.executeOne());}
    String doi() {return "10.5555/crawl-"+Db.id();}
    Map<String,Object> item(String doi,String title) {
        return new LinkedHashMap<>(Map.of("DOI",doi,"type","journal-article","title",List.of(title),"container-title",List.of("Fixture Journal"),
            "published-print",Map.of("date-parts",List.of(List.of(2020))),"indexed",Map.of("date-time","2025-01-01T00:00:00Z"),
            "author",List.of(Map.of("given","Test","family","Author")),"is-referenced-by-count",3));
    }
    void page(List<Map<String,Object>> items,String cursor,long total) {
        replies.add(new Reply(200,"application/json",json.writeValueAsString(Map.of("status","ok","message-type","work-list",
            "message",Map.of("items",items,"next-cursor",cursor,"total-results",total))),Map.of()));
    }
    @Test void boundedBudgetCompletesWithoutAdvancingWatermarkAndKeepsRawMetadata() {
        var task=start(task("BOUNDED",2,5,2));String first=doi(),second=doi();
        page(List.of(item(first,"Real fixture one"),item(second,"Real fixture two")),"next-one",5);runPage();
        var result=state(task);assertEquals("SUCCESS",result.get("state"));assertEquals("LIMIT_REACHED",result.get("completionReason"));
        assertEquals(2,((Number)result.get("received")).intValue());assertEquals(2,((Number)result.get("inserted")).intValue());
        assertEquals(0,db.count("SELECT COUNT(*) FROM crawl_checkpoint"));
        assertEquals(1,db.count("SELECT COUNT(*) FROM crawl_page WHERE task_id=?",task.get("id")));
        assertTrue(db.one("SELECT raw_json FROM crawl_page WHERE task_id=?",task.get("id")).get("rawJson").toString().contains(first));
        assertEquals(0,db.count("SELECT COUNT(*) FROM work_field f JOIN work w ON w.id=f.work_id WHERE w.doi=?",first));
        assertTrue(URLDecoder.decode(requests.getFirst(),StandardCharsets.UTF_8).contains("from-index-date:2025-01-01,until-index-date:2025-01-02,issn:0098-5589"));
    }
    @Test void incrementalCursorCommitsEachPageAndAdvancesWatermarkOnlyAfterExhaustion() {
        var task=start(task("INCREMENTAL",1,4,4));page(List.of(item(doi(),"Cursor first")),"cursor/+==",1);runPage();
        assertEquals("PENDING",state(task).get("state"));assertEquals(0,db.count("SELECT COUNT(*) FROM crawl_checkpoint"));
        page(List.of(item(doi(),"Cursor second")),"cursor/+==",2);runPage();
        assertEquals("PENDING",state(task).get("state"));assertEquals(0,db.count("SELECT COUNT(*) FROM crawl_checkpoint"));
        page(List.of(),"cursor/+==",2);runPage();
        var result=state(task);assertEquals("SUCCESS",result.get("state"));assertEquals("SOURCE_EXHAUSTED",result.get("completionReason"));
        assertEquals(3,((Number)result.get("committedPages")).intValue());
        assertEquals("2025-01-02",db.one("SELECT successful_until FROM crawl_checkpoint").get("successfulUntil"));
        assertTrue(URLDecoder.decode(requests.get(1),StandardCharsets.UTF_8).contains("cursor=cursor/+=="));
    }
    @Test void incrementalRecordLimitPreservesPartialPagesWithoutClaimingCompleteWindow() {
        var task=start(task("INCREMENTAL",20,3,1));page(List.of(item(doi(),"Budget fixture")),"more",10);runPage();
        var result=state(task);assertEquals("FAILED",result.get("state"));assertEquals("LIMIT_REACHED",result.get("errorCode"));
        assertEquals(1,((Number)result.get("received")).intValue());assertEquals(0,db.count("SELECT COUNT(*) FROM crawl_checkpoint"));
        assertTrue(requests.getFirst().contains("rows=1"));
    }
    @Test void pageBudgetAlsoStopsBoundedModeButDoesNotAdvanceCheckpoint() {
        var task=start(task("BOUNDED",1,1,5));page(List.of(item(doi(),"Page budget")),"more",5);runPage();
        assertEquals("SUCCESS",state(task).get("state"));assertEquals("LIMIT_REACHED",state(task).get("completionReason"));
        assertEquals(0,db.count("SELECT COUNT(*) FROM crawl_checkpoint"));
    }
    @Test void rateLimitHonorsRetryAfterAndResumesSameWindow() {
        var task=start(task("INCREMENTAL",2,3,6));replies.add(new Reply(429,"application/json","{}",Map.of("Retry-After","120")));
        long before=Db.now();runPage();var result=state(task);
        assertEquals("RETRYING",result.get("state"));assertTrue(((Number)result.get("nextRunAt")).longValue()>=before+120_000);
        assertFalse(runner.executeOne());assertEquals(0,db.count("SELECT COUNT(*) FROM crawl_page"));
        db.update("UPDATE crawl_task SET next_run_at=0 WHERE id=?",task.get("id"));page(List.of(),"",0);runPage();
        assertEquals("SUCCESS",state(task).get("state"));assertEquals(1,((Number)state(task).get("retryCount")).intValue());
    }
    @Test void htmlAndOversizedItemCountAreFailuresNotEmptySuccess() {
        var task=start(task("INCREMENTAL",1,2,2));replies.add(new Reply(200,"text/html","<html>Login required</html>",Map.of()));runPage();
        assertEquals("FAILED",state(task).get("state"));assertEquals("NON_JSON",state(task).get("errorCode"));
        var next=start(task("BOUNDED",1,2,1));page(List.of(item(doi(),"One"),item(doi(),"Two")),"next",2);runPage();
        assertEquals("FAILED",state(next).get("state"));assertEquals("INVALID_RESPONSE",state(next).get("errorCode"));
        assertEquals(0,db.count("SELECT COUNT(*) FROM crawl_page"));assertEquals(0,db.count("SELECT COUNT(*) FROM crawl_checkpoint"));
    }
    @Test void stopRequestedDuringRequestPreventsPublicationAtCommitBoundary() {
        var task=start(task("INCREMENTAL",2,3,6));var lease=store.claimNext();assertNotNull(lease);
        String doi=doi();page(List.of(item(doi,"Stop fixture")),"",1);var response=crossref.fetch(lease);
        var current=state(task);store.action(lease.id(),new CrawlStore.Action(((Number)current.get("version")).intValue(),"STOP"),admin);
        assertEquals("RUNNING",state(task).get("state"));assertFalse(store.commit(lease,response));
        assertEquals("STOPPED",state(task).get("state"));assertEquals(0,db.count("SELECT COUNT(*) FROM work WHERE doi=?",doi));
        assertEquals(0,db.count("SELECT COUNT(*) FROM crawl_page"));assertEquals(0,db.count("SELECT COUNT(*) FROM crawl_checkpoint"));
    }
    @Test void expiredAttemptCannotPublishAfterNewAttemptAcquiresLease() {
        var task=start(task("INCREMENTAL",2,3,6));var old=store.claimNext();assertNotNull(old);
        String doi=doi();page(List.of(item(doi,"Fence fixture")),"",1);var response=crossref.fetch(old);
        db.update("UPDATE crawl_task SET lease_until=0 WHERE id=?",old.id());db.update("UPDATE crawl_source SET lease_until=0,next_request_at=0");
        assertNull(store.claimNext());assertEquals("RETRYING",state(task).get("state"));
        db.update("UPDATE crawl_task SET next_run_at=0 WHERE id=?",old.id());var fresh=store.claimNext();assertNotNull(fresh);
        assertTrue(fresh.attempt()>old.attempt());assertFalse(store.commit(old,response));
        assertEquals(0,db.count("SELECT COUNT(*) FROM work WHERE doi=?",doi));assertTrue(store.commit(fresh,response));
        assertEquals("SUCCESS",state(task).get("state"));assertEquals(1,db.count("SELECT COUNT(*) FROM work WHERE doi=?",doi));
    }
    @Test void twoWorkersCannotOwnTheSameSourceConcurrently() throws Exception {
        start(task("BOUNDED",1,1,1));var barrier=new CyclicBarrier(2);
        try(var pool=Executors.newVirtualThreadPerTaskExecutor()) {
            var first=pool.submit(()->{barrier.await();return store.claimNext();});
            var second=pool.submit(()->{barrier.await();return store.claimNext();});
            assertEquals(1,(first.get(10,TimeUnit.SECONDS)==null?0:1)+(second.get(10,TimeUnit.SECONDS)==null?0:1));
        }
    }
    @SuppressWarnings("unchecked")
    @Test void doiConditionalCacheUses304AndCleansMarkupWithoutInventingFields() {
        String doi=doi();var raw=item(doi,"<jats:i>Testing &amp; verification</jats:i>");
        raw.put("abstract","<p>Useful &amp; bounded.</p><script>bad()</script><style>.hidden{}</style>");
        raw.put("published-online",Map.of("date-parts",List.of(List.of(2019,3,4))));
        raw.put("author",List.of(Map.of("name","Research Team","ORCID","bad-orcid","affiliation",List.of(Map.of("name","Raw University")))));
        String body=json.writeValueAsString(Map.of("status","ok","message-type","work","message",raw));
        var create=new CrawlStore.Create("crossref","","",doi,null,null,1,1,null,"BOUNDED",1,null,null);
        var first=start((Map<String,Object>)store.create(create,admin));replies.add(new Reply(200,"application/json",body,Map.of("ETag","fixture-v1")));runPage();
        assertEquals("SUCCESS",state(first).get("state"));var work=db.one("SELECT * FROM work WHERE doi=?",doi);
        assertEquals("Testing & verification",work.get("title"));assertEquals("2020",work.get("dateValue"));
        assertEquals("Useful & bounded.",work.get("abstractText"));assertTrue(work.get("detailsJson").toString().contains("published-print"));
        assertTrue(work.get("detailsJson").toString().contains("invalidOrcidCount"));
        long revision=db.count("SELECT revision FROM catalog_release");
        var second=start((Map<String,Object>)store.create(create,admin));replies.add(new Reply(304,"application/json","",Map.of()));runPage();
        assertEquals("SUCCESS",state(second).get("state"));assertEquals(revision,db.count("SELECT revision FROM catalog_release"));
        assertTrue(requestHeaders.get(1).entrySet().stream().anyMatch(e->e.getKey().equalsIgnoreCase("If-None-Match")&&e.getValue().contains("fixture-v1")));
        assertEquals(0,db.count("SELECT COUNT(*) FROM crawl_checkpoint"));
    }
    @SuppressWarnings("unchecked")
    @Test void noStoreResponseIsNotReusedForConditionalFetch() {
        String doi=doi();String body=json.writeValueAsString(Map.of("status","ok","message-type","work","message",item(doi,"No-store fixture")));
        var create=new CrawlStore.Create("crossref","","",doi,null,null,1,1,null,"BOUNDED",1,null,null);
        var first=start((Map<String,Object>)store.create(create,admin));
        replies.add(new Reply(200,"application/json",body,Map.of("ETag","private-cache","Cache-Control","no-store")));runPage();
        assertEquals("SUCCESS",state(first).get("state"));assertEquals(0,db.count("SELECT COUNT(*) FROM crawl_http_cache WHERE request_url LIKE '%/works/%'"));
        var second=start((Map<String,Object>)store.create(create,admin));replies.add(new Reply(200,"application/json",body,Map.of()));runPage();
        assertEquals("SUCCESS",state(second).get("state"));
        assertTrue(requestHeaders.get(1).keySet().stream().noneMatch(name->name.equalsIgnoreCase("If-None-Match")));
    }
    @Test void overlongDoiIsQuarantinedWithoutDiscardingOtherPageItems() {
        var task=start(task("BOUNDED",3,1,3));
        page(List.of(item("10.5555/"+"x".repeat(200),"Long identifier"),item(doi(),"Usable item")),"",2);runPage();
        var result=state(task);assertEquals("SUCCESS",result.get("state"));
        assertEquals(1,((Number)result.get("excluded")).intValue());assertEquals(1,((Number)result.get("inserted")).intValue());
    }
    @Test void excludedFrontMatterHasRawPageAndExplicitReason() {
        var task=start(task("INCREMENTAL",2,2,4));page(List.of(item(doi(),"Editorial Board")),"",1);runPage();
        var result=state(task);assertEquals("SUCCESS",result.get("state"));assertEquals(1,((Number)result.get("excluded")).intValue());
        assertEquals(0,((Number)result.get("inserted")).intValue());
        assertTrue(db.one("SELECT exclusions_json FROM crawl_page WHERE task_id=?",task.get("id")).get("exclusionsJson").toString().contains("NON_RESEARCH_FRONT_MATTER"));
    }
    @Test void robotsRulesRespectSpecificAgentAndLongestMatchingAllow() {
        assertFalse(CrossrefClient.robotsAllows("User-agent: *\nDisallow: /works\n","/works"));
        assertTrue(CrossrefClient.robotsAllows("User-agent: *\nDisallow: /works\nAllow: /works/10.1\n","/works/10.123/example"));
        assertTrue(CrossrefClient.robotsAllows("User-agent: *\nDisallow: /\nUser-agent: AcademicPlatform\nDisallow:\n","/works"));
    }
}
