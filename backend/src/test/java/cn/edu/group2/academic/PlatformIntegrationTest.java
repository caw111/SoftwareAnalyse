package cn.edu.group2.academic;

import static org.junit.jupiter.api.Assertions.*;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataIntegrityViolationException;

@SpringBootTest(properties={
    "spring.datasource.url=${TEST_DB_URL:jdbc:h2:mem:tests;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DEFAULT_NULL_ORDERING=HIGH;NON_KEYWORDS=YEAR;DB_CLOSE_DELAY=-1}",
    "spring.datasource.username=${TEST_DB_USER:sa}","spring.datasource.password=${TEST_DB_PASSWORD:}",
    "app.demo=true","app.demo-count=64","management.server.port=0"})
class PlatformIntegrationTest {
    @Autowired Db db;@Autowired AuthService auth;@Autowired ClaimService claims;
    @Autowired ImportService imports;@Autowired CatalogService catalog;@Autowired GraphService graph;
    AuthService.Actor admin;
    @BeforeEach void setup() {
        var u=db.one("SELECT * FROM app_user WHERE username='admin'");
        admin=new AuthService.Actor(u.get("id").toString(),"admin","Admin","ADMIN");
    }
    AuthService.Actor user(String role) {
        String username="test-"+Db.id().substring(0,12);
        String id=auth.createUser(username,"TestPassword2026!",username,role);
        return new AuthService.Actor(id,username,username,role);
    }
    String scholar() {
        String id="S-"+Db.id();db.update("INSERT INTO scholar VALUES(?,?,'I1','Test',TRUE)",id,"同名测试");return id;
    }
    Map<String,Object> action(Map<String,Object> c,String action,AuthService.Actor actor) {
        return claims.action(c.get("id").toString(),new ClaimService.Action(((Number)c.get("version")).intValue(),action,"测试审核依据",action.equals("SUBMIT")&&c.get("state").equals("NEED_MORE_INFO")?"补充证据":null),actor);
    }
    Map<String,Object> pending(AuthService.Actor u,String kind,String target,String role) {
        return action(claims.create(new ClaimService.Create(kind,target,"人工测试证明",role),u),"SUBMIT",u);
    }
    void portal(AuthService.Actor u,String target) {action(action(pending(u,"PORTAL",target,""),"TAKE",admin),"APPROVE",admin);}
    CatalogService.Query query(String q,Long version) {return catalog.query(q,"","","","",null,null,"demo","year",0,20,version);}
    ImportService.WorkInput sample(int id) {return Bootstrap.sample(id,new String[]{"林知远","林知远","陈思宁","周予安","李文澜","王清和","赵亦舟","刘星遥","孙嘉禾","吴明川","郑时雨","许予墨"});}

