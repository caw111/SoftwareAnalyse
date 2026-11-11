package cn.edu.group2.academic;

import static org.junit.jupiter.api.Assertions.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(properties={
 "spring.datasource.url=${TEST_DB_URL:jdbc:h2:mem:search-stat-tests;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DEFAULT_NULL_ORDERING=HIGH;NON_KEYWORDS=YEAR;DB_CLOSE_DELAY=-1}",
 "spring.datasource.username=${TEST_DB_USER:sa}","spring.datasource.password=${TEST_DB_PASSWORD:}",
 "app.demo=true","app.demo-count=64","management.server.port=0"})
class SearchStatisticsTest {
 @Autowired Db db;@Autowired ImportService imports;@Autowired CatalogService catalog;
 AuthService.Actor admin;
 @BeforeEach void setup() {var row=db.one("SELECT id FROM app_user WHERE username='admin'");admin=new AuthService.Actor(row.get("id").toString(),"admin","Admin","ADMIN");}
 String unique() {return UUID.randomUUID().toString();}
 long n(Map<String,Object> row,String key) {return ((Number)row.get(key)).longValue();}
 @SuppressWarnings("unchecked") List<Map<String,Object>> rows(Object value) {return (List<Map<String,Object>>)value;}
 ImportService.WorkInput paper(String key,String title,String text,String year,Integer citations,List<String> orgs,String field) {
  return new ImportService.WorkInput("PAPER",title,year,"10.77777/"+key,null,null,null,text,"Calibration",citations,citations==null?null:"TestCitation","UNKNOWN",true,key,"https://example.org/"+key,
   List.of(new ImportService.Contributor("S1","Alice","AUTHOR",orgs.isEmpty()?null:orgs.getFirst())),orgs,List.of(field),Map.of());
 }
 long publish(ImportService.WorkInput... values) {return n(imports.ingest(new ImportService.Batch(unique(),"RankFixture",List.of(values)),admin),"revision");}
 CatalogService.Query q(String text,String field,String sort,int page,int size,long revision) {return catalog.query(text,"","","",field,null,null,"demo",sort,page,size,revision);}
 @Test void titleBoostAndStablePaginationAreComputedBeforeSlicing() {
  String field=unique(),a=unique(),b=unique();
  long revision=publish(paper(a,"saffronquasar","neutral","2020",null,List.of(),field),paper(b,"neutral","saffronquasar","2025",null,List.of(),field));
  var first=catalog.search(q("saffronquasar",field,"relevance",0,1,revision));var second=catalog.search(q("saffronquasar",field,"relevance",1,1,revision));
  assertEquals(2L,first.get("total"));var top=rows(first.get("items")).getFirst();var next=rows(second.get("items")).getFirst();
  assertEquals("10.77777/"+a,top.get("doi"));assertEquals("10.77777/"+b,next.get("doi"));
  assertTrue(((Number)top.get("relevanceScore")).doubleValue()>((Number)next.get("relevanceScore")).doubleValue());
  assertEquals(first,catalog.search(q("saffronquasar",field,"relevance",0,1,revision)));
 }
 @Test void normalizedDoiIsExactEvenWhenAnotherAbstractRepeatsIt() {
  String field=unique(),key=unique();String doi="10.77777/"+key;
  long revision=publish(paper(key,"Unrelated exact publication","short","2020",null,List.of(),field),paper(unique(),"Other candidate",(doi+" ").repeat(15),"2026",null,List.of(),field));
  var result=catalog.search(q("https://doi.org/"+doi,field,"relevance",0,20,revision));
  assertEquals(doi,rows(result.get("items")).getFirst().get("doi"));assertEquals(1L,((Number)rows(result.get("items")).getFirst().get("exactMatch")).longValue());
 }
 @Test void tokenizerPreservesIndependentSingleCharactersAndTechnicalWords() {
  assertEquals(List.of("甲","graph"),SearchTerms.query("甲 graph"));assertEquals(List.of("r","language"),SearchTerms.query("R language"));
  assertEquals(List.of("机器","器学","学习"),SearchTerms.query("机器学习"));assertEquals(List.of("c++"),SearchTerms.query("C++"));
  String field=unique();long revision=publish(paper(unique(),"甲 graph C++","","2025",null,List.of(),field),paper(unique(),"乙 graph C++","","2025",null,List.of(),field));
  assertEquals(1L,catalog.search(q("甲 graph",field,"relevance",0,20,revision)).get("total"));
  assertEquals(2L,catalog.search(q("C++",field,"relevance",0,20,revision)).get("total"));
  assertEquals(0L,catalog.search(q("%%%%",field,"relevance",0,20,revision)).get("total"));
 }
 @Test void statisticsUseDistinctWorksKnownZeroAndDocumentFrequency() {
  String field=unique();long revision=publish(paper(unique(),"Quasartopic quasartopic","quasartopic","2020",0,List.of("I1","I2"),field),
    paper(unique(),"Quasartopic","","2021",null,List.of("I1"),field),paper(unique(),"Different subject","",null,5,List.of("I2"),field));
  var stats=catalog.stats(q("",field,"relevance",0,20,revision));
  var metrics=(Map<String,Object>)stats.get("metrics");assertEquals(3,n(metrics,"total"));assertEquals(2,n(metrics,"citationKnown"));
  var orgs=rows(stats.get("institutions"));assertEquals(4,orgs.stream().mapToLong(i->n(i,"count")).sum());assertTrue(orgs.stream().allMatch(i->n(i,"rank")==1));
  var citation=rows(stats.get("citations")).getFirst();assertEquals(5,n(citation,"count"));assertEquals(2,n(citation,"covered"));
  var hot=rows(stats.get("hotspots")).stream().filter(h->h.get("term").equals("quasartopic")).findFirst().orElseThrow();
  assertEquals(2,n(hot,"count"));assertEquals(2.0/3,((Number)hot.get("share")).doubleValue(),1e-9);assertEquals(3L,stats.get("hotspotDenominator"));
  assertTrue(rows(stats.get("years")).stream().anyMatch(y->y.get("year")==null&&n(y,"count")==1));
  assertEquals(2,rows(stats.get("hotspotTrend")).stream().filter(h->h.get("term").equals("quasartopic")).count());
 }
 @Test void relevanceUsesIdTieBreakAndEmptyResultsHaveNoFalsePercentages() {
  String field=unique();long revision=publish(paper(unique(),"equalquasar","","2020",null,List.of(),field),paper(unique(),"equalquasar","","2020",null,List.of(),field));
  var data=rows(catalog.search(q("equalquasar",field,"relevance",0,20,revision)).get("items"));
  var ids=data.stream().map(i->i.get("id").toString()).toList();assertEquals(ids.stream().sorted().toList(),ids);
  var empty=catalog.stats(q("impossiblemissingterm",field,"relevance",0,20,revision));assertEquals(0L,empty.get("hotspotDenominator"));assertTrue(rows(empty.get("hotspots")).isEmpty());
 }
}
