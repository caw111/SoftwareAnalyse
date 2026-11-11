package cn.edu.group2.academic;

import static org.junit.jupiter.api.Assertions.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/** Small serial correctness scenarios; no throughput/latency load generation. */
@SpringBootTest(properties={
    "spring.datasource.url=${TEST_DB_URL:jdbc:h2:mem:revision-tests;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DEFAULT_NULL_ORDERING=HIGH;NON_KEYWORDS=YEAR;DB_CLOSE_DELAY=-1}",
    "spring.datasource.username=${TEST_DB_USER:sa}","spring.datasource.password=${TEST_DB_PASSWORD:}",
    "app.demo=true","app.demo-count=64","management.server.port=0"})
class CatalogRevisionIntegrationTest {
    @Autowired Db db;@Autowired ImportService imports;@Autowired CatalogService catalog;@Autowired GraphService graph;
    AuthService.Actor admin;
    @BeforeEach void setup() {
        var user=db.one("SELECT * FROM app_user WHERE username='admin'");
        admin=new AuthService.Actor(user.get("id").toString(),"admin","Admin","ADMIN");
    }
    String unique() {return UUID.randomUUID().toString();}
    long revision() {return db.count("SELECT revision FROM catalog_release WHERE id=1");}
    long number(Map<String,Object> row,String key) {return ((Number)row.get(key)).longValue();}
    ImportService.WorkInput work(String key,String title,String year,int citations,String field,String scholar,long updated) {
        return new ImportService.WorkInput("PAPER",title,year,"10.99998/"+key,null,null,null,"版本验证摘要","合成版本期刊",citations,
            "版本验收来源","UNKNOWN",true,key,"https://example.org/revision/"+key,
            List.of(new ImportService.Contributor("S1","林知远","AUTHOR","I1"),new ImportService.Contributor(scholar,"合成协作学者","AUTHOR","I2")),
            List.of("I1","I2"),List.of(field),Map.of("purpose","serial functional acceptance"),
            Map.of("key",key,"title",title,"year",year,"citations",citations,"field",field,"scholar",scholar,"updated",updated),updated);
    }
    Map<String,Object> ingest(String source,ImportService.WorkInput... works) {return imports.ingest(new ImportService.Batch(unique(),source,List.of(works)),admin);}
    String id(String doi) {return db.one("SELECT id FROM work WHERE doi=?","10.99998/"+doi).get("id").toString();}
    CatalogService.Query query(String text,String field,long revision) {return catalog.query(text,"PAPER","","",field,null,null,"demo","year",0,20,revision);}
    @SuppressWarnings("unchecked") List<Map<String,Object>> rows(Object value) {return (List<Map<String,Object>>)value;}

    @Test void ownSourceUpdatePreservesIdBindingsAndAllOldReleaseViews() {
        String key=unique(),source="revision-"+key,oldField="before-"+key,newField="after-"+key;
        var first=ingest(source,work(key,"OldSnapshotAlpha","2020",4,oldField,"S2",1000));
        String id=id(key);long before=number(first,"revision");
        String researcher=db.one("SELECT id FROM app_user WHERE username='researcher'").get("id").toString();
        db.update("INSERT INTO outcome_binding(user_id,work_id,scholar_id,contribution_role) VALUES(?,?,?,'AUTHOR')",researcher,id,"S1");
        var changed=ingest(source,work(key,"NewSnapshotBeta","2025",17,newField,"S3",2000));
        long after=number(changed,"revision");
        assertEquals(1,number(changed,"updated"));assertEquals(id,id(key));assertTrue(after>before);
        assertEquals(1,db.count("SELECT COUNT(*) FROM outcome_binding WHERE user_id=? AND work_id=?",researcher,id));
        // Deliberately query the old release only after the update, so an old cache cannot hide a SQL bug.
        assertEquals("OldSnapshotAlpha",catalog.detail(id,before).get("title"));
        assertEquals("NewSnapshotBeta",catalog.detail(id,after).get("title"));
        assertEquals(1L,catalog.search(query("OldSnapshotAlpha",oldField,before)).get("total"));
        assertEquals(0L,catalog.search(query("OldSnapshotAlpha",oldField,after)).get("total"));
        assertEquals(1L,catalog.search(query("NewSnapshotBeta",newField,after)).get("total"));
        assertEquals(1L,number((Map<String,Object>)catalog.stats(query("",oldField,before)).get("metrics"),"total"));
        assertEquals(0L,number((Map<String,Object>)catalog.stats(query("",oldField,after)).get("metrics"),"total"));
        assertTrue(rows(catalog.detail(id,before).get("contributors")).stream().anyMatch(c->"S2".equals(c.get("scholarId"))));
        assertFalse(rows(catalog.detail(id,after).get("contributors")).stream().anyMatch(c->"S2".equals(c.get("scholarId"))));
        assertEquals(true,((Map<?,?>)graph.path("S1","S2",query("",oldField,before))).get("found"));
        assertEquals(false,((Map<?,?>)graph.path("S1","S2",query("",newField,after))).get("found"));
        assertEquals(2,db.count("SELECT COUNT(*) FROM work_revision WHERE id=?",id));
        assertEquals(2,db.count("SELECT COUNT(*) FROM search_document WHERE work_id=?",id));
        assertEquals(after,db.count("SELECT valid_to FROM work_revision WHERE id=? AND revision=?",id,before));
    }

