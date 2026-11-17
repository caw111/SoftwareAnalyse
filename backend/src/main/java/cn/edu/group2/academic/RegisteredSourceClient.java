package cn.edu.group2.academic;

import java.net.URI;
import java.nio.charset.*;
import java.security.*;
import java.util.*;
import jakarta.validation.Validator;
import org.springframework.stereotype.Service;

@Service
class RegisteredSourceClient {
    private final CrawlStore store;private final RegisteredSourceTransport transport;private final Validator validator;
    RegisteredSourceClient(CrawlStore store,RegisteredSourceTransport transport,Validator validator) {this.store=store;this.transport=transport;this.validator=validator;}

    CrawlPage fetch(CrawlStore.Lease lease) {
        var source=CrawlSourceCatalog.source(lease.sourceId());
        var batch=CrawlSourceCatalog.batch(lease.sourceId(),CrawlStore.str(lease.task(),"batchId"));
        var saved=store.document(lease.id());CrawlDocument document;
        RegisteredHtmlParser.Result parsed;
        if(saved==null) {
            URI uri=URI.create(batch.url());checkRobots(lease,uri);
            var response=request(lease,uri,Map.of("Accept",batch.contentType(),"User-Agent","AcademicPlatform/0.4 (public academic metadata collector)"));
            requireSuccess(response);
            boolean pdf=batch.contentType().equals("application/pdf");
            String type=response.header("Content-Type").toLowerCase(Locale.ROOT);
            if(pdf) {
                if(!(type.contains("pdf")||type.contains("octet-stream"))||response.body().length<5||!new String(response.body(),0,5,StandardCharsets.US_ASCII).equals("%PDF-"))
                    throw new CrawlFailure("INVALID_RESPONSE","登记附件没有返回 PDF，可能是网页外壳或文件已变更",false);
            } else if(!type.contains("text/html")&&!type.contains("application/xhtml+xml")) throw new CrawlFailure("NON_HTML","登记清单未返回 HTML，不能当作空清单",false);
            String raw=pdf?Base64.getEncoder().encodeToString(response.body()):decodeHtml(response);
            parsed=parse(lease.sourceId(),raw,pdf);
            document=new CrawlDocument(batch.url(),raw,batch.contentType(),pdf?"base64":"utf-8",checksum(response.body()),response.status(),response.header("ETag"),response.header("Last-Modified"),parsed.rows().size(),parsed.parserVersion(),Db.now());
        } else {
            document=new CrawlDocument(CrawlStore.str(saved,"requestUrl"),CrawlStore.str(saved,"rawBody"),CrawlStore.str(saved,"contentType"),CrawlStore.str(saved,"bodyEncoding"),CrawlStore.str(saved,"byteChecksum"),
                (int)CrawlStore.num(saved,"httpStatus"),CrawlStore.str(saved,"etag"),CrawlStore.str(saved,"lastModified"),(int)CrawlStore.num(saved,"recordCount"),CrawlStore.str(saved,"parserVersion"),CrawlStore.num(saved,"fetchedAt"));
            if(!batch.url().equals(document.url())) throw new CrawlFailure("DOCUMENT_CHANGED","已登记公告地址发生变化；保留原任务并创建新任务",false);
            parsed=parse(lease.sourceId(),document.raw(),document.bodyEncoding().equals("base64"));
            if(parsed.rows().size()!=document.recordCount()||!parsed.parserVersion().equals(document.parserVersion())) throw new CrawlFailure("DOCUMENT_CHANGED","解析规则改变了冻结快照的行数，请使用新任务复采",false);
        }
        store.assertActive(lease);
        int offset;
        try {offset=CrawlStore.str(lease.task(),"nextCursor").equals("*")?0:Integer.parseInt(CrawlStore.str(lease.task(),"nextCursor"));}
        catch(NumberFormatException e) {throw new CrawlFailure("INVALID_RESPONSE","已提交行断点不合法",false);}
        if(offset<0||offset>=parsed.rows().size()||offset!=CrawlStore.num(lease.task(),"received")) throw new CrawlFailure("INVALID_RESPONSE","公告行断点与已提交计数不一致",false);
        int count=(int)Math.min(CrawlStore.num(lease.task(),"pageSize"),CrawlStore.num(lease.task(),"maxRecords")-offset);
        if(count<1) throw new CrawlFailure("LIMIT_REACHED","记录处理预算已用尽",false);
        int end=Math.min(parsed.rows().size(),offset+count);
        var works=new ArrayList<ImportService.WorkInput>();var exclusions=new ArrayList<Map<String,Object>>();
        for(var row:parsed.rows().subList(offset,end)) {
            if(row.work()==null) {exclusions.add(row.exclusion());continue;}
            try {
                if(!validator.validate(row.work()).isEmpty()) throw ApiException.bad("字段长度或必填约束不符合入库要求");
                ImportService.normalize(row.work(),source.sourceName());works.add(row.work());
            } catch(RuntimeException e) {exclusions.add(Map.of("index",row.index(),"sourceKey",row.work().sourceKey(),"reason",Objects.toString(e.getMessage(),"INVALID_RECORD")));}
        }
        return new CrawlPage(document.url(),document.raw(),document.status(),document.etag(),document.lastModified(),end-offset,works,exclusions,Integer.toString(end),end==parsed.rows().size(),document);
    }
    private RegisteredHtmlParser.Result parse(String sourceId,String raw,boolean pdf) {
        return pdf?new CnipaPatentParser().parse(Base64.getDecoder().decode(raw)):new RegisteredHtmlParser().parse(sourceId,raw);
    }
    static String checksum(byte[] bytes) {
        try {return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));} catch(NoSuchAlgorithmException e) {throw new IllegalStateException(e);}
    }
    private String decodeHtml(RegisteredSourceTransport.Response response) {
        var header=java.util.regex.Pattern.compile("charset\\s*=\\s*[\"']?([^;\\s\"']+)",java.util.regex.Pattern.CASE_INSENSITIVE).matcher(response.header("Content-Type"));
        Charset charset=StandardCharsets.UTF_8;
        if(header.find()) try {charset=Charset.forName(header.group(1));} catch(RuntimeException e) {throw new CrawlFailure("INVALID_RESPONSE","来源声明了不支持的文字编码",false);}
        try {return charset.newDecoder().onMalformedInput(CodingErrorAction.REPORT).decode(java.nio.ByteBuffer.wrap(response.body())).toString();}
        catch(CharacterCodingException e) {throw new CrawlFailure("INVALID_RESPONSE","来源文字编码与响应不一致，未发布乱码题录",false);}
    }
    private RegisteredSourceTransport.Response request(CrawlStore.Lease lease,URI uri,Map<String,String> headers) {
        long wait=store.reserveRequest(lease);
        if(wait>0) try {Thread.sleep(wait);} catch(InterruptedException e) {Thread.currentThread().interrupt();throw new CrawlFailure("INTERRUPTED","等待来源间隔时被中断",true);}
        store.assertActive(lease);return transport.get(uri,headers);
    }
    private void checkRobots(CrawlStore.Lease lease,URI uri) {
        String url=uri.getScheme()+"://"+uri.getAuthority()+"/robots.txt";
        var cached=store.cached(url);String body;
        if(cached!=null&&CrawlStore.num(cached,"expiresAt")>Db.now()) body=CrawlStore.str(cached,"body");
        else {
            var response=request(lease,URI.create(url),Map.of("Accept","text/plain","User-Agent","AcademicPlatform/0.4"));
            if(response.status()==404||response.status()==410) body="";
            else {
                requireSuccess(response);body=new String(response.body(),StandardCharsets.UTF_8);
                if(body.stripLeading().startsWith("<")) throw new CrawlFailure("ROBOTS_DENIED","robots 返回网页，需人工核实来源访问条件",false);
            }
            store.cache(lease,url,new CrossrefTransport.Response(200,response.headers(),body),Db.now()+86_400_000);
        }
        String path=uri.getRawPath()+(uri.getRawQuery()==null?"":"?"+uri.getRawQuery());
        if(!CrossrefClient.robotsAllows(body,path)) throw new CrawlFailure("ROBOTS_DENIED","来源 robots 禁止该公告路径",false);
    }
    static void requireSuccess(RegisteredSourceTransport.Response response) {
        String prefix=new String(response.body(),0,Math.min(response.body().length,65536),StandardCharsets.UTF_8).toLowerCase(Locale.ROOT);
        boolean html=response.header("Content-Type").contains("html")||prefix.stripLeading().startsWith("<");
        if(response.header("cf-mitigated").equalsIgnoreCase("challenge")||html&&(prefix.contains("cf-chl-")||prefix.contains("verify you are human")||prefix.contains("人机验证")||prefix.contains("验证码")||prefix.contains("captcha")))
            throw new CrawlFailure("ACCESS_CHALLENGE","来源返回验证挑战，停止自动采集并保留失败原因",false);
        int status=response.status();if(status==200) return;
        if(status==401||status==403||status==412||status>=300&&status<400) throw new CrawlFailure("ACCESS_RESTRICTED","公告来源要求认证、拒绝访问或重定向，未绕过",false);
        if(status==404||status==410) throw new CrawlFailure("SOURCE_NOT_FOUND","已登记公告不存在或已移除，不能作为空数据成功",false);
        throw new CrawlFailure(status==429?"RATE_LIMITED":"HTTP_"+status,"公告来源返回 HTTP "+status,status==429||status==408||status>=500,CrossrefClient.retryAfter(response.header("Retry-After")),false);
    }
}
