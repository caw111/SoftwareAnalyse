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
    final CatalogRevisionStore snapshots; final SearchIndexService searchIndex;
    public ImportService(Db db,ObjectMapper json,CatalogRevisionStore snapshots,SearchIndexService searchIndex) {
        this.db=db;this.json=json;this.snapshots=snapshots;this.searchIndex=searchIndex;
    }
    public record Contributor(@Size(max=80) String scholarId,@NotBlank @Size(max=100) String name,
        @NotBlank @Size(max=40) String role,@Size(max=80) String institutionId,
        @Size(max=80) String orcid,@Size(max=20) List<@NotBlank @Size(max=2000) String> rawAffiliations) {
        public Contributor(String scholarId,String name,String role,String institutionId) {this(scholarId,name,role,institutionId,null,List.of());}
    }
    public record WorkInput(@NotBlank @Size(max=12) String type,@NotBlank @Size(max=1000) String title,
        @Size(max=10) String date,@Size(max=300) String doi,@Size(max=200) String identifier,
        @Size(max=80) String identifierType,@Size(max=200) String authority,
        @Size(max=16000) String abstractText,@Size(max=300) String venue,@PositiveOrZero Integer citationCount,
        @Size(max=200) String citationSource,@Size(max=20) String oaStatus,boolean simulated,
        @NotBlank @Size(max=200) String sourceKey,@NotBlank @Size(max=2000) String sourceUrl,
        @NotNull @Size(max=40) List<@Valid Contributor> contributors,
        @NotNull @Size(max=20) List<@NotBlank @Size(max=80) String> institutionIds,
        @NotNull @Size(max=20) List<@NotBlank @Size(max=100) String> fields,
        @NotNull Map<String,Object> details,Map<String,Object> rawPayload,@PositiveOrZero Long sourceUpdatedAt) {
        public WorkInput(String type,String title,String date,String doi,String identifier,String identifierType,String authority,
            String abstractText,String venue,Integer citationCount,String citationSource,String oaStatus,boolean simulated,
            String sourceKey,String sourceUrl,List<Contributor> contributors,List<String> institutionIds,List<String> fields,Map<String,Object> details) {
            this(type,title,date,doi,identifier,identifierType,authority,abstractText,venue,citationCount,citationSource,oaStatus,
                simulated,sourceKey,sourceUrl,contributors,institutionIds,fields,details,null,null);
        }
        public WorkInput(String type,String title,String date,String doi,String identifier,String identifierType,String authority,
            String abstractText,String venue,Integer citationCount,String citationSource,String oaStatus,boolean simulated,
            String sourceKey,String sourceUrl,List<Contributor> contributors,List<String> institutionIds,List<String> fields,
            Map<String,Object> details,Map<String,Object> rawPayload) {
            this(type,title,date,doi,identifier,identifierType,authority,abstractText,venue,citationCount,citationSource,oaStatus,
                simulated,sourceKey,sourceUrl,contributors,institutionIds,fields,details,rawPayload,null);
        }
    }
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
    public Map<String,Object> ingest(Batch batch,AuthService.Actor actor) {return ingestInternal(batch,actor,false);}
    /** Server-side adapter entry only; arbitrary admin JSON never implies a trusted ORCID assertion. */
    @Transactional
    public Map<String,Object> ingestTrustedCrossref(Batch batch,AuthService.Actor actor) {
        if(!"Crossref".equals(batch.sourceName())) throw ApiException.bad("可信来源入口仅接收 Crossref 适配记录");
        return ingestInternal(batch,actor,true);
    }
    private Map<String,Object> ingestInternal(Batch batch,AuthService.Actor actor,boolean trustedCrossref) {
        actor.admin();
        if(batch.works()==null||batch.works().isEmpty()||batch.works().size()>200) throw ApiException.bad("导入批次须有 1–200 条记录");
        // Bounded writes serialize across replicas. No network calls occur while this fence is held.
        long revision=((Number)db.one("SELECT revision FROM catalog_release WHERE id=1 FOR UPDATE").get("revision")).longValue();
        String requestHash=AuthService.hash(json.writeValueAsString(batch));
        var prior=db.rows("SELECT * FROM import_task WHERE request_key=?",batch.requestKey());
        if(!prior.isEmpty()) {
            if(!prior.getFirst().get("requestHash").equals(requestHash)) throw ApiException.conflict("幂等键已经用于不同内容");
            return prior.getFirst();
        }
        long next=revision+1,now=Db.now();String taskId=Db.id();
        int inserted=0,updated=0,unchanged=0,conflicts=0;
        db.update("""
            INSERT INTO import_task(id,request_key,request_hash,source_name,state,received,inserted,duplicates,revision,created_by,created_at)
            VALUES(?,?,?,?,'RUNNING',?,0,0,?,?,?)
            """,taskId,batch.requestKey(),requestHash,batch.sourceName(),batch.works().size(),next,actor.id(),now);
        Set<String> observations=new HashSet<>(),changed=new LinkedHashSet<>();boolean publicChanged=false;
        for(var w:batch.works()) {
            var n=normalize(w,batch.sourceName());
            if(json.writeValueAsString(w.details()).length()>16000) throw ApiException.bad("类型专属字段过长");
            String normalized=json.writeValueAsString(new WorkInput(w.type(),w.title(),w.date(),w.doi(),w.identifier(),w.identifierType(),
                w.authority(),w.abstractText(),w.venue(),w.citationCount(),w.citationSource(),w.oaStatus(),w.simulated(),
                w.sourceKey(),w.sourceUrl(),w.contributors(),w.institutionIds(),w.fields(),w.details(),null,w.sourceUpdatedAt()));
            String raw=w.rawPayload()==null?normalized:json.writeValueAsString(w.rawPayload());
            if(raw.length()>1_000_000) throw ApiException.bad("单条原始来源超过 1 MiB 字符限制");
            String checksum=AuthService.hash(raw),metadataHash=materialHash(w,n);
            var head=db.rows("""
                SELECT h.*,s.checksum FROM source_head h JOIN source_record s ON s.id=h.last_source_id
                WHERE h.source_name=? AND h.source_key=?
                """,batch.sourceName(),w.sourceKey());
            var byKey=db.rows("SELECT * FROM work WHERE canonical_key=?",n.key());
            Map<String,Object> current=!head.isEmpty()?db.one("SELECT * FROM work WHERE id=?",head.getFirst().get("workId"))
                :byKey.isEmpty()?null:byKey.getFirst();
            String workId=current==null?Db.id():current.get("id").toString();
            boolean identicalObservation=!head.isEmpty()&&head.getFirst().get("checksum").equals(checksum);
            String conflict=null;boolean accept=false,write=false;
            if(current==null) {accept=true;write=true;inserted++;}
            else if(identicalObservation&&metadataHash.equals(existingMaterialHash(current))) {unchanged++;}
            else if(identicalObservation) {conflict="REPROCESS_REVIEW_REQUIRED";}
            else {
                boolean owner=batch.sourceName().equals(current.get("primarySourceName"))&&w.sourceKey().equals(current.get("primarySourceKey"));
                String oldKey=current.get("canonicalKey").toString();
                boolean identityConflict=(!byKey.isEmpty()&&!byKey.getFirst().get("id").equals(workId))
                    ||(!oldKey.equals(n.key())&&(!owner||strongKey(oldKey,current.get("type").toString())
                        ||!current.get("type").equals(w.type())||!current.get("simulated").equals(w.simulated())));
                if(identityConflict) conflict="SOURCE_IDENTITY_CONFLICT";
                else if(metadataHash.equals(existingMaterialHash(current))) {
                    accept=true;
                    if(owner&&w.sourceUpdatedAt()!=null) db.update("UPDATE work SET source_updated_at=? WHERE id=? AND (source_updated_at IS NULL OR source_updated_at<?)",w.sourceUpdatedAt(),workId,w.sourceUpdatedAt());
                }
                else if(Boolean.TRUE.equals(current.get("metadataLocked"))) conflict="MANUALLY_LOCKED_METADATA";
                else if(!owner) conflict="CROSS_SOURCE_FIELD_CONFLICT";
                else if(!w.simulated()&&w.sourceUpdatedAt()==null) conflict="MISSING_SOURCE_UPDATE_TIME";
                else if(w.sourceUpdatedAt()!=null&&current.get("sourceUpdatedAt") instanceof Number old
                    &&w.sourceUpdatedAt()<=old.longValue()) conflict=w.sourceUpdatedAt()<old.longValue()?"STALE_SOURCE_OBSERVATION":"SAME_TIME_DIFFERENT_CONTENT";
                else {accept=true;write=true;updated++;}
            }
            if(write) {
                writeCurrent(w,n,workId,current,metadataHash,batch.sourceName(),next,now,trustedCrossref);
                changed.add(workId);publicChanged=true;
            }
            var known=db.rows("SELECT id,accepted FROM source_record WHERE source_name=? AND source_key=? AND checksum=?",batch.sourceName(),w.sourceKey(),checksum);
            String sourceId;
            if(known.isEmpty()) {
                sourceId=Db.id();
                db.update("""
                    INSERT INTO source_record(id,work_id,source_name,source_key,source_url,checksum,raw_json,fetched_at,revision,accepted,source_updated_at,normalized_json)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    """,sourceId,workId,batch.sourceName(),w.sourceKey(),w.sourceUrl(),checksum,raw,now,next,accept,w.sourceUpdatedAt(),normalized);
                if(accept) publicChanged=true;
            } else sourceId=known.getFirst().get("id").toString();
            String parser=Objects.toString(w.details().get("parserVersion"),"manual-v1");
            String rule=Objects.toString(w.details().get("ruleVersion"),"normalize-v2");
            if(parser.length()>100||rule.length()>100) throw ApiException.bad("解析或规则版本过长");
            if(db.count("SELECT COUNT(*) FROM source_processing WHERE source_id=? AND parser_version=? AND rule_version=? AND normalized_hash=?",sourceId,parser,rule,metadataHash)==0)
                db.update("INSERT INTO source_processing VALUES(?,?,?,?,?,?,?,?,?)",Db.id(),sourceId,parser,rule,metadataHash,normalized,
                    conflict!=null?"REVIEW_REQUIRED":identicalObservation?"UNCHANGED":"COMMITTED",write?next:revision,now);
            if(observations.add(sourceId)) db.update("INSERT INTO source_observation VALUES(?,?)",taskId,sourceId);
            if(head.isEmpty()) db.update("INSERT INTO source_head VALUES(?,?,?,?,?)",batch.sourceName(),w.sourceKey(),workId,sourceId,now);
            else db.update("UPDATE source_head SET last_source_id=?,last_seen_at=? WHERE source_name=? AND source_key=?",sourceId,now,batch.sourceName(),w.sourceKey());
            if(conflict!=null) {
                conflicts++;
                if(db.count("SELECT COUNT(*) FROM metadata_conflict WHERE work_id=? AND source_id=? AND reason=?",workId,sourceId,conflict)==0)
                    db.update("INSERT INTO metadata_conflict(id,work_id,source_id,base_revision,reason,state,created_at) VALUES(?,?,?,?,?,'OPEN',?)",Db.id(),workId,sourceId,revision,conflict,now);
            }
        }
        for(String workId:changed) {snapshots.publish(workId,next);searchIndex.index(workId,next);}
        long published=publicChanged?next:revision;
        db.update("UPDATE import_task SET state='SUCCESS',inserted=?,duplicates=?,updated=?,unchanged=?,conflicts=?,revision=? WHERE id=?",
            inserted,batch.works().size()-inserted,updated,unchanged,conflicts,published,taskId);
        if(publicChanged) db.update("UPDATE catalog_release SET revision=? WHERE id=1",next);
        audit(actor.id(),taskId,"IMPORT_PUBLISHED","RUNNING","SUCCESS","公开版本 "+published+"；新增 "+inserted+"，更新 "+updated+"，未变 "+unchanged+"，待复核 "+conflicts);
        return db.one("SELECT * FROM import_task WHERE id=?",taskId);
    }
    private static boolean strongKey(String key,String type) {
        int prefix=key.indexOf(":"+type+":");
        String business=prefix<0?key:key.substring(prefix+type.length()+2);
        return business.startsWith("doi:")||business.startsWith("patent:")||business.startsWith("project:")||business.startsWith("award:");
    }
    private String existingMaterialHash(Map<String,Object> current) {
        if(current.get("metadataHash")!=null) return current.get("metadataHash").toString();
        var legacy=db.rows("""
            SELECT raw_json FROM source_record WHERE work_id=? AND source_name=? AND source_key=? AND accepted=TRUE
            ORDER BY revision,fetched_at,id LIMIT 1
            """,current.get("id"),current.get("primarySourceName"),current.get("primarySourceKey"));
        if(legacy.isEmpty()) return "";
        try {var w=json.readValue(legacy.getFirst().get("rawJson").toString(),WorkInput.class);return materialHash(w,normalize(w,current.get("primarySourceName").toString()));}
        catch(RuntimeException ignored) {return "";} // Unknown old material requires review across sources.
    }
    private String materialHash(WorkInput w,Normalized n) {
        Map<String,Object> material=new TreeMap<>();
        material.put("title",n.title());material.put("type",w.type());material.put("date",blank(w.date())?null:w.date());
        material.put("doi",n.doi());material.put("identifier",w.identifier());material.put("identifierType",w.identifierType());material.put("authority",w.authority());
        material.put("abstract",Objects.toString(w.abstractText(),""));material.put("venue",Objects.toString(w.venue(),""));
        material.put("citations",w.citationCount());material.put("citationSource",w.citationSource());material.put("oa",Objects.requireNonNullElse(w.oaStatus(),"UNKNOWN"));
        var people=new ArrayList<Map<String,Object>>();
        for(var c:w.contributors()) {
            Map<String,Object> person=new TreeMap<>();person.put("id",blank(c.scholarId())?null:c.scholarId());person.put("name",c.name());person.put("role",c.role());
            person.put("institution",blank(c.institutionId())?null:c.institutionId());person.put("orcid",normalizedOrcid(c.orcid()));
            person.put("affiliations",c.rawAffiliations()==null?List.of():c.rawAffiliations());people.add(person);
        }
        material.put("people",people);material.put("institutions",new TreeSet<>(w.institutionIds()));material.put("fields",new TreeSet<>(w.fields()));
        material.put("details",canonicalJson(w.details()));
        return AuthService.hash(json.writeValueAsString(material));
    }
    private static Object canonicalJson(Object value) {
        if(value instanceof Map<?,?> map) {var result=new TreeMap<String,Object>();map.forEach((k,v)->result.put(k.toString(),canonicalJson(v)));return result;}
        if(value instanceof List<?> list) return list.stream().map(ImportService::canonicalJson).toList();
        return value;
    }
    private static String normalizedOrcid(String raw) {return blank(raw)?null:ProfileService.normalizeOrcid(raw);}
    private void writeCurrent(WorkInput w,Normalized n,String id,Map<String,Object> current,String hash,String source,long revision,long now,boolean trustedCrossref) {
        String search=(n.title()+" "+Objects.toString(n.doi(),"")+" "+Objects.toString(w.identifier(),"")+" "+Objects.toString(w.abstractText(),"")+" "+Objects.toString(w.venue(),"")
            +" "+String.join(" ",w.contributors().stream().map(c->c.name()+" "+String.join(" ",c.rawAffiliations()==null?List.of():c.rawAffiliations())).toList())).toLowerCase(Locale.ROOT);
        Object[] values={n.key(),w.type(),n.title(),search,blank(w.date())?null:w.date(),n.dateKind(),n.precision(),n.year(),n.doi(),w.identifier(),w.identifierType(),w.authority(),
            Objects.toString(w.abstractText(),""),Objects.toString(w.venue(),""),w.citationCount(),w.citationSource(),Objects.requireNonNullElse(w.oaStatus(),"UNKNOWN"),w.simulated(),revision,
            json.writeValueAsString(w.details()),source,w.sourceKey(),hash,w.sourceUpdatedAt()};
        if(current==null) {
            var insert=new ArrayList<Object>(Arrays.asList(values));insert.add(id);insert.add(now);
            db.update("""
                INSERT INTO work(canonical_key,type,title,search_text,date_value,date_kind,date_precision,year,doi,identifier,identifier_type,authority,
                    abstract_text,venue,citation_count,citation_source,oa_status,simulated,revision,details_json,
                    primary_source_name,primary_source_key,metadata_hash,source_updated_at,id,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,insert.toArray());
        } else {
            var update=new ArrayList<Object>(Arrays.asList(values));update.add(id);
            db.update("""
                UPDATE work SET canonical_key=?,type=?,title=?,search_text=?,date_value=?,date_kind=?,date_precision=?,year=?,doi=?,identifier=?,identifier_type=?,authority=?,
                    abstract_text=?,venue=?,citation_count=?,citation_source=?,oa_status=?,simulated=?,revision=?,details_json=?,
                    primary_source_name=?,primary_source_key=?,metadata_hash=?,source_updated_at=? WHERE id=?
                """,update.toArray());
            db.update("DELETE FROM contributor WHERE work_id=?",id);db.update("DELETE FROM work_institution WHERE work_id=?",id);db.update("DELETE FROM work_field WHERE work_id=?",id);
        }
        int position=0;Set<String> institutions=new HashSet<>(w.institutionIds());
        for(var c:w.contributors()) {
            String scholar=blank(c.scholarId())?null:c.scholarId(),orcid=normalizedOrcid(c.orcid());
            if(scholar==null&&trustedCrossref&&orcid!=null) {
                scholar=(w.simulated()?"DEMO-ORCID-":"ORCID-")+orcid;
                if(db.count("SELECT COUNT(*) FROM scholar WHERE id=?",scholar)==0)
                    db.update("INSERT INTO scholar(id,name,institution_id,bio,simulated) VALUES(?,?,NULL,?,?)",scholar,c.name(),"Crossref 来源 ORCID 署名元数据；不代表账号控制或门户认证。",w.simulated());
            }
            if(scholar!=null&&db.count("SELECT COUNT(*) FROM scholar WHERE id=? AND simulated=?",scholar,w.simulated())!=1) throw ApiException.bad("人物标识不存在或模拟标志不一致");
            db.update("INSERT INTO contributor(work_id,position,scholar_id,name,role,institution_id,orcid,raw_affiliations_json) VALUES(?,?,?,?,?,?,?,?)",
                id,++position,scholar,c.name(),c.role(),blank(c.institutionId())?null:c.institutionId(),orcid,json.writeValueAsString(c.rawAffiliations()==null?List.of():c.rawAffiliations()));
            if(!blank(c.institutionId())) institutions.add(c.institutionId());
        }
        for(String institution:institutions) db.update("INSERT INTO work_institution VALUES(?,?)",id,institution);
        for(String field:new HashSet<>(w.fields())) db.update("INSERT INTO work_field VALUES(?,?)",id,field);
    }
    void audit(String actor,String object,String action,String before,String after,String reason) {
        db.update("INSERT INTO audit_event(id,actor_id,object_id,action,before_state,after_state,reason,created_at) VALUES(?,?,?,?,?,?,?,?)",Db.id(),actor,object,action,before,after,reason,Db.now());
    }
}
