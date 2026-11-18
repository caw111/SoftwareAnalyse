package cn.edu.group2.academic;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

@SpringBootTest(properties={
 "spring.datasource.url=${TEST_DB_URL:jdbc:h2:mem:registered;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DEFAULT_NULL_ORDERING=HIGH;NON_KEYWORDS=YEAR;DB_CLOSE_DELAY=-1}",
 "spring.datasource.username=${TEST_DB_USER:sa}","spring.datasource.password=${TEST_DB_PASSWORD:}",
 "app.demo=true","app.demo-count=64","app.crawl.worker-enabled=false","management.server.port=0"})
class RegisteredSourceIntegrationTest {
    @Autowired CrawlStore store;@Autowired CrawlRunner runner;@Autowired RegisteredSourceClient client;@Autowired Db db;
    @Autowired ImportService imports;
    @MockitoBean RegisteredSourceTransport transport;
    AuthService.Actor admin;final Map<String,RegisteredSourceTransport.Response> replies=new HashMap<>();
    final AtomicInteger businessRequests=new AtomicInteger();String robots="User-agent: *\nAllow: /";
    @BeforeEach void setup() throws Exception {
        db.update("DELETE FROM crawl_document");db.update("DELETE FROM crawl_page");db.update("DELETE FROM crawl_task_log");db.update("DELETE FROM crawl_checkpoint");db.update("DELETE FROM crawl_task");db.update("DELETE FROM crawl_http_cache");
        db.update("UPDATE crawl_source SET enabled=CASE WHEN id='lynu-patents' THEN FALSE ELSE TRUE END,config_version=0,min_interval_ms=1,next_request_at=0,lease_token=NULL,lease_until=NULL,schedule_enabled=FALSE,schedule_user_id=NULL");
        var user=db.one("SELECT * FROM app_user WHERE username='admin'");admin=new AuthService.Actor(user.get("id").toString(),"admin","Admin","ADMIN");
        reset(transport);replies.clear();businessRequests.set(0);robots="User-agent: *\nAllow: /";
        for(var pair:Map.of("nsfc-projects","nsfc-2019.html","most-awards","most-2023.html","cnipa-patents","cnipa-25-gold.pdf").entrySet()) {
            var batch=CrawlSourceCatalog.source(pair.getKey()).batches().getFirst();
            replies.put(batch.url(),new RegisteredSourceTransport.Response(200,Map.of("Content-Type",List.of(batch.contentType())),fixture(pair.getValue())));
        }
        when(transport.get(any(URI.class),anyMap())).thenAnswer(call->{
            URI uri=call.getArgument(0);assertTrue(CrawlSourceCatalog.allows(uri));
            if(uri.getPath().equals("/robots.txt")) return response(200,"text/plain",robots);
            businessRequests.incrementAndGet();return replies.get(uri.toString());
        });
    }
    static byte[] fixture(String name) throws Exception {try(var input=RegisteredSourceIntegrationTest.class.getResourceAsStream("/crawl/"+name)) {return Objects.requireNonNull(input).readAllBytes();}}
    static RegisteredSourceTransport.Response response(int status,String type,String body) {return new RegisteredSourceTransport.Response(status,Map.of("Content-Type",List.of(type)),body.getBytes(StandardCharsets.UTF_8));}
    CrawlStore.Create input(String source,int records,int pageSize,int pages) {return new CrawlStore.Create(source,"","","",null,null,pageSize,pages,null,"BOUNDED",records,null,null,CrawlSourceCatalog.source(source).batches().getFirst().id());}
    @SuppressWarnings("unchecked") Map<String,Object> start(String source,int records,int pageSize,int pages) {
        var task=(Map<String,Object>)store.create(input(source,records,pageSize,pages),admin);
        return (Map<String,Object>)store.action(task.get("id").toString(),new CrawlStore.Action(((Number)task.get("version")).intValue(),"START"),admin);
    }
    void run() {db.update("UPDATE crawl_source SET next_request_at=0");assertTrue(runner.executeOne());}
    Map<String,Object> state(Map<String,Object> task) {return store.detail(task.get("id").toString());}