    @Test void defaultsNeverMixSimulatedWithReal() {
        var real=catalog.query("","","","","",null,null,"real","year",0,20,null);
        assertEquals(0L,catalog.search(real).get("total"));assertTrue((long)catalog.search(query("",null)).get("total")>=64);
    }
    @Test void invalidQueryIsDifferentFromEmptyResult() {
        assertThrows(ApiException.class,()->catalog.query("","","","","",2025,2020,"demo","year",0,20,null));
        assertEquals(0L,catalog.search(query("no-such-title-123456",null)).get("total"));
        assertThrows(ApiException.class,()->query("",Long.MAX_VALUE));
    }
    @Test void samePersonInstitutionMustBelongToSameContribution() {
        var correct=catalog.query("","","S1","I1","",null,null,"demo","year",0,20,null);
        var wrong=catalog.query("","","S1","I2","",null,null,"demo","year",0,20,null);
        assertTrue((long)catalog.search(correct).get("total")>0);assertEquals(0L,catalog.search(wrong).get("total"));
    }
    @Test void normalizeDoiAndDoNotInventDatePrecision() {
        assertEquals("10.1234/test",ImportService.normalizeDoi(" HTTPS://DOI.ORG/10.1234/TEST "));
        assertThrows(ApiException.class,()->ImportService.normalizeDoi("not a doi"));
        var n=ImportService.normalize(sample(1),"test");assertEquals("year",n.precision());
        var missing=ImportService.normalize(sample(0),"test");assertNull(missing.year());assertNull(missing.precision());
    }
    @Test void replayAndCrossSourceDoiDoNotDuplicateWork() {
        long before=db.count("SELECT COUNT(*) FROM work");var w=sample(0);
        String key=Db.id();var batch=new ImportService.Batch(key,"test-"+key,List.of(w));
        var first=imports.ingest(batch,admin);var replay=imports.ingest(batch,admin);
        assertEquals(first.get("id"),replay.get("id"));assertEquals(before,db.count("SELECT COUNT(*) FROM work"));
        assertThrows(ApiException.class,()->imports.ingest(new ImportService.Batch(key,"other",List.of(w)),admin));
    }
    @Test void failedBatchRollsBackWorkAndReleaseAndSource() {
        long version=db.count("SELECT revision FROM catalog_release"),count=db.count("SELECT COUNT(*) FROM work");
        String key=Db.id();var valid=sample(100001);var bad=sample(100002);
        var broken=new ImportService.WorkInput(bad.type()," ",bad.date(),bad.doi(),bad.identifier(),bad.identifierType(),bad.authority(),bad.abstractText(),bad.venue(),bad.citationCount(),bad.citationSource(),bad.oaStatus(),bad.simulated(),bad.sourceKey(),bad.sourceUrl(),bad.contributors(),bad.institutionIds(),bad.fields(),bad.details());
        assertThrows(ApiException.class,()->imports.ingest(new ImportService.Batch(key,"rollback",List.of(valid,broken)),admin));
        assertEquals(version,db.count("SELECT revision FROM catalog_release"));assertEquals(count,db.count("SELECT COUNT(*) FROM work"));assertEquals(0,db.count("SELECT COUNT(*) FROM import_task WHERE request_key=?",key));
    }
    @Test void previousReleaseSurvivesNewPublication() {
        var q=query("",null);long total=(long)catalog.search(q).get("total");
        var task=imports.ingest(new ImportService.Batch(Db.id(),"snapshot-test",List.of(sample(ThreadLocalRandom.current().nextInt(200000,100000000)))),admin);
        assertEquals(total,catalog.search(q).get("total"));assertEquals(total+1,catalog.search(query("",null)).get("total"));
        String id=db.one("SELECT id FROM work WHERE revision=?",task.get("revision")).get("id").toString();
        assertThrows(ApiException.class,()->catalog.detail(id,q.revision()));
    }
    @Test void applicantEvidenceIsPrivate() {
        var u=user("RESEARCHER");var other=user("RESEARCHER");var c=pending(u,"PORTAL",scholar(),"");
        assertThrows(ApiException.class,()->claims.detail(c.get("id").toString(),other));
        assertNotNull(claims.detail(c.get("id").toString(),u));
        assertThrows(ApiException.class,()->claims.list(other,true));
    }
    @Test void ordinaryAccountCannotClaimPortalBeforeIdentityApproval() {
        var u=user("USER");assertThrows(ApiException.class,()->pending(u,"PORTAL",scholar(),""));
        var identity=pending(u,"IDENTITY",u.id(),"");action(action(identity,"TAKE",admin),"APPROVE",admin);
        assertEquals("RESEARCHER",db.one("SELECT role FROM app_user WHERE id=?",u.id()).get("role"));
        assertEquals(0,db.count("SELECT COUNT(*) FROM portal_binding WHERE user_id=?",u.id()));
    }
    @Test void submittingEditedDraftSavesMaterialAndRejectsStaleVersion() {
        var applicant=user("USER");
        var draft=claims.create(new ClaimService.Create("IDENTITY",applicant.id(),"草稿原始材料",""),applicant);
        String id=draft.get("id").toString();
        var submitted=claims.action(id,new ClaimService.Action(0,"SUBMIT","","补全后的机构与身份证明"),applicant);
        assertEquals("PENDING_REVIEW",submitted.get("state"));
        assertEquals("补全后的机构与身份证明",submitted.get("evidence"));
        assertEquals(2,((Number)submitted.get("materialVersion")).intValue());
        var stale=assertThrows(ApiException.class,()->claims.action(id,new ClaimService.Action(0,"SUBMIT","","过期窗口的内容"),applicant));
        assertEquals(409,stale.status);
        assertEquals("补全后的机构与身份证明",db.one("SELECT evidence FROM claim WHERE id=?",id).get("evidence"));
    }
    @Test void blankDraftMaterialIsRejectedAndOmittedMaterialPreservesLegacyDraft() {
        var applicant=user("USER");
        var draft=claims.create(new ClaimService.Create("IDENTITY",applicant.id(),"已有的有效材料",""),applicant);
        String id=draft.get("id").toString();
        var invalid=assertThrows(ApiException.class,()->claims.action(id,new ClaimService.Action(0,"SUBMIT","","  "),applicant));
        assertEquals(400,invalid.status);
        var unchanged=db.one("SELECT * FROM claim WHERE id=?",id);
        assertEquals("DRAFT",unchanged.get("state"));assertEquals("已有的有效材料",unchanged.get("evidence"));
        assertEquals(0,((Number)unchanged.get("version")).intValue());
        assertEquals(1,((Number)unchanged.get("materialVersion")).intValue());
        var submitted=claims.action(id,new ClaimService.Action(0,"SUBMIT","",null),applicant);
        assertEquals("PENDING_REVIEW",submitted.get("state"));assertEquals("已有的有效材料",submitted.get("evidence"));
        assertEquals(1,((Number)submitted.get("materialVersion")).intValue());
    }
    @Test void supplementPreservesHistoryAndIncreasesMaterialVersion() {
        var u=user("RESEARCHER");var c=action(action(pending(u,"PORTAL",scholar(),""),"TAKE",admin),"NEED_MORE_INFO",admin);
        c=action(c,"SUBMIT",u);assertEquals("PENDING_REVIEW",c.get("state"));assertEquals(2,((Number)c.get("materialVersion")).intValue());
        assertEquals(0,db.count("SELECT COUNT(*) FROM portal_binding WHERE user_id=?",u.id()));
        assertTrue(db.count("SELECT COUNT(*) FROM audit_event WHERE object_id=?",c.get("id"))>=9);
    }
    @Test void expiredReviewLeaseCannotApproveButCanBeRetaken() {
        var u=user("RESEARCHER");var c=action(pending(u,"PORTAL",scholar(),""),"TAKE",admin);
        db.update("UPDATE claim SET lease_until=0 WHERE id=?",c.get("id"));
        assertThrows(ApiException.class,()->action(c,"APPROVE",admin));
        assertEquals("UNDER_REVIEW",action(c,"TAKE",admin).get("state"));
    }
    @Test void concurrentApprovalAndWithdrawalHaveExactlyOneWinner() throws Exception {
        var u=user("RESEARCHER");String target=scholar();var c=action(pending(u,"PORTAL",target,""),"TAKE",admin);
        var results=race(()->action(c,"APPROVE",admin),()->action(c,"WITHDRAW",u));
        assertEquals(1,results.stream().filter(Boolean::booleanValue).count());
        var finalState=db.one("SELECT state FROM claim WHERE id=?",c.get("id")).get("state");
        assertEquals(finalState.equals("APPROVED")?1:0,db.count("SELECT COUNT(*) FROM portal_binding WHERE scholar_id=?",target));
    }
    @Test void concurrentCompetingPortalClaimsCannotCreateTwoOwners() throws Exception {
        String target=scholar();var a=user("RESEARCHER");var b=user("RESEARCHER");
        var ca=action(pending(a,"PORTAL",target,""),"TAKE",admin);var cb=action(pending(b,"PORTAL",target,""),"TAKE",admin);
        var results=race(()->action(ca,"APPROVE",admin),()->action(cb,"APPROVE",admin));
        assertEquals(1,results.stream().filter(Boolean::booleanValue).count());assertEquals(1,db.count("SELECT COUNT(*) FROM portal_binding WHERE scholar_id=?",target));
    }
    @Test void coauthorsCanBothClaimAndRevokeOnlyOwnRelationship() {
        var a=user("RESEARCHER");var b=user("RESEARCHER");portal(a,scholar());portal(b,scholar());
        var task=imports.ingest(new ImportService.Batch(Db.id(),"coauthor-test",List.of(sample(ThreadLocalRandom.current().nextInt(30000,1000000)*8))),admin);
        String work=db.one("SELECT id FROM work WHERE revision=?",task.get("revision")).get("id").toString();
        action(action(pending(a,"OUTCOME",work,"AUTHOR"),"TAKE",admin),"APPROVE",admin);
        action(action(pending(b,"OUTCOME",work,"AUTHOR"),"TAKE",admin),"APPROVE",admin);
        assertEquals(2,db.count("SELECT COUNT(*) FROM outcome_binding WHERE work_id=?",work));
        action(action(pending(a,"REVOKE",work,"AUTHOR"),"TAKE",admin),"APPROVE",admin);
        assertEquals(1,db.count("SELECT COUNT(*) FROM outcome_binding WHERE work_id=?",work));assertEquals(1,db.count("SELECT COUNT(*) FROM work WHERE id=?",work));
    }
    @Test void graphReturnsEvidenceAndDistinguishesSameNamePeople() {
        var q=catalog.query("","PAPER","","","",null,null,"demo","year",0,20,null);
        @SuppressWarnings("unchecked") var result=(Map<String,Object>)graph.path("S1","S2",q);
        assertEquals(true,result.get("found"));assertEquals(1,result.get("hops"));assertFalse(((List<?>)result.get("edges")).isEmpty());
    }
    @Test void statisticsCountCanonicalWorksAndSeparateUnknownCitations() {
        var stats=catalog.stats(query("",null));@SuppressWarnings("unchecked") var metrics=(Map<String,Object>)stats.get("metrics");
        assertEquals(db.count("SELECT COUNT(*) FROM work WHERE simulated=TRUE"),((Number)metrics.get("total")).longValue());
        assertTrue(((Number)metrics.get("citationKnown")).longValue()<((Number)metrics.get("papers")).longValue());
    }
    @Test void organizationAwardKeepsInstitutionWithoutInventingPeople() {
        String id=db.one("SELECT w.id FROM work w WHERE w.type='AWARD' AND NOT EXISTS(SELECT 1 FROM contributor c WHERE c.work_id=w.id) LIMIT 1").get("id").toString();
        var detail=catalog.detail(id,null);
        assertTrue(((List<?>)detail.get("contributors")).isEmpty());
        assertFalse(((List<?>)detail.get("institutions")).isEmpty());
        assertEquals("award_year",detail.get("dateKind"));
    }
    List<Boolean> race(Callable<?> a,Callable<?> b) throws Exception {
        var barrier=new CyclicBarrier(2);
        try(var pool=Executors.newVirtualThreadPerTaskExecutor()) {
            List<Future<Boolean>> jobs=new ArrayList<>();
            for(var task:List.of(a,b)) jobs.add(pool.submit(()->{barrier.await();try{task.call();return true;}catch(ApiException|DataIntegrityViolationException e){return false;}}));
            return List.of(jobs.get(0).get(15,TimeUnit.SECONDS),jobs.get(1).get(15,TimeUnit.SECONDS));
        }
    }
}
