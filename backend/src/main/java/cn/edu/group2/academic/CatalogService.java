package cn.edu.group2.academic;

import java.time.Duration;
import java.util.*;
import com.github.benmanes.caffeine.cache.*;
import org.springframework.stereotype.Service;
import tools.jackson.databind.ObjectMapper;

@Service
public class CatalogService {
    private final Db db;
    private final ObjectMapper json;
    private final SearchIndexService index;
    private final Cache<Query,Map<String,Object>> searchCache=Caffeine.newBuilder().maximumSize(256).expireAfterAccess(Duration.ofMinutes(5)).build();
    private final Cache<Query,Map<String,Object>> statsCache=Caffeine.newBuilder().maximumSize(64).expireAfterAccess(Duration.ofMinutes(10)).build();
    public CatalogService(Db db,ObjectMapper json,SearchIndexService index) {this.db=db;this.json=json;this.index=index;}
    public record Query(String q,String type,String scholar,String institution,String field,Integer from,Integer to,
                        String dataset,String sort,int page,int size,long revision) {}
    Query query(String q,String type,String scholar,String institution,String field,Integer from,Integer to,String dataset,String sort,int page,int size,Long revision) {
        q=q==null?"":q.strip().toLowerCase(Locale.ROOT);
        if(q.length()>120||page<0||size<1||size>50||(long)page*size>10000) throw ApiException.bad("关键词最多 120 字，分页最多 50 条，深度不超过 10,000 条");
        if(!Set.of("","PAPER","PATENT","PROJECT","AWARD").contains(type)||!Set.of("real","demo").contains(dataset)||!Set.of("relevance","year","citations","title").contains(sort)) throw ApiException.bad("类型、数据集或排序不受支持");
        SearchTerms.query(q);
        if((from!=null&&(from<1000||from>2200))||(to!=null&&(to<1000||to>2200))||(from!=null&&to!=null&&from>to)) throw ApiException.bad("年份范围不合法");
        long latest=db.count("SELECT revision FROM catalog_release WHERE id=1");
        long version=revision==null?latest:revision;
        if(version<0||version>latest) throw new ApiException(410,"RELEASE_UNAVAILABLE","指定数据版本不存在，请重新检索");
        return new Query(q,type,scholar,institution,field,from,to,dataset,sort,page,size,version);
    }
    record Filter(String sql,List<Object> args) {}
    static String exactKey(String query) {return query.replaceFirst("^(https?://(dx\\.)?doi\\.org/|doi:\\s*)","");}
    Filter filter(Query q) {
        StringBuilder sql=new StringBuilder("w.revision<=? AND (w.valid_to IS NULL OR w.valid_to>?) AND w.simulated=?");
        List<Object> args=new ArrayList<>(List.of(q.revision(),q.revision(),q.dataset().equals("demo")));
        if(!q.q().isBlank()) {
            String exact=exactKey(q.q());
            sql.append(" AND (LOWER(COALESCE(w.doi,''))=? OR LOWER(COALESCE(w.identifier,''))=? OR (");args.add(exact);args.add(exact);
            var terms=SearchTerms.query(q.q());
            if(terms.isEmpty()) sql.append("1=0");
            for(int i=0;i<terms.size();i++) {
                if(i>0) sql.append(" AND ");
                sql.append("EXISTS(SELECT 1 FROM search_term st WHERE st.work_id=w.id AND st.revision=w.revision AND st.term=?)");args.add(terms.get(i));
            }
            sql.append("))");
        }
        if(!q.type().isEmpty()) {sql.append(" AND w.type=?");args.add(q.type());}
        if(q.from()!=null) {sql.append(" AND w.year>=?");args.add(q.from());}
        if(q.to()!=null) {sql.append(" AND w.year<=?");args.add(q.to());}
        if(!q.field().isBlank()) {sql.append(" AND EXISTS(SELECT 1 FROM work_field_revision f WHERE f.work_id=w.id AND f.revision=w.revision AND f.field_name=?)");args.add(q.field());}
        if(!q.scholar().isBlank()) {
            sql.append(" AND EXISTS(SELECT 1 FROM contributor_revision c WHERE c.work_id=w.id AND c.revision=w.revision AND c.scholar_id=?");args.add(q.scholar());
            if(!q.institution().isBlank()) {sql.append(" AND c.institution_id=?");args.add(q.institution());}sql.append(")");
        } else if(!q.institution().isBlank()) {sql.append(" AND EXISTS(SELECT 1 FROM work_institution_revision i WHERE i.work_id=w.id AND i.revision=w.revision AND i.institution_id=?)");args.add(q.institution());}
        return new Filter(sql.toString(),args);
    }
    public Map<String,Object> search(Query q) {return searchCache.get(q,this::loadSearch);}
    private Map<String,Object> loadSearch(Query q) {
        var f=filter(q);
        long total=db.count("SELECT COUNT(*) FROM work_revision w WHERE "+f.sql(),f.args().toArray());
        var terms=SearchTerms.query(q.q());
        boolean ranked=!terms.isEmpty();
        String prefix="",join="",score="0.0",exact="0";
        var args=new ArrayList<Object>();
        if(ranked) {
            var ranking=index.ranking(q.revision(),q.dataset().equals("demo"),terms);
            prefix=ranking.sql();args.addAll(ranking.args());
            join=" LEFT JOIN relevance r ON r.work_id=w.id AND r.revision=w.revision ";score="COALESCE(r.score,0.0)";
        }
        if(!q.q().isEmpty()) {exact="CASE WHEN LOWER(COALESCE(w.doi,''))=? OR LOWER(COALESCE(w.identifier,''))=? THEN 1 ELSE 0 END";args.add(exactKey(q.q()));args.add(exactKey(q.q()));}
        String order=switch(q.sort()) {
            case "citations" -> "w.citation_count DESC NULLS LAST,w.year DESC NULLS LAST,w.id";
            case "title" -> "w.title,w.id";
            case "year" -> "w.year DESC NULLS LAST,w.date_value DESC NULLS LAST,relevance_score DESC,w.id";
            default -> ranked?"exact_match DESC,relevance_score DESC,w.year DESC NULLS LAST,w.id":"w.revision DESC,w.id";
        };
        args.addAll(f.args());args.add(q.size());args.add((long)q.page()*q.size());
        var rows=db.rows(prefix+"SELECT w.id,w.type,w.title,w.date_value,w.date_kind,w.date_precision,w.year,w.doi,w.venue,w.citation_count,w.oa_status,w.simulated,w.revision AS content_revision,"+score+" AS relevance_score,"+exact+" AS exact_match FROM work_revision w "+join+" WHERE "+f.sql()+" ORDER BY "+order+" LIMIT ? OFFSET ?",args.toArray());
        if(!rows.isEmpty()) {
            var peopleArgs=new ArrayList<Object>();var pairs=new ArrayList<String>();
            for(var row:rows) {pairs.add("(c.work_id=? AND c.revision=?)");peopleArgs.add(row.get("id"));peopleArgs.add(row.get("contentRevision"));}
            var people=db.rows("SELECT c.*,i.name AS institution_name FROM contributor_revision c LEFT JOIN institution i ON i.id=c.institution_id WHERE "+String.join(" OR ",pairs)+" ORDER BY c.position",peopleArgs.toArray());
            for(var row:rows) row.put("contributors",people.stream().filter(p->p.get("workId").equals(row.get("id"))&&p.get("revision").equals(row.get("contentRevision"))).toList());
        }
        var result=new LinkedHashMap<String,Object>();
        result.put("items",rows);result.put("total",total);result.put("page",q.page());result.put("size",q.size());result.put("revision",q.revision());result.put("dataset",q.dataset());result.put("filters",q);
        result.put("facets",db.rows("SELECT w.type,COUNT(*) AS count FROM work_revision w WHERE "+f.sql()+" GROUP BY w.type ORDER BY w.type",f.args().toArray()));
        result.put("ranking",Map.of("algorithm",SearchIndexService.RULE_VERSION,"tokenizer",SearchTerms.VERSION,"k1",1.2,"b",0.75,"weightsStatus","baseline-needs-server-evaluation","exactIdentifierFirst",true));
        return result;
    }
    public Map<String,Object> detail(String id,Long revision) {
        long latest=db.count("SELECT revision FROM catalog_release WHERE id=1");
        long v=revision==null?latest:revision;
        if(v<0||v>latest) throw new ApiException(410,"RELEASE_UNAVAILABLE","数据版本不存在");
        var row=db.one("SELECT * FROM work_revision WHERE id=? AND revision<=? AND (valid_to IS NULL OR valid_to>?)",id,v,v);
        long contentRevision=((Number)row.get("revision")).longValue();
        row.remove("canonicalKey");row.remove("searchText");row.remove("validTo");
        row.put("details",json.readValue(row.remove("detailsJson").toString(),Map.class));
        row.put("revision",v);row.put("contentRevision",contentRevision);
        row.put("contributors",db.rows("SELECT c.*,i.name AS institution_name FROM contributor_revision c LEFT JOIN institution i ON c.institution_id=i.id WHERE c.work_id=? AND c.revision=? ORDER BY c.position",id,contentRevision));
        row.put("sources",db.rows("SELECT id,source_name,source_key,source_url,checksum,fetched_at,source_updated_at FROM source_record WHERE work_id=? AND accepted=TRUE AND revision<=? ORDER BY fetched_at,id",id,v));
        row.put("fields",db.rows("SELECT field_name FROM work_field_revision WHERE work_id=? AND revision=? ORDER BY field_name",id,contentRevision));
        row.put("institutions",db.rows("SELECT i.id,i.name FROM work_institution_revision wi JOIN institution i ON i.id=wi.institution_id WHERE wi.work_id=? AND wi.revision=? ORDER BY i.id",id,contentRevision));
        return row;
    }
    public Map<String,Object> stats(Query q) {
        // Sort/page do not change aggregation; normalize cache keys to avoid duplicate work.
        return statsCache.get(new Query(q.q(),q.type(),q.scholar(),q.institution(),q.field(),q.from(),q.to(),q.dataset(),"relevance",0,20,q.revision()),this::loadStats);
    }
    private Map<String,Object> loadStats(Query q) {
        var f=filter(q);var args=f.args().toArray();
        var metrics=db.one("SELECT COUNT(*) AS total,COALESCE(SUM(CASE WHEN w.type='PAPER' THEN 1 ELSE 0 END),0) AS papers,COALESCE(SUM(CASE WHEN w.type='PAPER' AND w.citation_count IS NOT NULL THEN 1 ELSE 0 END),0) AS citation_known,COALESCE(SUM(CASE WHEN w.type='PAPER' AND w.oa_status='OPEN' THEN 1 ELSE 0 END),0) AS open_papers,COALESCE(SUM(CASE WHEN w.type='PAPER' AND w.oa_status='UNKNOWN' THEN 1 ELSE 0 END),0) AS oa_unknown FROM work_revision w WHERE "+f.sql(),args);
        var institutions=db.rows("SELECT i.id,i.name,COUNT(DISTINCT w.id) AS count FROM work_revision w JOIN work_institution_revision wi ON wi.work_id=w.id AND wi.revision=w.revision JOIN institution i ON i.id=wi.institution_id WHERE "+f.sql()+" GROUP BY i.id,i.name ORDER BY count DESC,i.id LIMIT 100",args);
        long previous=-1;int rank=0,position=0;
        for(var item:institutions) {position++;long count=((Number)item.get("count")).longValue();if(count!=previous)rank=position;previous=count;item.put("rank",rank);}
        var result=new LinkedHashMap<String,Object>();
        result.put("revision",q.revision());result.put("dataset",q.dataset());result.put("generatedAt",Db.now());result.put("metrics",metrics);
        result.put("types",db.rows("SELECT w.type,COUNT(*) AS count FROM work_revision w WHERE "+f.sql()+" GROUP BY w.type ORDER BY w.type",args));
        result.put("years",db.rows("SELECT w.year,COUNT(*) AS count FROM work_revision w WHERE "+f.sql()+" GROUP BY w.year ORDER BY w.year NULLS LAST",args));
        result.put("fields",db.rows("SELECT COALESCE(f.field_name,'未分类') AS name,COUNT(DISTINCT w.id) AS count FROM work_revision w LEFT JOIN work_field_revision f ON f.work_id=w.id AND f.revision=w.revision WHERE "+f.sql()+" GROUP BY f.field_name ORDER BY count DESC,name LIMIT 50",args));
        result.put("institutions",institutions);
        result.put("citations",db.rows("SELECT w.citation_source AS source,SUM(w.citation_count) AS count,COUNT(*) AS covered FROM work_revision w WHERE "+f.sql()+" AND w.type='PAPER' AND w.citation_count IS NOT NULL GROUP BY w.citation_source",args));
        var hotspots=db.rows("SELECT st.term,COUNT(DISTINCT w.id) AS count FROM work_revision w JOIN search_term st ON st.work_id=w.id AND st.revision=w.revision AND st.text_term=TRUE WHERE "+f.sql()+" GROUP BY st.term ORDER BY count DESC,st.term LIMIT 20",args);
        long denominator=db.count("SELECT COUNT(*) FROM work_revision w JOIN search_document d ON d.work_id=w.id AND d.revision=w.revision WHERE "+f.sql()+" AND d.text_present=TRUE",args);
        for(var hot:hotspots) hot.put("share",denominator==0?null:((Number)hot.get("count")).doubleValue()/denominator);
        result.put("hotspots",hotspots);result.put("hotspotDenominator",denominator);
        result.put("hotspotRule",SearchTerms.VERSION+"/title-and-abstract/document-frequency/no-prediction");
        List<Map<String,Object>> trend=List.of();
        if(!hotspots.isEmpty()) {
            var hotArgs=new ArrayList<>(f.args());hotArgs.addAll(hotspots.stream().map(h->h.get("term")).toList());
            trend=db.rows("SELECT w.year,st.term,COUNT(DISTINCT w.id) AS count FROM work_revision w JOIN search_term st ON st.work_id=w.id AND st.revision=w.revision AND st.text_term=TRUE WHERE "+f.sql()+" AND st.term IN ("+String.join(",",Collections.nCopies(hotspots.size(),"?"))+") GROUP BY w.year,st.term ORDER BY w.year NULLS LAST,st.term",hotArgs.toArray());
        }
        result.put("hotspotTrend",trend);
        result.put("hotspotBuckets",db.rows("SELECT w.year,COUNT(*) AS denominator FROM work_revision w JOIN search_document d ON d.work_id=w.id AND d.revision=w.revision WHERE "+f.sql()+" AND d.text_present=TRUE GROUP BY w.year ORDER BY w.year NULLS LAST",args));
        var quality=db.one("SELECT COUNT(*) AS total,COALESCE(SUM(CASE WHEN NOT EXISTS(SELECT 1 FROM work_field_revision wf WHERE wf.work_id=w.id AND wf.revision=w.revision) THEN 1 ELSE 0 END),0) AS unclassified,COALESCE(SUM(CASE WHEN NOT EXISTS(SELECT 1 FROM work_institution_revision wi WHERE wi.work_id=w.id AND wi.revision=w.revision) THEN 1 ELSE 0 END),0) AS institution_unmatched,COALESCE(SUM(CASE WHEN w.abstract_text<>'' THEN 1 ELSE 0 END),0) AS abstract_available FROM work_revision w WHERE "+f.sql(),args);
        result.put("coverage",quality);
        result.put("notes","机构整计数、多领域分别按规范成果去重，分组之和不等于全库总量；引用按来源分组且未知不当作零；热点为标题/摘要词项的文档频次，同篇重复词只计一次，不是已确认学科或预测。年份为各类业务时间，未知单列。");
        return result;
    }
    public Object scholars(String q,String dataset) {
        if(q.length()>80||!Set.of("real","demo").contains(dataset)) throw ApiException.bad("查询参数不合法");
        return db.rows("SELECT s.*,i.name AS institution_name,CASE WHEN p.user_id IS NULL THEN FALSE ELSE TRUE END AS claimed FROM scholar s LEFT JOIN institution i ON i.id=s.institution_id LEFT JOIN portal_binding p ON p.scholar_id=s.id WHERE s.simulated=? AND (LOWER(s.name) LIKE ? OR s.id=?) ORDER BY s.id LIMIT 100",dataset.equals("demo"),"%"+q.toLowerCase(Locale.ROOT).replace("%","").replace("_","")+"%",q);
    }
    public Object referenceData() {return Map.of("institutions",db.rows("SELECT * FROM institution ORDER BY id"),"fields",db.rows("SELECT DISTINCT field_name AS name FROM work_field ORDER BY field_name"),"revision",db.count("SELECT revision FROM catalog_release WHERE id=1"));}
}