    @Test void unchangedHashHasAnotherObservationButNoExtraContentOrRelease() {
        String key=unique(),source="unchanged-"+key;
        var input=work(key,"UnchangedObservation","2024",3,"unchanged","S2",1000);
        var first=ingest(source,input);long before=revision();
        var second=ingest(source,input);
        assertEquals(1,number(second,"unchanged"));assertEquals(0,number(second,"updated"));assertEquals(before,revision());
        assertEquals(1,db.count("SELECT COUNT(*) FROM source_record WHERE source_name=? AND source_key=?",source,key));
        assertEquals(2,db.count("SELECT COUNT(*) FROM source_observation o JOIN source_record s ON s.id=o.source_id WHERE s.source_name=? AND s.source_key=?",source,key));
        assertEquals(1,db.count("SELECT COUNT(*) FROM work_revision WHERE id=?",id(key)));
        assertNotEquals(first.get("id"),second.get("id"));
    }

    @Test void crossSourceStrongIdentifierLinksEqualContentButQueuesConflictingFields() {
        String key=unique();var original=work(key,"PrimaryMetadata","2024",3,"cross","S2",1000);
        ingest("primary-"+key,original);String workId=id(key);
        long first=revision();var equivalent=ingest("secondary-equal-"+key,original);
        assertEquals(0,number(equivalent,"inserted"));assertEquals(0,number(equivalent,"conflicts"));assertTrue(revision()>first);
        long second=revision();var conflict=ingest("secondary-different-"+key,work(key,"ConflictingMetadata","2025",99,"different","S3",2000));
        assertEquals(1,number(conflict,"conflicts"));assertEquals(second,revision());
        assertEquals("PrimaryMetadata",catalog.detail(workId,null).get("title"));
        assertEquals(1,db.count("SELECT COUNT(*) FROM work WHERE doi=?","10.99998/"+key));
        assertEquals(1,db.count("SELECT COUNT(*) FROM metadata_conflict WHERE work_id=? AND reason='CROSS_SOURCE_FIELD_CONFLICT'",workId));
        assertEquals(1,rows(catalog.detail(workId,first).get("sources")).size());
        assertEquals(2,rows(catalog.detail(workId,null).get("sources")).size());
        assertEquals(3,db.count("SELECT COUNT(*) FROM source_record WHERE work_id=?",workId));
    }

    @Test void staleSourceAndManualLockCannotOverwritePublishedContent() {
        String key=unique(),source="time-"+key;
        ingest(source,work(key,"NewestRecord","2025",20,"time","S2",2000));String id=id(key);long before=revision();
        assertEquals(1,number(ingest(source,work(key,"StaleRecord","2020",1,"time","S2",1000)),"conflicts"));
        assertEquals("NewestRecord",catalog.detail(id,null).get("title"));
        db.update("UPDATE work SET metadata_locked=TRUE WHERE id=?",id);
        assertEquals(1,number(ingest(source,work(key,"NewerButLocked","2026",21,"time","S2",3000)),"conflicts"));
        assertEquals(before,revision());
        assertEquals(Set.of("STALE_SOURCE_OBSERVATION","MANUALLY_LOCKED_METADATA"),new HashSet<>(db.rows("SELECT reason FROM metadata_conflict WHERE work_id=?",id).stream().map(x->x.get("reason").toString()).toList()));
    }

    @Test void sourceKeyChangingItsStrongIdentifierIsQuarantinedWithRawEvidence() {
        String key=unique(),source="identity-"+key;
        var old=work(key,"StableIdentity","2024",2,"identity","S2",1000);ingest(source,old);long before=revision();
        var changed=new ImportService.WorkInput(old.type(),old.title(),old.date(),"10.99998/other-"+key,old.identifier(),old.identifierType(),old.authority(),
            old.abstractText(),old.venue(),old.citationCount(),old.citationSource(),old.oaStatus(),old.simulated(),key,old.sourceUrl(),old.contributors(),old.institutionIds(),old.fields(),old.details(),
            Map.of("DOI","10.99998/other-"+key,"updated",2000),2000L);
        assertEquals(1,number(ingest(source,changed),"conflicts"));assertEquals(before,revision());
        assertEquals(0,db.count("SELECT COUNT(*) FROM work WHERE doi=?","10.99998/other-"+key));
        assertEquals(1,db.count("SELECT COUNT(*) FROM source_record WHERE work_id=? AND accepted=FALSE",id(key)));
        assertEquals(1,db.count("SELECT COUNT(*) FROM metadata_conflict WHERE work_id=? AND reason='SOURCE_IDENTITY_CONFLICT'",id(key)));
    }