    @Test void sourcesExposeDistinctCapabilitiesAndRegisteredScopesCannotBeForged() {
        assertEquals(5,store.sources().size());
        for(var source:store.sources()) assertEquals(source.get("id").equals("crossref"),source.get("supportsIncremental"));
        assertThrows(ApiException.class,()->store.create(new CrawlStore.Create("nsfc-projects","","","",null,null,1,1,null,"BOUNDED",1,null,null,"http://127.0.0.1/private"),admin));
        assertThrows(ApiException.class,()->store.create(new CrawlStore.Create("nsfc-projects","","","",null,null,1,1,null,"BOUNDED",1,null,null,"lynu-grants-2025"),admin));
        assertThrows(ApiException.class,()->store.create(new CrawlStore.Create("most-awards","","","",null,null,1,1,null,"INCREMENTAL",1,null,null,"most-natural-science-2023"),admin));
        assertThrows(ApiException.class,()->store.create(new CrawlStore.Create("nsfc-projects","","quantum","",null,null,1,1,null,"BOUNDED",1,null,null,"nsfc-life-key-2019"),admin));
        assertThrows(ApiException.class,()->store.settings("nsfc-projects",new CrawlStore.Settings(0,true,2000,true,1440,"1234-5678",20,5,1),admin));
        assertEquals(0,businessRequests.get());
        assertFalse(CrawlSourceCatalog.allows(URI.create("https://www.nsfc.gov.cn/private")));
        assertFalse(CrawlSourceCatalog.allows(URI.create("http://www.nsfc.gov.cn/p1/2853/3102/72645.html")));
    }
    @Test void taskFreezesOneDocumentAndResumesSlicesWithoutAnotherNetworkRequest() {
        var task=start("nsfc-projects",2,1,3);run();var first=state(task);
        assertEquals("PENDING",first.get("state"));assertEquals(1L,CrawlStore.num(first,"received"));
        String id=task.get("id").toString();assertEquals(115L,CrawlStore.num(store.document(id),"recordCount"));
        // A different upstream edition must not alter the second slice of the existing task.
        replies.put(CrawlSourceCatalog.source("nsfc-projects").batches().getFirst().url(),response(200,"text/html","<html>Changed upstream</html>"));
        run();var finalState=state(task);
        assertEquals("SUCCESS",finalState.get("state"));assertEquals("LIMIT_REACHED",finalState.get("completionReason"));
        assertEquals(2L,CrawlStore.num(finalState,"received"));assertEquals(1,businessRequests.get());
        assertEquals(1L,db.count("SELECT COUNT(*) FROM crawl_document WHERE task_id=?",id));assertEquals(0L,db.count("SELECT COUNT(*) FROM crawl_checkpoint"));
        @SuppressWarnings("unchecked") var raw=(Map<String,Object>)store.rawPage(id,2);
        assertTrue(raw.get("rawJson").toString().contains("科学部编号"));assertTrue(raw.get("sliceMetadata").toString().contains("\"offset\":1"));
        assertEquals("text/html",raw.get("contentType"));
    }
    @Test void pdfBytesAndUnknownGrantDateSurvivePublicationAndReplayIsIdempotent() throws Exception {
        var first=start("cnipa-patents",1,1,1);run();assertEquals("SUCCESS",state(first).get("state"));
        var snapshot=store.document(first.get("id").toString());
        assertEquals("base64",snapshot.get("bodyEncoding"));assertArrayEquals(fixture("cnipa-25-gold.pdf"),Base64.getDecoder().decode(snapshot.get("rawBody").toString()));
        String key=new CnipaPatentParser().parse(fixture("cnipa-25-gold.pdf")).rows().getFirst().work().sourceKey();
        var work=db.one("SELECT w.* FROM work w JOIN source_head h ON h.work_id=w.id WHERE h.source_name=? AND h.source_key=?",CrawlSourceCatalog.source("cnipa-patents").sourceName(),key);
        assertNull(work.get("year"));assertEquals("grant_date",work.get("dateKind"));assertEquals(false,work.get("simulated"));
        long revision=db.count("SELECT revision FROM catalog_release WHERE id=1");
        var again=start("cnipa-patents",1,1,1);run();var replay=state(again);
        assertEquals(1L,CrawlStore.num(replay,"unchanged"));assertEquals(0L,CrawlStore.num(replay,"inserted"));assertEquals(revision,db.count("SELECT revision FROM catalog_release WHERE id=1"));
    }
    @Test void eachHtmlAdapterPublishesItsOwnOutcomeTypeAndDeclaredTimeMeaning() {
        for(var source:List.of("nsfc-projects","most-awards")) {
            var task=start(source,1,1,1);run();assertEquals("SUCCESS",state(task).get("state"));assertEquals(0L,CrawlStore.num(state(task),"excluded"));
            var work=db.one("SELECT w.* FROM work w JOIN source_head h ON h.work_id=w.id WHERE h.source_name=? ORDER BY h.last_seen_at DESC LIMIT 1",CrawlSourceCatalog.source(source).sourceName());
            assertEquals(CrawlSourceCatalog.source(source).outcomeType(),work.get("type"));
            assertEquals(source.equals("nsfc-projects")?2019:2023,((Number)work.get("year")).intValue());
            if(source.equals("nsfc-projects")) assertEquals("department_number",work.get("identifierType"));
        }
    }
    @Test void stopAtCommitBoundaryPublishesNeitherDocumentNorRows() {
        var task=start("nsfc-projects",1,1,1);var lease=store.claimNext();var page=client.fetch(lease);
        var current=state(task);store.action(lease.id(),new CrawlStore.Action(((Number)current.get("version")).intValue(),"STOP"),admin);
        assertFalse(store.commit(lease,page));assertEquals("STOPPED",state(task).get("state"));assertNull(store.document(lease.id()));
        assertEquals(0L,db.count("SELECT COUNT(*) FROM crawl_page WHERE task_id=?",lease.id()));
    }
    @Test void responseShellAndMissingDocumentFailWithoutPublishingAnEmptySuccess() {
        String url=CrawlSourceCatalog.source("most-awards").batches().getFirst().url();
        replies.put(url,response(200,"text/html","<html><body>JavaScript application</body></html>"));
        var task=start("most-awards",1,1,1);run();assertEquals("FAILED",state(task).get("state"));assertEquals("INVALID_RESPONSE",state(task).get("errorCode"));
        replies.put(url,response(404,"text/html","missing"));task=start("most-awards",1,1,1);run();assertEquals("SOURCE_NOT_FOUND",state(task).get("errorCode"));
        assertEquals(0L,db.count("SELECT COUNT(*) FROM crawl_document"));
    }
    @Test void robotsBlocksBeforeBusinessRequestAndRateLimitPreservesRetryAfter() {
        robots="User-agent: *\nDisallow: /";var task=start("most-awards",1,1,1);run();
        assertEquals("ROBOTS_DENIED",state(task).get("errorCode"));assertEquals(0,businessRequests.get());
        robots="User-agent: *\nAllow: /";db.update("DELETE FROM crawl_http_cache");
        String url=CrawlSourceCatalog.source("nsfc-projects").batches().getFirst().url();
        replies.put(url,new RegisteredSourceTransport.Response(429,Map.of("Content-Type",List.of("text/plain"),"Retry-After",List.of("120")),new byte[0]));
        long before=Db.now();task=start("nsfc-projects",1,1,1);run();var state=state(task);
        assertEquals("RETRYING",state.get("state"));assertTrue(CrawlStore.num(state,"nextRunAt")>=before+120_000);assertNull(store.document(task.get("id").toString()));
    }
    @Test void parserVersionChangeDuringResumeCannotMixEditions() {
        var task=start("nsfc-projects",2,1,3);run();String id=task.get("id").toString();
        db.update("UPDATE crawl_document SET parser_version='older-parser' WHERE task_id=?",id);run();
        assertEquals("FAILED",state(task).get("state"));assertEquals("DOCUMENT_CHANGED",state(task).get("errorCode"));assertEquals(1L,CrawlStore.num(state(task),"received"));
    }
    @Test void tlsValidationFailureStopsTheTaskAndRejectsManualRetryWithoutPublishing() {
        var failure=RegisteredSourceHttpTransport.requestFailure(new javax.net.ssl.SSLHandshakeException("untrusted source chain"));
        doThrow(failure).when(transport).get(any(URI.class),anyMap());
        var task=start("nsfc-projects",1,1,1);run();var result=state(task);
        assertEquals("FAILED",result.get("state"));assertEquals("TLS_VALIDATION_FAILED",result.get("errorCode"));
        assertEquals(0L,CrawlStore.num(result,"retryCount"));assertNull(store.document(task.get("id").toString()));
        assertEquals(0L,db.count("SELECT COUNT(*) FROM crawl_page WHERE task_id=?",task.get("id")));
        var retry=assertThrows(ApiException.class,()->store.action(task.get("id").toString(),new CrawlStore.Action(((Number)result.get("version")).intValue(),"RETRY"),admin));
        assertEquals(409,retry.status);
    }
    @Test void retiredSourceRemainsDescribedButCannotCreateReenableStartRetryOrReachItsHost() {
        var source=store.sources().stream().filter(s->s.get("id").equals("lynu-patents")).findFirst().orElseThrow();
        assertEquals(false,source.get("available"));assertEquals(true,source.get("deprecated"));assertFalse(source.get("deprecationReason").toString().isBlank());
        assertEquals(4,store.sources().stream().filter(s->Boolean.TRUE.equals(s.get("available"))).count());
        assertFalse(CrawlSourceCatalog.allows(URI.create(CrawlSourceCatalog.source("lynu-patents").batches().getFirst().url())));
        assertFalse(CrawlSourceCatalog.allows(URI.create("https://sites.lynu.edu.cn/robots.txt")));
        // Even a stale pre-cutover database flag cannot restore a retired source's capability.
        db.update("UPDATE crawl_source SET enabled=TRUE WHERE id='lynu-patents'");
        assertEquals(409,assertThrows(ApiException.class,()->store.create(input("lynu-patents",1,1,1),admin)).status);
        assertEquals(409,assertThrows(ApiException.class,()->store.settings("lynu-patents",new CrawlStore.Settings(0,true,2000,false,1440,"",1,1,1),admin)).status);
        var pending=legacyTask("PENDING");var failed=legacyTask("FAILED");
        assertEquals(409,assertThrows(ApiException.class,()->store.action(pending,new CrawlStore.Action(0,"START"),admin)).status);
        assertEquals(409,assertThrows(ApiException.class,()->store.action(failed,new CrawlStore.Action(0,"RETRY"),admin)).status);
        assertEquals("PENDING",store.detail(pending).get("state"));assertEquals("FAILED",store.detail(failed).get("state"));
        assertEquals(0,businessRequests.get());
    }
    @Test void retiredSourceRejectsOldValidLeaseBeforeFetchAndCommitAndWorkerCancelsPendingTask() {
        String running=legacyTask("RUNNING"),token=Db.id();long until=Db.now()+180_000;
        db.update("UPDATE crawl_source SET enabled=TRUE,lease_token=?,lease_until=? WHERE id='lynu-patents'",token,until);
        db.update("UPDATE crawl_task SET lease_token=?,lease_until=?,attempt=1 WHERE id=?",token,until,running);
        var lease=new CrawlStore.Lease(running,"lynu-patents",token,1,store.detail(running));
        assertEquals("SOURCE_DEPRECATED",assertThrows(CrawlFailure.class,()->client.fetch(lease)).code);
        assertEquals("SOURCE_DEPRECATED",assertThrows(CrawlFailure.class,()->store.reserveRequest(lease)).code);
        assertEquals("SOURCE_DEPRECATED",assertThrows(CrawlFailure.class,()->store.assertActive(lease)).code);
        var page=new CrawlPage("https://sites.lynu.edu.cn/kycx/info/1221/5141.htm","historical",200,"","",0,List.of(),List.of(),"0",true,null);
        assertFalse(store.commit(lease,page));assertEquals("STOPPED",store.detail(running).get("state"));
        assertEquals("SOURCE_DEPRECATED",store.detail(running).get("errorCode"));assertEquals(0L,db.count("SELECT COUNT(*) FROM crawl_page WHERE task_id=?",running));
        String pending=legacyTask("PENDING");assertNull(store.claimNext());assertEquals("STOPPED",store.detail(pending).get("state"));
        assertEquals(0,businessRequests.get());
    }
    @Test void retirementMigrationCancelsActiveAttemptsAndPreservesPublishedWorksAndEvidence() throws Exception {
        var ids=new LinkedHashMap<String,String>();
        for(String state:List.of("PENDING","RUNNING","RETRYING","SUCCESS","FAILED","STOPPED")) ids.put(state,legacyTask(state));
        String token=Db.id();long until=Db.now()+180_000;
        db.update("UPDATE crawl_source SET enabled=TRUE,schedule_enabled=TRUE,lease_token=?,lease_until=? WHERE id='lynu-patents'",token,until);
        db.update("UPDATE crawl_task SET lease_token=?,lease_until=?,attempt=1 WHERE id=?",token,until,ids.get("RUNNING"));
        var oldLease=new CrawlStore.Lease(ids.get("RUNNING"),"lynu-patents",token,1,store.detail(ids.get("RUNNING")));
        String original=new String(fixture("lynu-2025.html"),StandardCharsets.UTF_8),hash=AuthService.hash(original);
        String url=CrawlSourceCatalog.source("lynu-patents").batches().getFirst().url();
        db.update("INSERT INTO crawl_document VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",ids.get("SUCCESS"),url,original,"text/html","utf-8",hash,hash,200,null,null,28,RegisteredHtmlParser.VERSION,Db.now());
        db.update("""
            INSERT INTO crawl_page(task_id,page_no,attempt,request_url,raw_json,response_checksum,http_status,exclusions_json,received,accepted,excluded,created_at)
            VALUES(?,1,1,?,?,?,200,'[]',1,1,0,?)
            """,ids.get("SUCCESS"),url,"{\"offset\":0}",hash,Db.now());
        db.update("UPDATE crawl_task SET received=1,committed_pages=1 WHERE id=?",ids.get("SUCCESS"));
        // Offline import represents an existing pre-retirement result, never a new network fetch.
        var historical=new RegisteredHtmlParser().parse("lynu-patents",original).rows().getFirst().work();
        imports.ingest(new ImportService.Batch("historical-lynu-"+Db.id(),"LYNU Patent Grants",List.of(historical)),admin);
        var recordsBefore=db.rows("SELECT * FROM source_record WHERE source_name='LYNU Patent Grants' ORDER BY id");
        var worksBefore=db.rows("SELECT w.* FROM work w WHERE EXISTS(SELECT 1 FROM source_record s WHERE s.work_id=w.id AND s.source_name='LYNU Patent Grants') ORDER BY w.id");
        new ResourceDatabasePopulator(new ClassPathResource("db/migration/V7__retire_lynu_source.sql")).execute(Objects.requireNonNull(db.jdbc.getDataSource()));
        var source=db.one("SELECT * FROM crawl_source WHERE id='lynu-patents'");
        assertEquals(false,source.get("enabled"));assertEquals(false,source.get("scheduleEnabled"));assertEquals(1L,CrawlStore.num(source,"configVersion"));assertNull(source.get("leaseToken"));
        for(String state:List.of("PENDING","RUNNING","RETRYING")) {
            var task=store.detail(ids.get(state));assertEquals("STOPPED",task.get("state"));assertEquals("SOURCE_DEPRECATED",task.get("errorCode"));
            assertEquals(false,task.get("runnable"));assertEquals(true,task.get("stopRequested"));assertNull(task.get("leaseToken"));assertNotNull(task.get("completedAt"));
            assertEquals(1L,db.count("SELECT COUNT(*) FROM crawl_task_log WHERE task_id=? AND action='SOURCE_DEPRECATED'",ids.get(state)));
        }
        for(String state:List.of("SUCCESS","FAILED","STOPPED")) {assertEquals(state,store.detail(ids.get(state)).get("state"));assertEquals(0L,CrawlStore.num(store.detail(ids.get(state)),"version"));}
        assertFalse(store.commit(oldLease,null)); // Fencing rejects before examining a late worker's payload.
        assertEquals(recordsBefore,db.rows("SELECT * FROM source_record WHERE source_name='LYNU Patent Grants' ORDER BY id"));
        assertEquals(worksBefore,db.rows("SELECT w.* FROM work w WHERE EXISTS(SELECT 1 FROM source_record s WHERE s.work_id=w.id AND s.source_name='LYNU Patent Grants') ORDER BY w.id"));
        @SuppressWarnings("unchecked") var raw=(Map<String,Object>)store.rawPage(ids.get("SUCCESS"),1);
        assertEquals(original,raw.get("rawJson"));assertEquals(1L,CrawlStore.num(store.detail(ids.get("SUCCESS")),"committedPages"));
    }
    @SuppressWarnings("unchecked")
    private String legacyTask(String state) {
        var task=(Map<String,Object>)store.create(input("nsfc-projects",2,1,2),admin);String id=task.get("id").toString();
        // Model a V6 row without bypassing the production API's new source prohibition.
        db.update("UPDATE crawl_task SET source_id='lynu-patents',batch_id='lynu-grants-2025',state=?,runnable=TRUE WHERE id=?",state,id);return id;
    }
}
