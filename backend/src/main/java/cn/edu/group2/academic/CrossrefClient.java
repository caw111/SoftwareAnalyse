package cn.edu.group2.academic;

import java.net.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import tools.jackson.databind.*;

@Service
public class CrossrefClient {
    static final String ENDPOINT="https://api.crossref.org";
    private final CrossrefTransport transport;private final CrawlStore store;private final ObjectMapper json;private final String mailto;
    CrossrefClient(CrossrefTransport transport,CrawlStore store,ObjectMapper json,@Value("${app.crawl.contact-email:}") String mailto) {
        this.transport=transport;this.store=store;this.json=json;this.mailto=mailto.strip();
        if(!this.mailto.isEmpty()&&!this.mailto.matches("[^\\s@]+@[^\\s@]+\\.[^\\s@]+")) throw new IllegalArgumentException("CRAWL_CONTACT_EMAIL must be a valid contact address");
    }
    record Page(String url,String raw,int status,String etag,String lastModified,int received,
        List<ImportService.WorkInput> works,List<Map<String,Object>> exclusions,String nextCursor,boolean finished) {}
    boolean contactConfigured() {return !mailto.isEmpty();}
    static String encode(String value) {return URLEncoder.encode(value,java.nio.charset.StandardCharsets.UTF_8);}
    URI requestUri(CrawlStore.Lease lease) {
        var task=lease.task();String doi=CrawlStore.str(task,"doi");
        if(!doi.isEmpty()) return URI.create(ENDPOINT+"/works/"+encode(doi)+(mailto.isEmpty()?"":"?mailto="+encode(mailto)));
        String filter="from-index-date:"+task.get("fromDate")+",until-index-date:"+task.get("untilDate");
        if(!CrawlStore.str(task,"issn").isEmpty()) filter+=",issn:"+task.get("issn");
        if(task.get("fromPublicationYear")!=null) filter+=",from-pub-date:"+task.get("fromPublicationYear");
        if(task.get("toPublicationYear")!=null) filter+=",until-pub-date:"+task.get("toPublicationYear");
        String query=CrawlStore.str(task,"queryText");
        return URI.create(ENDPOINT+"/works?filter="+encode(filter)+"&rows="+rowsFor(lease)+"&cursor="+encode(CrawlStore.str(task,"nextCursor"))
            +(query.isEmpty()?"":"&query="+encode(query))+(mailto.isEmpty()?"":"&mailto="+encode(mailto)));
    }
    private static long rowsFor(CrawlStore.Lease lease) {return Math.min(CrawlStore.num(lease.task(),"pageSize"),CrawlStore.num(lease.task(),"maxRecords")-CrawlStore.num(lease.task(),"received"));}
    Page fetch(CrawlStore.Lease lease) {
        URI uri=requestUri(lease);checkRobots(lease,uri.getRawPath());
        var cached=store.cached(uri.toString());var headers=headers();
        if(cached!=null) {
            if(!CrawlStore.str(cached,"etag").isEmpty()) headers.put("If-None-Match",CrawlStore.str(cached,"etag"));
            if(!CrawlStore.str(cached,"lastModified").isEmpty()) headers.put("If-Modified-Since",CrawlStore.str(cached,"lastModified"));
        }
        var response=request(lease,uri,headers);
        String body=response.body();
        if(response.status()==304) {
            if(cached==null) throw new CrawlFailure("INVALID_RESPONSE","收到 304 但没有对应的完整缓存",false);
            body=CrawlStore.str(cached,"body");
            if(response.header("Cache-Control").toLowerCase(Locale.ROOT).contains("no-store")) store.cache(lease,uri.toString(),response,0);
        } else {
            requireSuccess(response,lease);
            if(!response.header("Content-Type").toLowerCase(Locale.ROOT).contains("json")) throw new CrawlFailure("NON_JSON","来源未返回 JSON，可能是登录页或访问条件页面",false);
            store.cache(lease,uri.toString(),response,Db.now()+86_400_000);
        }
        return parse(lease,uri.toString(),body,response);
    }
    private Map<String,String> headers() {
        var headers=new LinkedHashMap<String,String>();headers.put("Accept","application/json");
        headers.put("User-Agent","AcademicPlatform/0.3 (Crossref metadata adapter"+(mailto.isEmpty()?"":"; mailto:"+mailto)+")");return headers;
    }
    private CrossrefTransport.Response request(CrawlStore.Lease lease,URI uri,Map<String,String> headers) {
        long wait=store.reserveRequest(lease);
        if(wait>0) try {Thread.sleep(wait);} catch(InterruptedException e) {Thread.currentThread().interrupt();throw new CrawlFailure("INTERRUPTED","请求等待被中断",true);}
        store.assertActive(lease);
        var response=transport.get(uri,headers);
        try {
            double interval=Double.parseDouble(response.header("X-Rate-Limit-Interval").replace("s",""));
            double limit=Double.parseDouble(response.header("X-Rate-Limit-Limit"));
            if(interval>0&&limit>0) store.advertisedRate(lease,(long)Math.ceil(interval*1000/limit));
        } catch(NumberFormatException ignored) { }
        return response;
    }
    private void requireSuccess(CrossrefTransport.Response response,CrawlStore.Lease lease) {
        int status=response.status();
        String body=response.body().toLowerCase(Locale.ROOT);
        boolean html=response.header("Content-Type").toLowerCase(Locale.ROOT).contains("html")||body.stripLeading().startsWith("<html")||body.stripLeading().startsWith("<!doctype html");
        if(response.header("cf-mitigated").equalsIgnoreCase("challenge")||html&&(body.contains("captcha")||body.contains("cf-chl-")||body.contains("challenge-platform")||body.contains("verify you are human")||body.contains("验证码")||body.contains("人机验证")))
            throw new CrawlFailure("ACCESS_CHALLENGE","来源要求验证码或人机核验，需人工复核访问条件；不会绕过挑战",false);
        if(status==200) return;
        if(status==401||status==403||status==412||status>=300&&status<400) throw new CrawlFailure("ACCESS_RESTRICTED","来源拒绝访问或要求跳转，请管理员核查访问条件；不会绕过限制",false);
        if((status==400||status==404)&&!CrawlStore.str(lease.task(),"doi").isEmpty()) throw new CrawlFailure("DOI_NOT_FOUND","来源未返回该 DOI，请核对标识",false);
        if((status==400||status==404)&&!CrawlStore.str(lease.task(),"nextCursor").equals("*"))
            throw new CrawlFailure("CURSOR_EXPIRED","游标可能已过期，将幂等重扫原固定窗口",true,0,true);
        boolean retry=status==408||status==429||status>=500;
        throw new CrawlFailure(status==429?"RATE_LIMITED":"HTTP_"+status,"来源返回 HTTP "+status,retry,retryAfter(response.header("Retry-After")),false);
    }
    static long retryAfter(String value) {
        if(value==null||value.isBlank()) return 0;
        try {return Math.addExact(Db.now(),Math.multiplyExact(Math.max(0,Long.parseLong(value.strip())),1000));}
        catch(ArithmeticException e) {return Long.MAX_VALUE;}
        catch(NumberFormatException e) {
            try {return ZonedDateTime.parse(value,DateTimeFormatter.RFC_1123_DATE_TIME).toInstant().toEpochMilli();} catch(RuntimeException ignored) {return 0;}
        }
    }
    private void checkRobots(CrawlStore.Lease lease,String path) {
        String url=ENDPOINT+"/robots.txt";var cached=store.cached(url);String body;
        if(cached!=null&&CrawlStore.num(cached,"expiresAt")>Db.now()) body=CrawlStore.str(cached,"body");
        else {
            var headers=headers();headers.put("Accept","text/plain");var response=request(lease,URI.create(url),headers);
            if(response.status()==404||response.status()==410) body="";
            else if(response.status()==200) {
                body=response.body();if(body.stripLeading().startsWith("<")) throw new CrawlFailure("ROBOTS_DENIED","robots.txt 返回网页外壳，需核查来源",false);
            }
            else {requireSuccess(response,lease);throw new CrawlFailure("ROBOTS_DENIED","来源 robots.txt 不可核验，暂不采集",false);}
            store.cache(lease,url,new CrossrefTransport.Response(200,response.headers(),body),Db.now()+86_400_000);
        }
        if(!robotsAllows(body,path)) throw new CrawlFailure("ROBOTS_DENIED","来源 robots.txt 不允许当前采集路径",false);
    }
    static boolean robotsAllows(String body,String path) {
        record Rule(String path,boolean allow) {}
        var specific=new ArrayList<Rule>();var wildcard=new ArrayList<Rule>();var agents=new ArrayList<String>();boolean rulesStarted=false,specificSeen=false;
        for(String line:body.split("\\R")) {
            String value=line.split("#",2)[0].strip();int colon=value.indexOf(':');if(colon<0) continue;
            String key=value.substring(0,colon).strip().toLowerCase(Locale.ROOT),text=value.substring(colon+1).strip();
            if(key.equals("user-agent")) {if(rulesStarted) {agents.clear();rulesStarted=false;}agents.add(text.toLowerCase(Locale.ROOT));if(text.equalsIgnoreCase("AcademicPlatform")) specificSeen=true;}
            else if(key.equals("allow")||key.equals("disallow")) {
                rulesStarted=true;if(text.isEmpty()) continue;
                var rule=new Rule(text,key.equals("allow"));
                if(agents.stream().anyMatch(a->a.equals("academicplatform"))) specific.add(rule);
                else if(agents.contains("*")) wildcard.add(rule);
            }
        }
        var chosen=specificSeen?specific:wildcard;int longest=-1;boolean allowed=true;
        for(var rule:chosen) {
            String pattern=rule.path();boolean end=pattern.endsWith("$");if(end) pattern=pattern.substring(0,pattern.length()-1);
            StringBuilder regex=new StringBuilder("^");for(String part:pattern.split("\\*",-1)) {if(regex.length()>1) regex.append(".*");regex.append(Pattern.quote(part));}
            if(end) regex.append('$');
            if(Pattern.compile(regex.toString()).matcher(path).find()) {
                int specificity=pattern.replace("*","").length();
                if(specificity>longest||specificity==longest&&rule.allow()) {longest=specificity;allowed=rule.allow();}
            }
        }
        return allowed;
    }
    private Page parse(CrawlStore.Lease lease,String url,String body,CrossrefTransport.Response response) {
        JsonNode root;
        try {root=json.readTree(body);} catch(RuntimeException e) {throw new CrawlFailure("INVALID_RESPONSE","来源 JSON 无法解析，未推进断点或水位",false);}
        boolean single=!CrawlStore.str(lease.task(),"doi").isEmpty();
        if(root==null||!root.path("status").asText().equals("ok")||!root.path("message").isObject()) throw new CrawlFailure("INVALID_RESPONSE","缺少有效 Crossref 响应信封",false);
        if(!root.path("message-type").asText().equals(single?"work":"work-list")) throw new CrawlFailure("INVALID_RESPONSE","Crossref 响应类型与请求不一致",false);
        var message=root.path("message");var items=new ArrayList<JsonNode>();
        if(single) {
            try {if(!CrawlStore.str(lease.task(),"doi").equals(ImportService.normalizeDoi(message.path("DOI").asText("")))) throw new IllegalArgumentException();}
            catch(RuntimeException invalid) {throw new CrawlFailure("INVALID_RESPONSE","单条响应 DOI 与请求标识不一致",false);}
            items.add(message);
        }
        else {
            if(!message.path("items").isArray()||(!message.path("total-results").isIntegralNumber()||message.path("total-results").asLong()<0)) throw new CrawlFailure("INVALID_RESPONSE","列表缺少 items 或 total-results，不能视为有效空结果",false);
            message.path("items").forEach(items::add);
            if(items.size()>rowsFor(lease)) throw new CrawlFailure("INVALID_RESPONSE","来源返回数量超过请求页大小",false);
        }
        var works=new ArrayList<ImportService.WorkInput>();var exclusions=new ArrayList<Map<String,Object>>();int index=0;
        for(var item:items) {
            try {works.add(map(item));}
            catch(RuntimeException e) {exclusions.add(Map.of("index",index,"doi",item.path("DOI").asText(""),"reason",Objects.toString(e.getMessage(),"INVALID_ITEM"),"checksum",AuthService.hash(item.toString())));}
            index++;
        }
        boolean finished=single||items.size()<rowsFor(lease);String next=single?"":message.path("next-cursor").asText("");
        if(!finished&&next.isBlank()) throw new CrawlFailure("INVALID_RESPONSE","非末页缺少可前进游标，不能报告完成",false);
        return new Page(url,body,response.status(),response.header("ETag"),response.header("Last-Modified"),items.size(),works,exclusions,next,finished);
    }
    @SuppressWarnings("unchecked")
    private ImportService.WorkInput map(JsonNode item) {
        String type=item.path("type").asText("");
        if(!Set.of("journal-article","proceedings-article").contains(type)) throw new IllegalArgumentException("UNSUPPORTED_GENRE:"+type);
        String doi=ImportService.normalizeDoi(item.path("DOI").asText(""));if(doi==null) throw new IllegalArgumentException("MISSING_DOI");
        if(doi.length()>200) throw new IllegalArgumentException("DOI_EXCEEDS_SOURCE_KEY_LIMIT");
        String title=cleanText(firstText(item.path("title")));
        if(title.isBlank()||title.length()>1000) throw new IllegalArgumentException("INVALID_TITLE");
        String normalized=title.toLowerCase(Locale.ROOT).replaceAll("<[^>]+>","").strip();
        if(normalized.matches("^(editorial( board)?|front matter|back matter|table of contents|contents|cover|erratum|corrigendum|correction|retraction)(\\s*[:：].*)?$")) throw new IllegalArgumentException("NON_RESEARCH_FRONT_MATTER");
        var contributors=new ArrayList<ImportService.Contributor>();int invalidOrcids=0;
        for(var author:item.path("author")) {
            if(contributors.size()>=40) break;
            String name=(author.path("given").asText("")+" "+author.path("family").asText("")).strip();
            if(name.isBlank()) name=author.path("name").asText("");if(name.isBlank()) continue;
            var affiliations=new ArrayList<String>();for(var affiliation:author.path("affiliation")) {String text=affiliation.path("name").asText("").strip();if(!text.isBlank()&&affiliations.size()<20) affiliations.add(limit(text,500));}
            String orcid=author.path("ORCID").asText("");
            try {orcid=ProfileService.normalizeOrcid(orcid);} catch(ApiException invalid) {orcid="";invalidOrcids++;}
            contributors.add(new ImportService.Contributor(null,limit(name,100),"AUTHOR",null,orcid,affiliations));
        }
        Integer cited=item.path("is-referenced-by-count").isIntegralNumber()?item.path("is-referenced-by-count").asInt():null;if(cited!=null&&cited<0) cited=null;
        var details=new LinkedHashMap<String,Object>();details.put("sourceType",type);details.put("classificationStatus","UNCLASSIFIED");details.put("parserVersion","crossref-v1");
        details.put("invalidOrcidCount",invalidOrcids);
        details.put("publisher",limit(item.path("publisher").asText(""),300));details.put("authorsTruncated",Math.max(0,item.path("author").size()-contributors.size()));
        String date="";for(String field:List.of("published-print","published-online","issued","published")) {date=publicationDate(item.path(field));if(!date.isBlank()) {details.put("dateSource",field);break;}}
        Long updated=null;try {updated=Instant.parse(item.path("indexed").path("date-time").asText()).toEpochMilli();} catch(RuntimeException ignored) { }
        return new ImportService.WorkInput("PAPER",title,date,doi,null,null,null,
            limit(cleanText(item.path("abstract").asText("")),16000),limit(firstText(item.path("container-title")),300),cited,cited==null?null:"Crossref","UNKNOWN",false,
            doi,"https://doi.org/"+encode(doi),contributors,List.of(),List.of(),details,json.convertValue(item,Map.class),updated);
    }
    private static String cleanText(String value) {
        String plain=value.replaceAll("(?is)<(script|style)\\b[^>]*>.*?</\\1\\s*>"," ").replaceAll("<[^>]+>"," ");
        return java.text.Normalizer.normalize(org.springframework.web.util.HtmlUtils.htmlUnescape(plain),java.text.Normalizer.Form.NFC).replaceAll("\\s+"," ").strip();
    }
    private static String firstText(JsonNode value) {return value.isArray()&&value.size()>0?value.get(0).asText(""):"";}
    private static String limit(String value,int max) {return value.length()>max?value.substring(0,max):value;}
    private static String publicationDate(JsonNode value) {
        try {
            var parts=value.path("date-parts").get(0);if(parts==null||!parts.isArray()||parts.isEmpty()) return "";
            int year=parts.get(0).asInt();if(year<1000||year>2200) return "";
            if(parts.size()==1) return Year.of(year).toString();
            int month=parts.get(1).asInt();if(parts.size()==2) return YearMonth.of(year,month).toString();
            return LocalDate.of(year,month,parts.get(2).asInt()).toString();
        } catch(RuntimeException ignored) {return "";}
    }
}
