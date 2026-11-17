package cn.edu.group2.academic;

import static org.junit.jupiter.api.Assertions.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.jsoup.Jsoup;
import org.jsoup.nodes.*;
import org.junit.jupiter.api.Test;

class RegisteredHtmlParserTest {
    private final RegisteredHtmlParser parser=new RegisteredHtmlParser();
    @Test void lynuPreservesApplicationGrantDatesAndUnassertedAffiliations() throws Exception {
        var parsed=parser.parse("lynu-patents",fixture("lynu-2025.html"));
        assertEquals(28,parsed.rows().size());assertAllAccepted(parsed);
        assertEquals("2026-06-10",parsed.publicationDate());
        var work=parsed.rows().getFirst().work();
        assertEquals("PATENT",work.type());assertEquals("CN202420753596.1",work.identifier());assertEquals("application_number",work.identifierType());
        assertEquals("2025-01-03",work.date());assertEquals("2024-04-12",work.details().get("applicationDate"));
        assertEquals(List.of("李丽艳","赵涛","任塘珂","董顺波","别鹏"),work.contributors().stream().map(ImportService.Contributor::name).toList());
        assertTrue(work.contributors().stream().allMatch(c->c.scholarId()==null&&c.institutionId()==null&&c.rawAffiliations().isEmpty()));
        assertNull(work.sourceUpdatedAt());assertFalse(work.simulated());assertTrue(work.rawPayload().containsKey("rowHtml"));
        assertEquals(work.rawPayload(),parser.parse("lynu-patents",fixture("lynu-2025.html")).rows().getFirst().work().rawPayload());
    }
    @Test void nsfcUsesFundingYearAndDoesNotPromoteDepartmentNumberToApprovalNumber() throws Exception {
        var parsed=parser.parse("nsfc-projects",fixture("nsfc-2019.html"));
        assertEquals(115,parsed.rows().size());assertAllAccepted(parsed);assertEquals("2020-04-02",parsed.publicationDate());
        var work=parsed.rows().getFirst().work();assertEquals("PROJECT",work.type());assertEquals("2019",work.date());
        assertEquals("3193000529",work.identifier());assertEquals("department_number",work.identifierType());
        assertEquals("297",work.details().get("directFunding"));assertEquals("万元",work.details().get("fundingUnit"));
        assertEquals("张永振",work.contributors().getFirst().name());assertEquals("PI",work.contributors().getFirst().role());
        assertEquals(List.of("中国疾病预防控制中心传染病预防控制所"),work.contributors().getFirst().rawAffiliations());
        assertTrue(work.institutionIds().isEmpty());assertNull(work.contributors().getFirst().institutionId());assertNull(work.sourceUpdatedAt());
    }
    @Test void mostSeparatesGradesPeopleAffiliationsAndNominators() throws Exception {
        var parsed=parser.parse("most-awards",fixture("most-2023.html"));assertEquals(49,parsed.rows().size());assertAllAccepted(parsed);
        assertEquals("2024-06-24",parsed.publicationDate());
        var first=parsed.rows().getFirst().work();assertEquals("2023",first.date());assertEquals("一等奖",first.details().get("awardLevel"));
        assertEquals(5,first.contributors().size());assertEquals("方 忠",first.contributors().getFirst().name());
        assertEquals(List.of("中国科学院物理研究所"),first.contributors().getFirst().rawAffiliations());
        var second=parsed.rows().get(1).work();assertEquals("二等奖",second.details().get("awardLevel"));
        assertEquals("Z-101-2-01",second.identifier());assertEquals("田 刚",second.details().get("nominator"));
        assertEquals(List.of("刘 毅"),second.contributors().stream().map(ImportService.Contributor::name).toList());
        assertTrue(parsed.rows().stream().flatMap(r->r.work().contributors().stream()).allMatch(c->c.scholarId()==null&&c.institutionId()==null));
    }
    @Test void malformedNonemptyRowsAreQuarantinedWithoutShiftingRowIndexes() throws Exception {
        Document document=Jsoup.parse(fixture("lynu-2025.html"));Element first=dataRow(document,"CN202420753596.1");
        first.children().get(1).text("broken-number");
        var parsed=parser.parse("lynu-patents",document.html());assertEquals(28,parsed.rows().size());
        assertEquals("INVALID_APPLICATION_NUMBER",parsed.rows().getFirst().exclusion().get("reason"));assertEquals(0,parsed.rows().getFirst().index());
        assertNotNull(parsed.rows().get(1).work());assertEquals(1,parsed.rows().get(1).index());
        first.children().get(1).text("CN202420753596.1");first.children().get(5).text("20250230");
        assertEquals("INVALID_BUSINESS_DATE",parser.parse("lynu-patents",document.html()).rows().getFirst().exclusion().get("reason"));
    }
    @Test void missingPatentDatesStayUnknownInsteadOfUsingPagePublication() throws Exception {
        Document document=Jsoup.parse(fixture("lynu-2025.html"));Element row=dataRow(document,"CN202420753596.1");
        row.children().get(4).empty();row.children().get(5).empty();
        var work=parser.parse("lynu-patents",document.html()).rows().getFirst().work();
        assertEquals("",work.date());assertEquals("",work.details().get("applicationDate"));assertEquals(true,work.details().get("dateMissing"));
    }
    @Test void changedHeadersWrongBatchesAndEmptyTablesFailClosed() throws Exception {
        String source=fixture("nsfc-2019.html");
        assertEquals("INVALID_RESPONSE",assertThrows(CrawlFailure.class,()->parser.parse("nsfc-projects",source.replace("科学部编号","批准号"))).code);
        assertThrows(CrawlFailure.class,()->parser.parse("nsfc-projects",source.replace("2019年生命科学部重点项目资助清单","2020年生命科学部重点项目资助清单")));
        Document document=Jsoup.parse(source);Element table=dataRow(document,"3193000529").closest("table");
        table.select("tbody tr").remove();assertThrows(CrawlFailure.class,()->parser.parse("nsfc-projects",document.html()));
        assertThrows(CrawlFailure.class,()->parser.parse("nsfc-projects","<title>2019年生命科学部重点项目资助清单</title><p>Access denied</p>"));
    }
    @Test void duplicatesAndMergedDataCellsAreExplicitExclusions() throws Exception {
        Document document=Jsoup.parse(fixture("lynu-2025.html"));Element row=dataRow(document,"CN202420753596.1");
        row.after(row.clone());var parsed=parser.parse("lynu-patents",document.html());assertEquals(29,parsed.rows().size());
        assertEquals("DUPLICATE_SOURCE_IDENTIFIER",parsed.rows().get(1).exclusion().get("reason"));
        row.children().get(2).attr("rowspan","2");assertEquals("UNSUPPORTED_DATA_CELL_SPAN",parser.parse("lynu-patents",document.html()).rows().getFirst().exclusion().get("reason"));
    }
    @Test void explicitlyLabeledOrganizationAwardsNeverBecomePeople() {
        String html="<title>2023年度国家自然科学奖获奖项目目录</title><p>二 等 奖</p><table><tr><td>序号</td><td>编号</td><td>项目名称</td><td>主要完成单位</td><td>提名者</td></tr>"
            +"<tr><td>1</td><td>Z-101-2-01</td><td>组织获奖样例</td><td><p>某研究所</p><p>某大学</p></td><td>某提名机构</td></tr></table>";
        html+=html.substring(html.indexOf("<p>二 等 奖")).replace("二 等 奖","一 等 奖").replace("Z-101-2-01","Z-101-1-01");
        var work=parser.parse("most-awards",html).rows().getFirst().work();assertTrue(work.contributors().isEmpty());
        assertEquals("ORGANIZATION",work.details().get("recipientType"));assertEquals(List.of("某研究所","某大学"),work.details().get("completionUnitsRaw"));
        assertTrue(work.institutionIds().isEmpty());
    }
    @Test void oneMissingOrEmptyAwardGradeCannotSilentlyBecomeAPartialSuccess() throws Exception {
        Document document=Jsoup.parse(fixture("most-2023.html"));Element last=document.select("table").last();assertNotNull(last);
        last.select("tr").first().children().get(1).text("奖励编号");
        assertThrows(CrawlFailure.class,()->parser.parse("most-awards",document.html()));
        Document empty=Jsoup.parse(fixture("most-2023.html"));var rows=empty.select("table").last().select("tr");
        for(int i=1;i<rows.size();i++) rows.get(i).remove();
        assertThrows(CrawlFailure.class,()->parser.parse("most-awards",empty.html()));
    }
    static String fixture(String name) throws Exception {try(var input=RegisteredHtmlParserTest.class.getResourceAsStream("/crawl/"+name)) {assertNotNull(input);return new String(input.readAllBytes(),StandardCharsets.UTF_8);}}
    private static Element dataRow(Document document,String identifier) {return document.select("td").stream().filter(c->c.text().equals(identifier)).findFirst().orElseThrow().parent();}
    private static void assertAllAccepted(RegisteredHtmlParser.Result parsed) {for(var row:parsed.rows()) assertNotNull(row.work(),()->"row "+row.index()+": "+row.exclusion());}
}
