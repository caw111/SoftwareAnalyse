package cn.edu.group2.academic;

import java.time.*;
import java.util.*;
import jakarta.validation.constraints.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;

@Service
public class CrawlStore {
    static final long LEASE_MS=180_000;
    private final Db db;private final ImportService imports;private final ObjectMapper json;
    CrawlStore(Db db,ImportService imports,ObjectMapper json) {this.db=db;this.imports=imports;this.json=json;}
    public record Create(@NotBlank String sourceId,@Size(max=9) String issn,@Size(max=200) String query,
        @Size(max=300) String doi,String fromDate,String untilDate,@Min(1) @Max(100) int pageSize,
        @Min(1) @Max(100) int maxPages,String parentTaskId,String mode,@Min(1) @Max(10000) Integer maxRecords,
        @Min(1000) @Max(2200) Integer fromPublicationYear,@Min(1000) @Max(2200) Integer toPublicationYear) {}
    public record Action(@Min(0) int version,@NotBlank String action) {}
    public record Settings(@Min(0) int version,boolean enabled,@Min(1000) @Max(60000) int minIntervalMs,
        boolean scheduleEnabled,@Min(60) @Max(10080) int scheduleEveryMinutes,@NotNull @Size(max=9) String scheduleIssn,
        @Min(1) @Max(100) int schedulePageSize,@Min(1) @Max(100) int scheduleMaxPages,
        @Min(1) @Max(31) int scheduleLookbackDays) {}
    record Lease(String id,String sourceId,String token,int attempt,Map<String,Object> task) {}
    static String str(Map<String,Object> row,String key) {return Objects.toString(row.get(key),"");}
    static long num(Map<String,Object> row,String key) {return row.get(key)==null?0:((Number)row.get(key)).longValue();}
    static boolean flag(Map<String,Object> row,String key) {return Boolean.TRUE.equals(row.get(key));}
    static String blank(String value) {return value==null?"":value.strip();}
    private static String scopeKey(String issn,String query,String doi,Integer fromYear,Integer toYear) {
        return AuthService.hash(issn+"\n"+query+"\n"+doi+"\n"+Objects.toString(fromYear,"")+"\n"+Objects.toString(toYear,""));
    }
    private Map<String,Object> sourceLock(String source) {return db.one("SELECT * FROM crawl_source WHERE id=? FOR UPDATE",source);}
    private Map<String,Object> taskLock(String id) {return db.one("SELECT * FROM crawl_task WHERE id=? FOR UPDATE",id);}
    private void event(Map<String,Object> task,String action,String after,String message) {
        db.update("INSERT INTO crawl_task_log(task_id,attempt,action,before_state,after_state,message,created_at) VALUES(?,?,?,?,?,?,?)",
            task.get("id"),task.get("attempt"),action,task.get("state"),after,message,Db.now());
    }
    private void transition(Map<String,Object> task,String state,String action,String message) {
        event(task,action,state,message);
        db.update("UPDATE crawl_task SET state=?,version=version+1,updated_at=? WHERE id=?",state,Db.now(),task.get("id"));
        task.put("state",state);
    }
    @Transactional
    public Object create(Create input,AuthService.Actor actor) {actor.admin();return createLocked(input,actor,sourceLock(input.sourceId()),false);}
    private Object createLocked(Create input,AuthService.Actor actor,Map<String,Object> source,boolean runnable) {
        if(!flag(source,"enabled")) throw ApiException.conflict("来源已停用");
        String issn=blank(input.issn()).toUpperCase(Locale.ROOT),query=blank(input.query()),doi=blank(input.doi());
        if(!issn.isEmpty()&&!issn.matches("[0-9]{4}-[0-9]{3}[0-9X]")) throw ApiException.bad("ISSN 格式不正确");
        if(!doi.isEmpty()) {doi=ImportService.normalizeDoi(doi);if(!issn.isEmpty()||!query.isEmpty()) throw ApiException.bad("DOI 定向采集不能同时设置 ISSN 或关键词");}
        if(doi.isEmpty()&&issn.isEmpty()&&query.isEmpty()) throw ApiException.bad("请指定 ISSN、关键词或单条 DOI，避免无范围采集");
        if(input.pageSize()<1||input.pageSize()>100||input.maxPages()<1||input.maxPages()>100) throw ApiException.bad("每页条数和页预算应为 1–100");
        String mode=blank(input.mode()).isEmpty()?"BOUNDED":input.mode();
        int maxRecords=input.maxRecords()==null?input.pageSize()*input.maxPages():input.maxRecords();
        if(!Set.of("BOUNDED","INCREMENTAL").contains(mode)||maxRecords<1||maxRecords>10000) throw ApiException.bad("采集模式或原始记录预算不合法");
        if(input.fromPublicationYear()!=null&&input.toPublicationYear()!=null&&input.fromPublicationYear()>input.toPublicationYear()) throw ApiException.bad("出版起始年不能晚于终止年");
        if(!doi.isEmpty()&&(input.fromPublicationYear()!=null||input.toPublicationYear()!=null)) throw ApiException.bad("单条 DOI 模式不使用出版年筛选");
        LocalDate from,to;
        try {
            from=LocalDate.parse(doi.isEmpty()?input.fromDate():LocalDate.now(ZoneOffset.UTC).toString());
            to=LocalDate.parse(doi.isEmpty()?input.untilDate():from.toString());
        } catch(RuntimeException e) {throw ApiException.bad("固定窗口日期须为 YYYY-MM-DD");}
        if(from.isAfter(to)||from.plusDays(30).isBefore(to)||to.isAfter(LocalDate.now(ZoneOffset.UTC))) throw ApiException.bad("采集窗口须为过去或当前日期内的 1–31 天");
        String parent=blank(input.parentTaskId());
        if(!parent.isEmpty()) {
            var old=db.one("SELECT source_id,state FROM crawl_task WHERE id=?",parent);
            if(!old.get("sourceId").equals(input.sourceId())||!Set.of("SUCCESS","STOPPED","FAILED").contains(old.get("state"))) throw ApiException.bad("前序任务须为同来源的已结束任务");
        }
        String scope=scopeKey(issn,query,doi,input.fromPublicationYear(),input.toPublicationYear()),id=Db.id();long now=Db.now();
        db.update("""
            INSERT INTO crawl_task(id,source_id,created_by,parent_task_id,scope_key,issn,query_text,doi,from_date,until_date,page_size,max_pages,mode,max_records,from_publication_year,to_publication_year,state,runnable,next_cursor,source_config_version,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'PENDING',?,'*',?,?,?)
            """,id,input.sourceId(),actor.id(),parent.isEmpty()?null:parent,scope,issn,query,doi,from.toString(),to.toString(),input.pageSize(),input.maxPages(),mode,maxRecords,input.fromPublicationYear(),input.toPublicationYear(),runnable,source.get("configVersion"),now,now);
        var result=db.one("SELECT * FROM crawl_task WHERE id=?",id);event(result,"CREATE","PENDING",runnable?"定时计划创建有界任务":"管理员创建任务，等待明确启动");
        return result;
    }
    public List<Map<String,Object>> sources() {return db.rows("SELECT id,name,enabled,config_version,min_interval_ms,next_request_at,schedule_enabled,schedule_every_minutes,schedule_issn,schedule_page_size,schedule_max_pages,schedule_lookback_days,next_schedule_at FROM crawl_source ORDER BY id");}
    public Object checkpoints() {return db.rows("SELECT * FROM crawl_checkpoint ORDER BY source_id,scope_key");}
    public Object list(int page,int size) {
        if(page<0||size<1||size>100) throw ApiException.bad("页码或每页数量不合法");
        return Map.of("items",db.rows("SELECT * FROM crawl_task ORDER BY created_at DESC,id LIMIT ? OFFSET ?",size,(long)page*size),"total",db.count("SELECT COUNT(*) FROM crawl_task"),"page",page,"size",size);
    }
    public Map<String,Object> detail(String id) {
        var task=db.one("SELECT * FROM crawl_task WHERE id=?",id);
        task.put("logs",db.rows("SELECT * FROM crawl_task_log WHERE task_id=? ORDER BY sequence_no",id));
        task.put("pages",db.rows("SELECT task_id,page_no,attempt,http_status,response_checksum,exclusions_json,import_task_id,revision,received,accepted,excluded,created_at FROM crawl_page WHERE task_id=? ORDER BY page_no",id));return task;
    }
    public Object rawPage(String id,int page) {return db.one("SELECT * FROM crawl_page WHERE task_id=? AND page_no=?",id,page);}
    @Transactional
    public Object settings(String id,Settings input,AuthService.Actor actor) {
        actor.admin();var source=sourceLock(id);
        if(num(source,"configVersion")!=input.version()) throw ApiException.conflict("来源配置已变化，请刷新");
        if(input.scheduleEnabled()&&(!input.enabled()||!input.scheduleIssn().matches("[0-9]{4}-[0-9]{3}[0-9Xx]"))) throw ApiException.bad("启用定时采集前须启用来源并填写有效 ISSN");
        db.update("""
            UPDATE crawl_source SET enabled=?,config_version=config_version+1,min_interval_ms=?,schedule_enabled=?,schedule_every_minutes=?,schedule_issn=?,schedule_page_size=?,schedule_max_pages=?,schedule_lookback_days=?,next_schedule_at=?,schedule_user_id=? WHERE id=?
            """,input.enabled(),input.minIntervalMs(),input.scheduleEnabled(),input.scheduleEveryMinutes(),input.scheduleIssn().toUpperCase(Locale.ROOT),input.schedulePageSize(),input.scheduleMaxPages(),input.scheduleLookbackDays(),Db.now()+input.scheduleEveryMinutes()*60_000L,actor.id(),id);
        if(!input.enabled()) db.update("UPDATE crawl_task SET stop_requested=TRUE,version=version+1 WHERE source_id=? AND state IN ('PENDING','RUNNING','RETRYING')",id);
        imports.audit(actor.id(),id,"CRAWL_SOURCE_CONFIG",null,null,"来源配置版本 "+(input.version()+1));return sources().stream().filter(s->s.get("id").equals(id)).findFirst().orElseThrow();
    }
    @Transactional
    public Object action(String id,Action input,AuthService.Actor actor) {
        actor.admin();var task=taskLock(id);String state=str(task,"state");
        if(num(task,"version")!=input.version()) throw ApiException.conflict("采集任务已变化，请刷新");
        switch(input.action()) {
            case "START" -> {
                if(!state.equals("PENDING")||flag(task,"stopRequested")) throw ApiException.conflict("只能启动未取消的等待任务");
                if(db.count("SELECT COUNT(*) FROM crawl_source WHERE id=? AND enabled=TRUE",task.get("sourceId"))!=1) throw ApiException.conflict("来源已停用");
                db.update("UPDATE crawl_task SET runnable=TRUE,version=version+1,updated_at=? WHERE id=?",Db.now(),id);event(task,"START","PENDING","管理员启动任务");
            }
            case "STOP" -> {
                if(Set.of("SUCCESS","STOPPED").contains(state)) throw ApiException.conflict("终态任务不可变更，请创建关联的新任务");
                db.update("UPDATE crawl_task SET stop_requested=TRUE,version=version+1,updated_at=? WHERE id=?",Db.now(),id);
                if(state.equals("RUNNING")) event(task,"STOP_REQUESTED",state,"等待执行器在安全边界确认停止");
                else {transition(task,"STOPPED","ADMIN_CANCELLED","管理员取消，保留已提交页面");db.update("UPDATE crawl_task SET error_code='ADMIN_CANCELLED',completed_at=? WHERE id=?",Db.now(),id);}
            }
            case "RETRY" -> {
                if(!state.equals("FAILED")||flag(task,"stopRequested")) throw ApiException.conflict("只能重试未放弃的失败任务");
                if(num(task,"retryCount")>=3||Set.of("PAGE_LIMIT","LIMIT_REACHED","ACCESS_RESTRICTED","ROBOTS_DENIED","NON_JSON","INVALID_RESPONSE","RESPONSE_TOO_LARGE").contains(str(task,"errorCode"))) throw ApiException.conflict("预算耗尽或需要修正访问/范围条件，请创建关联的新任务");
                transition(task,"RETRYING","MANUAL_RETRY","管理员请求从已提交断点重试");
                db.update("UPDATE crawl_task SET retry_count=retry_count+1,runnable=TRUE,next_run_at=? WHERE id=?",Db.now(),id);
            }
            default -> throw ApiException.bad("不支持的采集操作");
        }
        return detail(id);
    }
    @Transactional
    public void scheduleDue() {
        long now=Db.now();
        for(var candidate:db.rows("SELECT id FROM crawl_source WHERE enabled=TRUE AND schedule_enabled=TRUE AND next_schedule_at<=?",now)) {
            var source=sourceLock(str(candidate,"id"));
            if(!flag(source,"enabled")||!flag(source,"scheduleEnabled")||num(source,"nextScheduleAt")>now) continue;
            var admins=db.rows("SELECT * FROM app_user WHERE id=? AND role='ADMIN'",source.get("scheduleUserId"));
            if(admins.isEmpty()) {db.update("UPDATE crawl_source SET schedule_enabled=FALSE WHERE id=?",source.get("id"));continue;}
            db.update("UPDATE crawl_source SET next_schedule_at=? WHERE id=?",now+num(source,"scheduleEveryMinutes")*60_000,source.get("id"));
            if(db.count("SELECT COUNT(*) FROM crawl_task WHERE source_id=? AND state IN ('PENDING','RUNNING','RETRYING')",source.get("id"))>0) continue;
            String issn=str(source,"scheduleIssn"),scope=scopeKey(issn,"","",null,null);
            LocalDate end=LocalDate.now(ZoneOffset.UTC).minusDays(1),start=end.minusDays(num(source,"scheduleLookbackDays")-1);
            var checkpoint=db.rows("SELECT successful_until FROM crawl_checkpoint WHERE source_id=? AND scope_key=?",source.get("id"),scope);
            if(!checkpoint.isEmpty()) start=LocalDate.parse(str(checkpoint.getFirst(),"successfulUntil"));
            if(start.isAfter(end)) continue;
            if(start.plusDays(30).isBefore(end)) end=start.plusDays(30);
            var admin=admins.getFirst();createLocked(new Create(str(source,"id"),issn,"","",start.toString(),end.toString(),(int)num(source,"schedulePageSize"),(int)num(source,"scheduleMaxPages"),null,"INCREMENTAL",(int)(num(source,"schedulePageSize")*num(source,"scheduleMaxPages")),null,null),new AuthService.Actor(str(admin,"id"),str(admin,"username"),str(admin,"displayName"),"ADMIN"),source,true);
        }
    }
    @Transactional
    public Lease claimNext() {
        long now=Db.now();
        for(var candidate:db.rows("SELECT id,source_id FROM crawl_task WHERE (state IN ('PENDING','RETRYING') AND (runnable=TRUE OR stop_requested=TRUE) AND next_run_at<=?) OR (state='RUNNING' AND lease_until<=?) ORDER BY created_at,id LIMIT 20",now,now)) {
            var source=sourceLock(str(candidate,"sourceId"));var task=taskLock(str(candidate,"id"));String state=str(task,"state");
            if(Set.of("SUCCESS","FAILED","STOPPED").contains(state)) continue;
            if(state.equals("RUNNING")&&num(task,"leaseUntil")>now) continue;
            if(flag(task,"stopRequested")||!flag(source,"enabled")) {stop(task,source,"ADMIN_CANCELLED");continue;}
            if(state.equals("RUNNING")) {failLocked(task,source,new CrawlFailure("LEASE_EXPIRED","执行租约过期，旧执行器已失效",true));continue;}
            if(!flag(task,"runnable")||num(task,"nextRunAt")>now||num(source,"nextRequestAt")>now||num(source,"leaseUntil")>now) continue;
            if(num(task,"committedPages")>=num(task,"maxPages")) {failLocked(task,source,new CrawlFailure("PAGE_LIMIT","页预算已用尽，固定窗口尚未完整扫描；请创建更大预算的新任务",false));continue;}
            if(db.count("SELECT COUNT(*) FROM app_user WHERE id=? AND role='ADMIN'",task.get("createdBy"))!=1) {failLocked(task,source,new CrawlFailure("ADMIN_REVOKED","创建者已无采集管理权限",false));continue;}
            String token=Db.id();int attempt=(int)num(task,"attempt")+1;
            db.update("UPDATE crawl_source SET lease_token=?,lease_until=? WHERE id=?",token,now+LEASE_MS,source.get("id"));
            db.update("UPDATE crawl_task SET attempt=?,lease_token=?,lease_until=?,source_config_version=? WHERE id=?",attempt,token,now+LEASE_MS,source.get("configVersion"),task.get("id"));
            task.put("attempt",attempt);transition(task,"RUNNING","LEASE_ACQUIRED","执行尝试 "+attempt+" 获得来源租约");
            return new Lease(str(task,"id"),str(source,"id"),token,attempt,db.one("SELECT * FROM crawl_task WHERE id=?",task.get("id")));
        }
        return null;
    }
    private boolean valid(Lease lease,Map<String,Object> source,Map<String,Object> task) {
        return str(task,"state").equals("RUNNING")&&num(task,"attempt")==lease.attempt()&&lease.token().equals(task.get("leaseToken"))
            &&lease.token().equals(source.get("leaseToken"))&&num(task,"leaseUntil")>Db.now()&&num(source,"leaseUntil")>Db.now();
    }
    @Transactional
    public long reserveRequest(Lease lease) {
        var source=sourceLock(lease.sourceId());var task=taskLock(lease.id());
        if(!valid(lease,source,task)) throw new CrawlFailure("STALE_ATTEMPT","执行尝试已失效",false);
        if(flag(task,"stopRequested")||!flag(source,"enabled")) throw new CrawlFailure("STOP_REQUESTED","采集已请求停止",false);
        long start=Math.max(Db.now(),num(source,"nextRequestAt"));
        if(start+25_000>=num(task,"leaseUntil")) throw new CrawlFailure("SOURCE_WAIT","来源要求等待后再请求",true,start,false);
        db.update("UPDATE crawl_source SET next_request_at=? WHERE id=?",start+num(source,"minIntervalMs"),source.get("id"));return Math.max(0,start-Db.now());
    }
    @Transactional
    public void assertActive(Lease lease) {
        var source=sourceLock(lease.sourceId());var task=taskLock(lease.id());
        if(!valid(lease,source,task)) throw new CrawlFailure("STALE_ATTEMPT","执行尝试已失效",false);
        if(flag(task,"stopRequested")||!flag(source,"enabled")) throw new CrawlFailure("STOP_REQUESTED","采集已请求停止",false);
    }
    public Map<String,Object> cached(String url) {var rows=db.rows("SELECT * FROM crawl_http_cache WHERE url_hash=?",AuthService.hash(url));return rows.isEmpty()?null:rows.getFirst();}
    @Transactional
    public void cache(Lease lease,String url,CrossrefTransport.Response response,long expires) {
        var source=sourceLock(lease.sourceId());var task=taskLock(lease.id());if(!valid(lease,source,task)||flag(task,"stopRequested")) return;
        String key=AuthService.hash(url);db.update("DELETE FROM crawl_http_cache WHERE url_hash=?",key);
        String control=response.header("Cache-Control").toLowerCase(Locale.ROOT);
        if(control.contains("no-store")) return;
        String etag=response.header("ETag"),modified=response.header("Last-Modified");
        if(etag.length()>1000) etag="";if(modified.length()>200) modified="";
        if(!url.endsWith("/robots.txt")&&etag.isEmpty()&&modified.isEmpty()) return;
        if(control.contains("no-cache")) expires=0;
        var age=java.util.regex.Pattern.compile("(?:^|,)\\s*max-age\\s*=\\s*\"?([0-9]+)").matcher(control);
        if(age.find()) {
            try {expires=Math.min(expires,Db.now()+Math.min(86_400,Long.parseLong(age.group(1)))*1000);}
            catch(NumberFormatException ignored) {expires=0;}
        }
        if(db.count("SELECT COUNT(*) FROM crawl_http_cache")>=64) db.update("DELETE FROM crawl_http_cache WHERE url_hash IN (SELECT url_hash FROM crawl_http_cache ORDER BY stored_at LIMIT 1)");
        db.update("INSERT INTO crawl_http_cache VALUES(?,?,?,?,?,?,?)",key,url,response.body(),etag,modified,expires,Db.now());
    }
    @Transactional
    public void advertisedRate(Lease lease,long interval) {
        var source=sourceLock(lease.sourceId());var task=taskLock(lease.id());if(!valid(lease,source,task)) return;
        db.update("UPDATE crawl_source SET next_request_at=? WHERE id=?",Math.max(num(source,"nextRequestAt"),Db.now()+Math.max(0,interval)),source.get("id"));
    }
    @Transactional
    public boolean commit(Lease lease,CrossrefClient.Page page) {
        var source=sourceLock(lease.sourceId());var task=taskLock(lease.id());
        if(!valid(lease,source,task)) return false;
        if(flag(task,"stopRequested")||!flag(source,"enabled")) {stop(task,source,"ADMIN_CANCELLED");return false;}
        var user=db.one("SELECT * FROM app_user WHERE id=?",task.get("createdBy"));
        if(!str(user,"role").equals("ADMIN")) {failLocked(task,source,new CrawlFailure("ADMIN_REVOKED","创建者已无采集管理权限",false));return false;}
        int number=(int)num(task,"committedPages")+1;Map<String,Object> imported=Map.of();
        if(!page.works().isEmpty()) imported=imports.ingestTrustedCrossref(new ImportService.Batch("crawl:"+lease.id()+":"+number,"Crossref",page.works()),new AuthService.Actor(str(user,"id"),str(user,"username"),str(user,"displayName"),"ADMIN"));
        db.update("""
            INSERT INTO crawl_page(task_id,page_no,attempt,request_url,raw_json,response_checksum,http_status,etag,last_modified,exclusions_json,import_task_id,revision,received,accepted,excluded,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,lease.id(),number,lease.attempt(),page.url(),page.raw(),AuthService.hash(page.raw()),page.status(),page.etag().length()<=1000?page.etag():null,page.lastModified().length()<=200?page.lastModified():null,json.writeValueAsString(page.exclusions()),imported.get("id"),imported.get("revision"),page.received(),page.works().size(),page.exclusions().size(),Db.now());
        db.update("""
            UPDATE crawl_task SET next_cursor=?,committed_pages=committed_pages+1,received=received+?,inserted=inserted+?,updated=updated+?,unchanged=unchanged+?,excluded=excluded+?,conflicts=conflicts+?,publication_revision=COALESCE(?,publication_revision),error_code='',error_message='' WHERE id=?
            """,page.nextCursor(),page.received(),num(imported,"inserted"),num(imported,"updated"),num(imported,"unchanged"),page.exclusions().size(),num(imported,"conflicts"),imported.get("revision"),lease.id());
        boolean limited=num(task,"received")+page.received()>=num(task,"maxRecords")||number>=num(task,"maxPages");
        if(page.finished()||limited&&str(task,"mode").equals("BOUNDED")) {
            String completion=page.finished()?"SOURCE_EXHAUSTED":"LIMIT_REACHED";
            transition(task,"SUCCESS",completion,page.finished()?"固定范围已耗尽，页面及处理结果已可靠提交":"已达到管理员设置的限量预算，限量采集完成；不推进同步水位");
            if(str(task,"mode").equals("INCREMENTAL")&&str(task,"doi").isEmpty()) advanceCheckpoint(task);
            db.update("UPDATE crawl_task SET completed_at=?,completion_reason=? WHERE id=?",Db.now(),completion,lease.id());
        } else if(limited) {
            failLocked(task,source,new CrawlFailure("LIMIT_REACHED","预算已用尽，增量固定窗口尚未完整扫描；保留已提交数据但不推进成功水位",false));return true;
        } else transition(task,"PENDING","PAGE_COMMITTED","已提交第 "+number+" 页，等待下一页");
        release(task,source);return true;
    }
    private void advanceCheckpoint(Map<String,Object> task) {
        var previous=db.rows("SELECT * FROM crawl_checkpoint WHERE source_id=? AND scope_key=? FOR UPDATE",task.get("sourceId"),task.get("scopeKey"));
        if(previous.isEmpty()) db.update("INSERT INTO crawl_checkpoint VALUES(?,?,?,?,?,?,?)",task.get("sourceId"),task.get("scopeKey"),task.get("issn"),task.get("queryText"),task.get("untilDate"),task.get("id"),Db.now());
        else if(str(task,"fromDate").compareTo(str(previous.getFirst(),"successfulUntil"))<=0&&str(task,"untilDate").compareTo(str(previous.getFirst(),"successfulUntil"))>0)
            db.update("UPDATE crawl_checkpoint SET successful_until=?,task_id=?,updated_at=? WHERE source_id=? AND scope_key=?",task.get("untilDate"),task.get("id"),Db.now(),task.get("sourceId"),task.get("scopeKey"));
    }
    @Transactional
    public void fail(Lease lease,CrawlFailure failure) {
        var source=sourceLock(lease.sourceId());var task=taskLock(lease.id());if(!valid(lease,source,task)) return;
        if(flag(task,"stopRequested")||!flag(source,"enabled")||failure.code.equals("STOP_REQUESTED")) {stop(task,source,"ADMIN_CANCELLED");return;}
        failLocked(task,source,failure);
    }
    private void failLocked(Map<String,Object> task,Map<String,Object> source,CrawlFailure failure) {
        transition(task,"FAILED",failure.code,failure.getMessage());
        db.update("UPDATE crawl_task SET error_code=?,error_message=? WHERE id=?",failure.code,failure.getMessage(),task.get("id"));
        if(failure.retryAt>0) db.update("UPDATE crawl_source SET next_request_at=? WHERE id=?",Math.max(failure.retryAt,num(source,"nextRequestAt")),source.get("id"));
        if(failure.retryable&&num(task,"retryCount")<3&&!flag(task,"stopRequested")) {
            long backoff=Math.min(60_000,2000L<<num(task,"retryCount"))+java.util.concurrent.ThreadLocalRandom.current().nextLong(500);
            transition(task,"RETRYING","RETRY_SCHEDULED","有限退避后重试；分页断点与成功水位保持独立");
            db.update("UPDATE crawl_task SET retry_count=retry_count+1,next_run_at=?,next_cursor=CASE WHEN ? THEN '*' ELSE next_cursor END WHERE id=?",Math.max(Db.now()+backoff,failure.retryAt),failure.resetCursor,task.get("id"));
        } else if(failure.retryable) {event(task,"RETRY_EXHAUSTED","FAILED","重试预算耗尽，保留失败终态");db.update("UPDATE crawl_task SET error_code='RETRY_EXHAUSTED' WHERE id=?",task.get("id"));}
        release(task,source);
    }
    private void stop(Map<String,Object> task,Map<String,Object> source,String reason) {
        transition(task,"STOPPED",reason,"执行器已在安全边界停止，已提交数据保留，成功水位不变");
        db.update("UPDATE crawl_task SET completed_at=?,error_code=? WHERE id=?",Db.now(),reason,task.get("id"));release(task,source);
    }
    private void release(Map<String,Object> task,Map<String,Object> source) {
        db.update("UPDATE crawl_source SET lease_token=NULL,lease_until=NULL WHERE id=? AND lease_token=?",source.get("id"),task.get("leaseToken"));
        db.update("UPDATE crawl_task SET lease_token=NULL,lease_until=NULL WHERE id=?",task.get("id"));
    }
}
