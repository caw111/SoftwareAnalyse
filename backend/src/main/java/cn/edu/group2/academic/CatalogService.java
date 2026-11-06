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
    private final Cache<Query,Map<String,Object>> searchCache=Caffeine.newBuilder().maximumSize(256).expireAfterAccess(Duration.ofMinutes(5)).build();
    private final Cache<Query,Map<String,Object>> statsCache=Caffeine.newBuilder().maximumSize(64).expireAfterAccess(Duration.ofMinutes(10)).build();
    public CatalogService(Db db,ObjectMapper json) {this.db=db;this.json=json;}
    public record Query(String q,String type,String scholar,String institution,String field,Integer from,Integer to,
                        String dataset,String sort,int page,int size,long revision) {}
    Query query(String q,String type,String scholar,String institution,String field,Integer from,Integer to,String dataset,String sort,int page,int size,Long revision) {
        q=q==null?"":q.strip().toLowerCase(Locale.ROOT);
        if(q.length()>120||page<0||size<1||size>50||(long)page*size>10000) throw ApiException.bad("关键词最多 120 字，分页最多 50 条，深度不超过 10,000 条");
        if(!Set.of("","PAPER","PATENT","PROJECT","AWARD").contains(type)||!Set.of("real","demo").contains(dataset)||!Set.of("year","citations","title").contains(sort)) throw ApiException.bad("类型、数据集或排序不受支持");
        if((from!=null&&(from<1000||from>2200))||(to!=null&&(to<1000||to>2200))||(from!=null&&to!=null&&from>to)) throw ApiException.bad("年份范围不合法");
        long latest=db.count("SELECT revision FROM catalog_release WHERE id=1");
        long version=revision==null?latest:revision;
        if(version<0||version>latest) throw new ApiException(410,"RELEASE_UNAVAILABLE","指定数据版本不存在，请重新检索");
        return new Query(q,type,scholar,institution,field,from,to,dataset,sort,page,size,version);
    }
    record Filter(String sql,List<Object> args) {}
    Filter filter(Query q) {
        StringBuilder sql=new StringBuilder("w.revision<=? AND w.simulated=?");
        List<Object> args=new ArrayList<>(List.of(q.revision(),q.dataset().equals("demo")));
        if(!q.q().isBlank()) {
            for(String token:q.q().split("\\s+")) {sql.append(" AND w.search_text LIKE ? ESCAPE '!'");args.add("%"+token.replace("!","!!").replace("%","!%").replace("_","!_")+"%");}
        }
        if(!q.type().isEmpty()) {sql.append(" AND w.type=?");args.add(q.type());}
        if(q.from()!=null) {sql.append(" AND w.year>=?");args.add(q.from());}
        if(q.to()!=null) {sql.append(" AND w.year<=?");args.add(q.to());}
        if(!q.field().isBlank()) {sql.append(" AND EXISTS(SELECT 1 FROM work_field f WHERE f.work_id=w.id AND f.field_name=?)");args.add(q.field());}
        if(!q.scholar().isBlank()) {
            sql.append(" AND EXISTS(SELECT 1 FROM contributor c WHERE c.work_id=w.id AND c.scholar_id=?");args.add(q.scholar());
            if(!q.institution().isBlank()) {sql.append(" AND c.institution_id=?");args.add(q.institution());}sql.append(")");
        } else if(!q.institution().isBlank()) {sql.append(" AND EXISTS(SELECT 1 FROM work_institution i WHERE i.work_id=w.id AND i.institution_id=?)");args.add(q.institution());}
        return new Filter(sql.toString(),args);
    }
    public Map<String,Object> search(Query q) {return searchCache.get(q,this::loadSearch);}
    private Map<String,Object> loadSearch(Query q) {
        var f=filter(q);
        long total=db.count("SELECT COUNT(*) FROM work w WHERE "+f.sql(),f.args().toArray());
        String order=switch(q.sort()) {
            case "citations" -> "w.citation_count DESC NULLS LAST,w.year DESC NULLS LAST,w.id";
            case "title" -> "w.title,w.id";
            default -> "w.year DESC NULLS LAST,w.id";
        };
        var args=new ArrayList<>(f.args());args.add(q.size());args.add((long)q.page()*q.size());
        var rows=db.rows("SELECT w.id,w.type,w.title,w.date_value,w.date_kind,w.date_precision,w.year,w.doi,w.venue,w.citation_count,w.oa_status,w.simulated FROM work w WHERE "+f.sql()+" ORDER BY "+order+" LIMIT ? OFFSET ?",args.toArray());
        if(!rows.isEmpty()) {
            String marks=String.join(",",Collections.nCopies(rows.size(),"?"));
            var ids=rows.stream().map(r->r.get("id")).toArray();
            var people=db.rows("SELECT c.*,i.name AS institution_name FROM contributor c LEFT JOIN institution i ON i.id=c.institution_id WHERE c.work_id IN ("+marks+") ORDER BY c.position",ids);
            for(var row:rows) row.put("contributors",people.stream().filter(p->p.get("workId").equals(row.get("id"))).toList());
        }
        return Map.of("items",rows,"total",total,"page",q.page(),"size",q.size(),"revision",q.revision(),"dataset",q.dataset(),"filters",q,
            "facets",db.rows("SELECT w.type,COUNT(*) AS count FROM work w WHERE "+f.sql()+" GROUP BY w.type ORDER BY w.type",f.args().toArray()));
    }
    public Map<String,Object> detail(String id,Long revision) {
        long latest=db.count("SELECT revision FROM catalog_release WHERE id=1");
        long v=revision==null?latest:revision;
        if(v<0||v>latest) throw new ApiException(410,"RELEASE_UNAVAILABLE","数据版本不存在");
        var row=db.one("SELECT * FROM work WHERE id=? AND revision<=?",id,v);
        row.remove("canonicalKey");row.remove("searchText");
        row.put("details",json.readValue(row.remove("detailsJson").toString(),Map.class));
        row.put("revision",v);
        row.put("contributors",db.rows("SELECT c.*,i.name AS institution_name FROM contributor c LEFT JOIN institution i ON c.institution_id=i.id WHERE c.work_id=? ORDER BY c.position",id));
        row.put("sources",db.rows("SELECT id,source_name,source_key,source_url,checksum,fetched_at FROM source_record WHERE work_id=? AND revision<=? ORDER BY fetched_at,id",id,v));
        row.put("fields",db.rows("SELECT field_name FROM work_field WHERE work_id=? ORDER BY field_name",id));
        row.put("institutions",db.rows("SELECT i.id,i.name FROM work_institution wi JOIN institution i ON i.id=wi.institution_id WHERE wi.work_id=? ORDER BY i.id",id));
        return row;
    }
    public Map<String,Object> stats(Query q) {return statsCache.get(q,this::loadStats);}
    private Map<String,Object> loadStats(Query q) {
        var f=filter(q);var args=f.args().toArray();
        var metrics=db.one("SELECT COUNT(*) AS total,SUM(CASE WHEN w.type='PAPER' THEN 1 ELSE 0 END) AS papers,SUM(CASE WHEN w.type='PAPER' AND w.citation_count IS NOT NULL THEN 1 ELSE 0 END) AS citation_known,SUM(CASE WHEN w.type='PAPER' AND w.oa_status='OPEN' THEN 1 ELSE 0 END) AS open_papers,SUM(CASE WHEN w.type='PAPER' AND w.oa_status='UNKNOWN' THEN 1 ELSE 0 END) AS oa_unknown FROM work w WHERE "+f.sql(),args);
        var institutions=db.rows("SELECT i.id,i.name,COUNT(DISTINCT w.id) AS count FROM work w JOIN work_institution wi ON wi.work_id=w.id JOIN institution i ON i.id=wi.institution_id WHERE "+f.sql()+" GROUP BY i.id,i.name ORDER BY count DESC,i.id LIMIT 100",args);
        long previous=-1;int rank=0,index=0;
        for(var item:institutions) {index++;long count=((Number)item.get("count")).longValue();if(count!=previous)rank=index;previous=count;item.put("rank",rank);}
        return Map.of("revision",q.revision(),"dataset",q.dataset(),"generatedAt",Db.now(),"metrics",metrics,
            "types",db.rows("SELECT w.type,COUNT(*) AS count FROM work w WHERE "+f.sql()+" GROUP BY w.type ORDER BY w.type",args),
            "years",db.rows("SELECT w.year,COUNT(*) AS count FROM work w WHERE "+f.sql()+" GROUP BY w.year ORDER BY w.year NULLS LAST",args),
            "fields",db.rows("SELECT COALESCE(f.field_name,'未分类') AS name,COUNT(DISTINCT w.id) AS count FROM work w LEFT JOIN work_field f ON f.work_id=w.id WHERE "+f.sql()+" GROUP BY f.field_name ORDER BY count DESC,name LIMIT 50",args),
            "institutions",institutions,
            "citations",db.rows("SELECT w.citation_source AS source,SUM(w.citation_count) AS count,COUNT(*) AS covered FROM work w WHERE "+f.sql()+" AND w.type='PAPER' AND w.citation_count IS NOT NULL GROUP BY w.citation_source",args),
            "notes","机构与领域分别按成果去重，多标签合计不等于全库总量；引用按来源分组，缺失不当作零；年度为各类型业务时间。领域数量不是热点预测。");
    }
    public Object scholars(String q,String dataset) {
        if(q.length()>80||!Set.of("real","demo").contains(dataset)) throw ApiException.bad("查询参数不合法");
        return db.rows("SELECT s.*,i.name AS institution_name,CASE WHEN p.user_id IS NULL THEN FALSE ELSE TRUE END AS claimed FROM scholar s LEFT JOIN institution i ON i.id=s.institution_id LEFT JOIN portal_binding p ON p.scholar_id=s.id WHERE s.simulated=? AND (LOWER(s.name) LIKE ? OR s.id=?) ORDER BY s.id LIMIT 100",dataset.equals("demo"),"%"+q.toLowerCase(Locale.ROOT).replace("%","").replace("_","")+"%",q);
    }
    public Object referenceData() {return Map.of("institutions",db.rows("SELECT * FROM institution ORDER BY id"),"fields",db.rows("SELECT DISTINCT field_name AS name FROM work_field ORDER BY field_name"),"revision",db.count("SELECT revision FROM catalog_release WHERE id=1"));}
}
