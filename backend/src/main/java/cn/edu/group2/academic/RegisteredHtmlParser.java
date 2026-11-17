package cn.edu.group2.academic;

import java.text.Normalizer;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.regex.Pattern;
import org.jsoup.Jsoup;
import org.jsoup.nodes.*;

/** Pure parsing of reviewed announcement tables. Fetching and task budgets belong to the crawler. */
public final class RegisteredHtmlParser {
    public static final String VERSION="registered-html-v1";
    public record Row(int index,ImportService.WorkInput work,Map<String,Object> exclusion) {
        public Row {
            if(index<0||(work==null)==(exclusion==null)) throw new IllegalArgumentException("A row is accepted or quarantined, never both");
            if(exclusion!=null) exclusion=Collections.unmodifiableMap(new LinkedHashMap<>(exclusion));
        }
    }
    public record Result(List<Row> rows,String publicationDate,String pageTitle,String parserVersion) {
        public Result {rows=List.copyOf(rows);}
    }
    private record Source(String id,String batch,String url,String title,String type,List<String> headers,String dateSelector) {}
    private static final Map<String,Source> SOURCES=Map.of(
        "lynu-patents",new Source("lynu-patents","lynu-grants-2025","https://sites.lynu.edu.cn/kycx/info/1221/5141.htm",
            "2025年获得授权的专利清单","PATENT",List.of("序号","申请号","专利类别","发明名称","申请日","授权公告日","发明人"),"[class*=timestyle]"),
        "nsfc-projects",new Source("nsfc-projects","nsfc-life-key-2019","https://www.nsfc.gov.cn/p1/2853/3102/72645.html",
            "2019年生命科学部重点项目资助清单","PROJECT",List.of("序号","科学部编号","项目名称","负责人","依托单位","直接费用（万元）"),".detail-introduce"),
        "most-awards",new Source("most-awards","most-natural-science-2023","https://www.most.gov.cn/cxfw/kjjlcx/kjjl2023/202406/t20240624_191176.html",
            "2023年度国家自然科学奖获奖项目目录","AWARD",List.of("序号","编号","项目名称","主要完成人","提名者"),".notes")
    );
    public Result parse(String sourceId,String html) {
        Source source=SOURCES.get(sourceId);
        if(source==null) throw invalid("未登记的公告解析器");
        if(html==null||html.isBlank()||html.length()>2_500_000) throw invalid("公告正文为空或超出解析上限");
        Document document=Jsoup.parse(html,source.url());
        document.outputSettings().prettyPrint(false);
        String pageTitle=title(document,source.title());
        String publicationDate=publicationDate(document,source.dateSelector());
        var result=new ArrayList<Row>();var seen=new HashSet<String>();int tables=0;
        for(Element table:document.select("table")) {
            var tableRows=table.select("tr").stream().filter(row->row.closest("table")==table).toList();
            int header=-1;boolean organizations=false;
            for(int i=0;i<tableRows.size();i++) {
                var cells=cells(tableRows.get(i));
                if(matches(cells,source.headers())) {header=i;break;}
                if(source.type().equals("AWARD")&&matches(cells,List.of("序号","编号","项目名称","主要完成单位","提名者"))) {header=i;organizations=true;break;}
            }
            if(header<0) continue;
            tables++;
            int rowsBeforeTable=result.size();
            String grade=source.type().equals("AWARD")?awardGrade(table,document):"";
            for(int i=header+1;i<tableRows.size();i++) {
                Element row=tableRows.get(i);var cells=cells(row);
                if(cells.isEmpty()||cells.stream().allMatch(c->text(c).isEmpty())) continue;
                if(matches(cells,source.headers())||source.type().equals("AWARD")&&matches(cells,List.of("序号","编号","项目名称","主要完成单位","提名者"))) continue;
                String heading=compact(row.text());
                if(source.type().equals("AWARD")&&Set.of("一等奖","二等奖","三等奖","特等奖").contains(heading)) {grade=heading;continue;}
                int index=result.size();String rawHtml=row.outerHtml();
                var rawCells=cells.stream().map(c->text(c)).toList();
                try {
                    if(cells.size()!=source.headers().size()) throw new IllegalArgumentException("COLUMN_COUNT_CHANGED");
                    if(cells.stream().anyMatch(c->span(c,"rowspan")>1||span(c,"colspan")>1)) throw new IllegalArgumentException("UNSUPPORTED_DATA_CELL_SPAN");
                    if(!rawCells.getFirst().matches("[0-9]+")) throw new IllegalArgumentException("INVALID_ROW_NUMBER");
                    var raw=new LinkedHashMap<String,Object>();raw.put("sourceId",source.id());raw.put("batchId",source.batch());raw.put("cells",rawCells);raw.put("rowHtml",rawHtml);
                    if(rawHtml.length()>64_000) throw new IllegalArgumentException("ROW_TOO_LARGE");
                    var details=new LinkedHashMap<String,Object>();details.put("parserVersion",VERSION);details.put("batchId",source.batch());
                    details.put("sourcePublicationDate",publicationDate);details.put("sourcePublicationDateKind","page_publication_date");
                    ImportService.WorkInput work=switch(source.type()) {
                        case "PATENT"->patent(source,rawCells,raw,details);
                        case "PROJECT"->project(source,rawCells,raw,details);
                        default->award(source,rawCells,cells.get(3),raw,details,grade,organizations);
                    };
                    if(!seen.add(work.sourceKey())) throw new IllegalArgumentException("DUPLICATE_SOURCE_IDENTIFIER");
                    result.add(new Row(index,work,null));
                } catch(IllegalArgumentException e) {
                    result.add(new Row(index,null,Map.of("index",index,"reason",Objects.toString(e.getMessage(),"INVALID_ROW"),
                        "sourceId",source.id(),"rowChecksum",AuthService.hash(rawHtml),"rowNumber",rawCells.isEmpty()?"":limit(rawCells.getFirst(),80))));
                }
            }
            if(result.size()==rowsBeforeTable) throw invalid("登记公告的一个表格异常为空，不能报告部分成功");
        }
        if(tables!=(source.type().equals("AWARD")?2:1)) throw invalid("登记表格数量或表头变化，不能忽略缺失的奖项组或数据表");
        if(result.isEmpty()) throw invalid("登记公告表格异常为空，不能报告有效空结果");
        return new Result(result,publicationDate,pageTitle,VERSION);
    }
    private static ImportService.WorkInput patent(Source source,List<String> cells,Map<String,Object> raw,Map<String,Object> details) {
        String identifier=required(cells.get(1),200,"MISSING_APPLICATION_NUMBER");
        if(!identifier.matches("CN[0-9]{12}\\.[0-9Xx]")) throw new IllegalArgumentException("INVALID_APPLICATION_NUMBER");
        String title=required(cells.get(3),1000,"MISSING_PATENT_TITLE"),application=date(cells.get(4)),grant=date(cells.get(5));
        if(!application.isEmpty()&&!grant.isEmpty()&&application.compareTo(grant)>0) throw new IllegalArgumentException("GRANT_PRECEDES_APPLICATION");
        details.put("patentType",cells.get(2));details.put("applicationDate",application);details.put("grantDate",grant);
        details.put("applicationNumberRaw",identifier);details.put("grantEvidence",source.url()+"（2025年获得授权的专利清单）");
        details.put("legalStatus","未核验当前法律状态");details.put("sourcePublisher","洛阳师范学院科研处");
        details.put("dateMissing",grant.isEmpty());
        var contributors=people(cells.get(6),"INVENTOR",List.of());
        if(contributors.isEmpty()) throw new IllegalArgumentException("MISSING_INVENTOR");
        return work(source,title,grant,identifier,"application_number","CN",contributors,details,raw);
    }
    private static ImportService.WorkInput project(Source source,List<String> cells,Map<String,Object> raw,Map<String,Object> details) {
        String identifier=required(cells.get(1),200,"MISSING_DEPARTMENT_NUMBER");
        if(!identifier.matches("[0-9]{8,20}")) throw new IllegalArgumentException("INVALID_DEPARTMENT_NUMBER");
        String title=required(cells.get(2),1000,"MISSING_PROJECT_TITLE"),person=required(cells.get(3),100,"MISSING_PRINCIPAL_INVESTIGATOR");
        String host=required(cells.get(4),2000,"MISSING_HOST_INSTITUTION");
        details.put("fundingYear",2019);details.put("departmentNumber",identifier);details.put("numberLabel","科学部编号");
        details.put("fundingAgency","国家自然科学基金委员会");details.put("projectCategory","生命科学部重点项目");
        details.put("hostInstitution",host);details.put("directFunding",cells.get(5));details.put("fundingUnit","万元");
        details.put("fundingCurrency","CNY");details.put("affiliationRelation","project_host_institution");
        // Scientific-department numbers are not asserted to be NSFC approval numbers.
        return work(source,title,"2019",identifier,"department_number","NSFC",
            List.of(new ImportService.Contributor(null,person,"PI",null,null,List.of(host))),details,raw);
    }
    private static ImportService.WorkInput award(Source source,List<String> cells,Element recipientCell,Map<String,Object> raw,Map<String,Object> details,String grade,boolean organizations) {
        String identifier=required(cells.get(1),200,"MISSING_AWARD_NUMBER");
        if(!identifier.matches("[A-Z]-[0-9]{3}-[0-9]-[0-9]{2}")) throw new IllegalArgumentException("INVALID_AWARD_NUMBER");
        String title=required(cells.get(2),1000,"MISSING_AWARD_TITLE");
        if(grade.isEmpty()) throw new IllegalArgumentException("MISSING_AWARD_LEVEL");
        details.put("awardName","国家自然科学奖");details.put("awardYear",2023);details.put("awardLevel",grade);
        details.put("nominator",cells.get(4));details.put("recipientType",organizations?"ORGANIZATION":"PERSON");
        var recipients=new ArrayList<ImportService.Contributor>();var units=new LinkedHashSet<String>();
        var blocks=recipientCell.select("p").stream().filter(p->p.select("p").size()==1).map(RegisteredHtmlParser::text).filter(t->!t.isBlank()).toList();
        if(blocks.isEmpty()) blocks=Arrays.stream(recipientCell.wholeText().split("[;；\\r\\n]+")).map(RegisteredHtmlParser::normalize).filter(t->!t.isBlank()).toList();
        if(blocks.isEmpty()) throw new IllegalArgumentException("MISSING_AWARD_RECIPIENT");
        if(organizations) units.addAll(blocks);
        else for(String block:blocks) {
            int open=block.indexOf('（');char close='）';if(open<0) {open=block.indexOf('(');close=')';}
            String name=block;List<String> affiliations=List.of();
            if(open>=0) {
                int end=block.lastIndexOf(close);
                if(end<=open||!block.substring(end+1).isBlank()) throw new IllegalArgumentException("INVALID_AWARD_AFFILIATION");
                name=normalize(block.substring(0,open));String affiliation=required(normalize(block.substring(open+1,end)),2000,"EMPTY_AWARD_AFFILIATION");
                affiliations=List.of(affiliation);units.add(affiliation);
            }
            recipients.add(new ImportService.Contributor(null,required(name,100,"INVALID_AWARDEE_NAME"),"AWARDEE",null,null,affiliations));
        }
        if(recipients.size()>40||units.size()>20) throw new IllegalArgumentException("TOO_MANY_AWARD_RECIPIENTS");
        details.put("completionUnitsRaw",new ArrayList<>(units));
        return work(source,title,"2023",identifier,"award_project_number","MOST",recipients,details,raw);
    }
    private static ImportService.WorkInput work(Source source,String title,String date,String identifier,String identifierType,String authority,
        List<ImportService.Contributor> contributors,Map<String,Object> details,Map<String,Object> raw) {
        // Announcement publication dates are not trustworthy update timestamps. Changed rows need review.
        return new ImportService.WorkInput(source.type(),title,date,null,identifier,identifierType,authority,"","",null,null,"UNKNOWN",false,
            source.batch()+":"+identifier,source.url(),contributors,List.of(),List.of(),details,raw,null);
    }
    static List<ImportService.Contributor> people(String value,String role,List<String> affiliations) {
        var result=new ArrayList<ImportService.Contributor>();
        for(String name:value.split("[;；、]+")) {name=normalize(name);if(!name.isBlank()) result.add(new ImportService.Contributor(null,required(name,100,"INVALID_PERSON_NAME"),role,null,null,affiliations));}
        if(result.size()>40) throw new IllegalArgumentException("TOO_MANY_CONTRIBUTORS");
        return result;
    }
    private static List<Element> cells(Element row) {return row.children().stream().filter(e->e.tagName().equals("td")||e.tagName().equals("th")).toList();}
    private static boolean matches(List<Element> cells,List<String> names) {
        if(cells.size()!=names.size()) return false;
        for(int i=0;i<names.size();i++) if(!compact(cells.get(i).text()).equals(compact(names.get(i)))) return false;
        return true;
    }
    private static int span(Element cell,String attribute) {try {return cell.hasAttr(attribute)?Integer.parseInt(cell.attr(attribute)):1;}catch(NumberFormatException e){return 2;}}
    private static String awardGrade(Element table,Document document) {
        String latest="";
        for(Element element:document.getAllElements()) {
            if(element==table) break;
            String value=compact(element.text());if(Set.of("一等奖","二等奖","三等奖","特等奖").contains(value)) latest=value;
        }
        return latest;
    }
    private static String title(Document document,String expected) {
        var values=new ArrayList<String>();values.add(document.title());
        for(Element meta:document.select("meta[name]")) if(Set.of("pagetitle","articletitle","title").contains(meta.attr("name").toLowerCase(Locale.ROOT))) values.add(meta.attr("content"));
        for(Element heading:document.select(".detail-title,.title_wide,[class*=titlestyle],h1,h2,h3")) values.add(heading.text());
        for(String value:values) if(compact(value).contains(compact(expected))) return normalize(value);
        throw invalid("公告标题或批次年份与登记来源不一致");
    }
    private static String publicationDate(Document document,String selector) {
        String value=document.select(selector).text();
        var match=Pattern.compile("([12][0-9]{3})[-年]([0-9]{1,2})[-月]([0-9]{1,2})日?").matcher(value);
        if(!match.find()) return "";
        try {return LocalDate.of(Integer.parseInt(match.group(1)),Integer.parseInt(match.group(2)),Integer.parseInt(match.group(3))).toString();}
        catch(RuntimeException invalid) {return "";}
    }
    static String normalize(String value) {return Normalizer.normalize(Objects.toString(value,""),Normalizer.Form.NFC).replaceAll("[\\p{Z}\\s]+"," ").strip();}
    private static String compact(String value) {return normalize(value).replaceAll("[\\p{Z}\\s]+","");}
    private static String text(Element element) {return normalize(element.text());}
    private static String date(String value) {
        value=normalize(value);if(value.isEmpty()||Set.of("-","--","未知","未提供").contains(value)) return "";
        try {return (value.matches("[0-9]{8}")?LocalDate.parse(value,DateTimeFormatter.BASIC_ISO_DATE):LocalDate.parse(value)).toString();}
        catch(RuntimeException invalid) {throw new IllegalArgumentException("INVALID_BUSINESS_DATE");}
    }
    static String required(String value,int max,String message) {if(value==null||value.isBlank()||value.length()>max) throw new IllegalArgumentException(message);return value;}
    private static String limit(String value,int max) {return value.length()>max?value.substring(0,max):value;}
    static CrawlFailure invalid(String message) {return new CrawlFailure("INVALID_RESPONSE",message,false);}
}
