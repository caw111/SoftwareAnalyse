package cn.edu.group2.academic;

import static org.junit.jupiter.api.Assertions.*;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.apache.pdfbox.pdmodel.*;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.junit.jupiter.api.Test;

class CnipaPatentParserTest {
    private final CnipaPatentParser parser=new CnipaPatentParser();
    @Test void officialAttachmentHasThirtyPatentsAcrossFourPagesWithoutInventedDates() throws Exception {
        var result=parser.parse(fixture());assertEquals(30,result.rows().size());assertEquals("",result.publicationDate());
        for(var row:result.rows()) {
            assertNotNull(row.work(),()->"row "+row.index()+": "+row.exclusion());var work=row.work();
            assertEquals("PATENT",work.type());assertEquals("application_number",work.identifierType());assertEquals("CN",work.authority());
            assertEquals("",work.date());assertEquals("",work.details().get("applicationDate"));assertEquals("",work.details().get("grantDate"));assertNull(work.sourceUpdatedAt());
            assertTrue(work.institutionIds().isEmpty());assertTrue(work.contributors().stream().allMatch(c->c.role().equals("INVENTOR")&&c.scholarId()==null&&c.institutionId()==null&&c.rawAffiliations().isEmpty()));
        }
        var first=result.rows().getFirst().work();assertEquals("CN202111257655.3",first.identifier());assertEquals("ZL202111257655.3",first.details().get("patentNumberRaw"));
        assertEquals(3,((List<?>)first.details().get("patentHoldersRaw")).size());assertEquals(9,first.contributors().size());
        var last=result.rows().getLast().work();assertEquals("CN200610066995.7",last.identifier());assertEquals("磷酸奥司他韦颗粒剂及其制备方法",last.title());
        assertEquals(4,last.rawPayload().get("page"));assertEquals(7,last.contributors().size());
    }
    @Test void gridBoundariesKeepWrappedInventorsAndPatentHoldersInTheirOwnRows() throws Exception {
        var result=parser.parse(fixture());var seventh=result.rows().get(6).work();
        assertEquals("桥梁运架机",seventh.title());assertEquals("CN201921689519.X",seventh.identifier());
        assertEquals(List.of("罗九林","蒋中明","朵君泰","王治斌","桂婞","万鹏","周光忠","谌启发","梁志新","周衍领","马遥遥","郭春晖"),seventh.contributors().stream().map(ImportService.Contributor::name).toList());
        assertEquals(List.of("中铁第五勘察设计院集团有限公司"),seventh.details().get("patentHoldersRaw"));
        assertFalse(result.rows().get(7).work().contributors().stream().anyMatch(c->c.name().equals("郭春晖")));
        assertEquals("数据库事务处理方法、装置及服务器",result.rows().get(3).work().title());
        assertEquals(List.of("腾讯科技（深圳）有限公司"),result.rows().get(3).work().details().get("patentHoldersRaw"));
    }
    @Test void rejectsWrongDocumentsAndEnforcesResourceLimits() throws Exception {
        assertThrows(CrawlFailure.class,()->parser.parse("<html>Access denied</html>".getBytes(StandardCharsets.UTF_8)));
        byte[] oversized=new byte[8*1024*1024+1];assertThrows(CrawlFailure.class,()->parser.parse(oversized));
        try(PDDocument document=new PDDocument();var output=new ByteArrayOutputStream()) {
            document.addPage(new PDPage(new PDRectangle(841.9f,595.3f)));document.save(output);
            assertEquals("INVALID_RESPONSE",assertThrows(CrawlFailure.class,()->parser.parse(output.toByteArray())).code);
        }
        try(PDDocument document=new PDDocument();var output=new ByteArrayOutputStream()) {
            for(int i=0;i<33;i++) document.addPage(new PDPage());document.save(output);
            assertThrows(CrawlFailure.class,()->parser.parse(output.toByteArray()));
        }
    }
    private static byte[] fixture() throws Exception {try(var input=CnipaPatentParserTest.class.getResourceAsStream("/crawl/cnipa-25-gold.pdf")) {assertNotNull(input);return input.readAllBytes();}}
}