    @Test void finalSnapshotOfMultipleChangesInOneBatchIsUnique() {
        String key=unique();var first=work(key,"BatchInitial","2020",1,"batch","S2",1000);
        var second=work(key,"BatchFinal","2025",2,"batch","S3",2000);
        var result=ingest("batch-"+key,first,second);String id=id(key);
        assertEquals(1,number(result,"inserted"));assertEquals(1,number(result,"updated"));
        assertEquals(1,db.count("SELECT COUNT(*) FROM work_revision WHERE id=?",id));
        assertEquals(1,db.count("SELECT COUNT(*) FROM search_document WHERE work_id=?",id));
        assertEquals("BatchFinal",catalog.detail(id,null).get("title"));
    }

    @Test void malformedBatchRollsBackCurrentSourcesSnapshotsAndIndex() {
        String key=unique();var valid=work(key,"RollbackRevision","2024",3,"rollback","S2",1000);
        var invalid=work(unique()," ","2024",3,"rollback","S2",1000);long before=revision();
        assertThrows(ApiException.class,()->ingest("rollback-"+key,valid,invalid));
        assertEquals(before,revision());assertEquals(0,db.count("SELECT COUNT(*) FROM work WHERE doi=?","10.99998/"+key));
        assertEquals(0,db.count("SELECT COUNT(*) FROM source_head WHERE source_name=?","rollback-"+key));
        assertEquals(0,db.count("SELECT COUNT(*) FROM source_record WHERE source_name=?","rollback-"+key));
        assertEquals(0,db.count("SELECT COUNT(*) FROM work_revision WHERE title='RollbackRevision'"));
    }

    @Test void trustedOrcidOnlyCreatesMetadataAndPreservesRawAffiliations() {
        String key=unique();var base=work(key,"OrcidMetadata","2024",3,"orcid","S2",1000);
        var person=new ImportService.Contributor(null,"同名作者","AUTHOR",null,"https://orcid.org/0000-0002-1825-0097",List.of("Department A, Example University","Example Institute"));
        var input=new ImportService.WorkInput(base.type(),base.title(),base.date(),base.doi(),null,null,null,base.abstractText(),base.venue(),3,"Crossref","UNKNOWN",true,
            key,base.sourceUrl(),List.of(person),List.of(),List.of(),Map.of(),Map.of("DOI",base.doi(),"author",List.of(Map.of("ORCID",person.orcid()))),1000L);
        long users=db.count("SELECT COUNT(*) FROM app_user"),portals=db.count("SELECT COUNT(*) FROM portal_binding");
        imports.ingestTrustedCrossref(new ImportService.Batch(unique(),"Crossref",List.of(input)),admin);
        var contributor=db.one("SELECT * FROM contributor WHERE work_id=?",id(key));
        assertEquals("DEMO-ORCID-0000-0002-1825-0097",contributor.get("scholarId"));
        assertTrue(contributor.get("rawAffiliationsJson").toString().contains("Department A, Example University"));
        assertNull(contributor.get("institutionId"));assertEquals(users,db.count("SELECT COUNT(*) FROM app_user"));assertEquals(portals,db.count("SELECT COUNT(*) FROM portal_binding"));
        String other=unique();var manual=new ImportService.WorkInput(input.type(),input.title(),input.date(),"10.99998/"+other,null,null,null,input.abstractText(),input.venue(),3,"Crossref","UNKNOWN",true,
            other,input.sourceUrl(),List.of(person),List.of(),List.of(),Map.of(),Map.of("DOI","10.99998/"+other),1000L);
        imports.ingest(new ImportService.Batch(unique(),"Crossref",List.of(manual)),admin);
        assertNull(db.one("SELECT scholar_id FROM contributor WHERE work_id=?",id(other)).get("scholarId"));
    }
    @Test void identicalRawCanBeReprocessedByNewParserWithoutOverwritingPriorMetadata() {
        String key=unique(),source="reparse-"+key;
        var first=work(key,"InitialParserTitle","2024",4,"reparse","S2",1000);
        ingest(source,first);String workId=id(key);long before=revision();
        var next=new ImportService.WorkInput(first.type(),"CorrectedParserTitle",first.date(),first.doi(),first.identifier(),first.identifierType(),first.authority(),first.abstractText(),first.venue(),first.citationCount(),first.citationSource(),first.oaStatus(),first.simulated(),first.sourceKey(),first.sourceUrl(),first.contributors(),first.institutionIds(),first.fields(),Map.of("parserVersion","parser-v2"),first.rawPayload(),first.sourceUpdatedAt());
        var result=ingest(source,next);
        assertEquals(1,number(result,"conflicts"));assertEquals(before,revision());
        assertEquals("InitialParserTitle",catalog.detail(workId,null).get("title"));
        assertEquals(1,db.count("SELECT COUNT(*) FROM source_record WHERE work_id=?",workId));
        assertEquals(2,db.count("SELECT COUNT(*) FROM source_processing p JOIN source_record s ON s.id=p.source_id WHERE s.work_id=?",workId));
        assertEquals(1,db.count("SELECT COUNT(*) FROM source_processing p JOIN source_record s ON s.id=p.source_id WHERE s.work_id=? AND p.parser_version='parser-v2' AND p.result='REVIEW_REQUIRED'",workId));
    }

}
