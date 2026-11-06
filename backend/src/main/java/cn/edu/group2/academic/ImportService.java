package cn.edu.group2.academic;

import java.net.URI;
import java.text.Normalizer;
import java.time.*;
import java.time.format.DateTimeParseException;
import java.util.*;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;

@Service
public class ImportService {
    final Db db; final ObjectMapper json;
    public ImportService(Db db,ObjectMapper json) {this.db=db;this.json=json;}
    public record Contributor(@Size(max=80) String scholarId,@NotBlank @Size(max=100) String name,
        @NotBlank @Size(max=40) String role,@Size(max=80) String institutionId) {}
    public record WorkInput(@NotBlank @Size(max=12) String type,@NotBlank @Size(max=1000) String title,
        @Size(max=10) String date,@Size(max=300) String doi,@Size(max=200) String identifier,
        @Size(max=80) String identifierType,@Size(max=200) String authority,
        @Size(max=16000) String abstractText,@Size(max=300) String venue,@PositiveOrZero Integer citationCount,
        @Size(max=200) String citationSource,@Size(max=20) String oaStatus,boolean simulated,
        @NotBlank @Size(max=200) String sourceKey,@NotBlank @Size(max=2000) String sourceUrl,
        @NotNull @Size(max=40) List<@Valid Contributor> contributors,
        @NotNull @Size(max=20) List<@NotBlank @Size(max=80) String> institutionIds,
        @NotNull @Size(max=20) List<@NotBlank @Size(max=100) String> fields,
        @NotNull Map<String,Object> details) {}
    public record Batch(@NotBlank @Size(max=100) String requestKey,@NotBlank @Size(max=200) String sourceName,
        @NotEmpty @Size(max=200) List<@Valid WorkInput> works) {}
    record Normalized(String title,String doi,String key,String dateKind,String precision,Integer year) {}
    static String normalizeDoi(String raw) {
        if(raw==null||raw.isBlank()) return null;
        String doi=raw.strip().toLowerCase(Locale.ROOT).replaceFirst("^(https?://(dx\\.)?doi\\.org/|doi:\\s*)","");
        if(!doi.matches("10\\.\\d{4,9}/\\S+")) throw ApiException.bad("DOI 格式不合法");
        return doi;
    }
    static Normalized normalize(WorkInput w,String source) {
        if(!Set.of("PAPER","PATENT","PROJECT","AWARD").contains(w.type())) throw ApiException.bad("未知成果类型");
        String title=Normalizer.normalize(w.title(),Normalizer.Form.NFC).replaceAll("\\s+"," ").strip();
        if(title.isEmpty()) throw ApiException.bad("题名不能为空");
        Integer year=null;String precision=null;
        if(w.date()!=null&&!w.date().isBlank()) {
            try {
                switch(w.date().length()) {
                    case 4 -> {Year.parse(w.date());precision="year";}
                    case 7 -> {YearMonth.parse(w.date());precision="month";}
                    case 10 -> {LocalDate.parse(w.date());precision="day";}
                    default -> throw ApiException.bad("日期须为 YYYY、YYYY-MM 或 YYYY-MM-DD");
                }
                year=Integer.parseInt(w.date().substring(0,4));
                if(year<1000||year>2200) throw ApiException.bad("年份超出支持范围");
            } catch(DateTimeParseException|NumberFormatException e) {throw ApiException.bad("日期不是有效日期");}
        }
        String kind=switch(w.type()) {case "PAPER"->"publication_date";case "PATENT"->"grant_date";case "PROJECT"->"funding_year";default->"award_year";};
        String doi=w.type().equals("PAPER")?normalizeDoi(w.doi()):null;
        if(!w.type().equals("PAPER")&&w.doi()!=null&&!w.doi().isBlank()) throw ApiException.bad("非论文不能使用 DOI 字段");
        if(w.type().equals("PATENT")&&(!"application_number".equals(w.identifierType())||blank(w.identifier())||blank(w.authority())||blank(Objects.toString(w.details().get("grantEvidence"),"")))) throw ApiException.bad("授权专利需司法辖区、申请号和授权依据；日期可未知");
        String key=source+":"+w.sourceKey();
        if(doi!=null) key="doi:"+doi;
        else if(!blank(w.identifier())&&!blank(w.authority())) {
            if(w.type().equals("PATENT")) key="patent:"+w.authority()+":"+w.identifier();
            if(w.type().equals("PROJECT")&&"approval_number".equals(w.identifierType())) key="project:"+w.authority()+":"+w.identifier();
            if(w.type().equals("AWARD")&&year!=null&&"award_project_number".equals(w.identifierType())) key="award:"+w.authority()+":"+year+":"+w.identifier();
        }
        key=(w.simulated()?"demo:":"real:")+w.type()+":"+key;
        if(key.length()>500) throw ApiException.bad("来源键过长");
        try {URI uri=URI.create(w.sourceUrl());if(!Set.of("http","https").contains(uri.getScheme())||uri.getHost()==null||uri.getUserInfo()!=null) throw ApiException.bad("来源地址必须是 http/https 链接");}
        catch(IllegalArgumentException e) {throw ApiException.bad("来源地址不合法");}
        String oa=Objects.requireNonNullElse(w.oaStatus(),"UNKNOWN");
        if(!Set.of("OPEN","NOT_FOUND","UNKNOWN").contains(oa)) throw ApiException.bad("开放状态不合法");
        if(w.citationCount()!=null&&(w.citationCount()<0||blank(w.citationSource())||!w.type().equals("PAPER"))) throw ApiException.bad("引用数仅用于论文，必须注明来源");
        String role=switch(w.type()) {case "PAPER"->"AUTHOR";case "PATENT"->"INVENTOR";case "PROJECT"->"PI";default->"AWARDEE";};
        if(w.contributors().stream().anyMatch(c->!role.equals(c.role()))) throw ApiException.bad("贡献角色不适用于成果类型");
        return new Normalized(title,doi,key,kind,precision,year);
    }
    static boolean blank(String s) {return s==null||s.isBlank();}
    @Transactional
    public Map<String,Object> ingest(Batch batch,AuthService.Actor actor) {
        actor.admin();
        // Single publication row fences concurrent writers in PostgreSQL and H2, across replicas.
        long revision=((Number)db.one("SELECT revision FROM catalog_release WHERE id=1 FOR UPDATE").get("revision")).longValue();
        String requestHash=AuthService.hash(json.writeValueAsString(batch));
        var prior=db.rows("SELECT * FROM import_task WHERE request_key=?",batch.requestKey());
        if(!prior.isEmpty()) {
            if(!prior.getFirst().get("requestHash").equals(requestHash)) throw ApiException.conflict("幂等键已经用于不同内容");
            return prior.getFirst();
        }
        long next=revision+1;int inserted=0;String taskId=Db.id();long now=Db.now();
        db.update("INSERT INTO import_task VALUES(?,?,?,?,?,?,?,?,?,?,?)",taskId,batch.requestKey(),requestHash,batch.sourceName(),"RUNNING",batch.works().size(),0,0,next,actor.id(),now);
        Set<String> observations=new HashSet<>();
        for(var w:batch.works()) {
            var n=normalize(w,batch.sourceName());
            if(json.writeValueAsString(w.details()).length()>16000) throw ApiException.bad("类型专属字段过长");
            var existing=db.rows("SELECT id FROM work WHERE canonical_key=?",n.key());
            String workId;
            if(existing.isEmpty()) {
                workId=Db.id();inserted++;
                String search=(n.title()+" "+Objects.toString(n.doi(),"")+" "+Objects.toString(w.identifier(),"")+" "+Objects.toString(w.abstractText(),"")).toLowerCase(Locale.ROOT);
                db.update("INSERT INTO work(id,canonical_key,type,title,search_text,date_value,date_kind,date_precision,year,doi,identifier,identifier_type,authority,abstract_text,venue,citation_count,citation_source,oa_status,simulated,revision,created_at,details_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    workId,n.key(),w.type(),n.title(),search,blank(w.date())?null:w.date(),n.dateKind(),n.precision(),n.year(),n.doi(),w.identifier(),w.identifierType(),w.authority(),Objects.toString(w.abstractText(),""),Objects.toString(w.venue(),""),w.citationCount(),w.citationSource(),Objects.requireNonNullElse(w.oaStatus(),"UNKNOWN"),w.simulated(),next,now,json.writeValueAsString(w.details()));
                int position=0;Set<String> institutions=new HashSet<>(w.institutionIds());
                for(var c:w.contributors()) {
                    if(!blank(c.scholarId())&&db.count("SELECT COUNT(*) FROM scholar WHERE id=? AND simulated=?",c.scholarId(),w.simulated())!=1) throw ApiException.bad("人物标识不存在或模拟标志不一致");
                    db.update("INSERT INTO contributor VALUES(?,?,?,?,?,?)",workId,++position,blank(c.scholarId())?null:c.scholarId(),c.name(),c.role(),blank(c.institutionId())?null:c.institutionId());
                    if(!blank(c.institutionId())) institutions.add(c.institutionId());
                }
                for(String institution:institutions) db.update("INSERT INTO work_institution VALUES(?,?)",workId,institution);
                for(String field:new HashSet<>(w.fields())) db.update("INSERT INTO work_field VALUES(?,?)",workId,field);
            } else workId=existing.getFirst().get("id").toString();
            var priorSource=db.rows("SELECT DISTINCT work_id FROM source_record WHERE source_name=? AND source_key=?",batch.sourceName(),w.sourceKey());
            if(priorSource.stream().anyMatch(s->!s.get("workId").equals(workId))) throw ApiException.conflict("来源键已指向另一成果，需人工复核");
            String raw=json.writeValueAsString(w),checksum=AuthService.hash(raw);
            var sources=db.rows("SELECT id FROM source_record WHERE source_name=? AND source_key=? AND checksum=?",batch.sourceName(),w.sourceKey(),checksum);
            String sourceId;
            if(sources.isEmpty()) {
                sourceId=Db.id();
                db.update("INSERT INTO source_record VALUES(?,?,?,?,?,?,?,?,?)",sourceId,workId,batch.sourceName(),w.sourceKey(),w.sourceUrl(),checksum,raw,now,next);
            } else sourceId=sources.getFirst().get("id").toString();
            if(observations.add(sourceId)) db.update("INSERT INTO source_observation VALUES(?,?)",taskId,sourceId);
        }
        db.update("UPDATE import_task SET state='SUCCESS',inserted=?,duplicates=? WHERE id=?",inserted,batch.works().size()-inserted,taskId);
        db.update("UPDATE catalog_release SET revision=? WHERE id=1",next);
        audit(actor.id(),taskId,"IMPORT_PUBLISHED","RUNNING","SUCCESS","原子发布版本 "+next);
        return db.one("SELECT * FROM import_task WHERE id=?",taskId);
    }
    void audit(String actor,String object,String action,String before,String after,String reason) {
        db.update("INSERT INTO audit_event(id,actor_id,object_id,action,before_state,after_state,reason,created_at) VALUES(?,?,?,?,?,?,?,?)",Db.id(),actor,object,action,before,after,reason,Db.now());
    }
}
