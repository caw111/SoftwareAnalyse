package cn.edu.group2.academic;

import java.time.Duration;
import java.util.*;
import com.github.benmanes.caffeine.cache.*;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.*;

@Service
public class GraphService {
    final Db db;final CatalogService catalog;
    final Cache<CatalogService.Query,List<Map<String,Object>>> edges=Caffeine.newBuilder().maximumSize(16).expireAfterAccess(Duration.ofMinutes(5)).build();
    GraphService(Db db,CatalogService catalog) {this.db=db;this.catalog=catalog;}
    List<Map<String,Object>> load(CatalogService.Query query) {
        var f=catalog.filter(query);
        var nodes=db.rows("SELECT DISTINCT c.scholar_id FROM work_revision w JOIN contributor_revision c ON c.work_id=w.id AND c.revision=w.revision WHERE "+f.sql()+" AND c.scholar_id IS NOT NULL LIMIT 2001",f.args().toArray());
        if(nodes.size()>2000) throw new ApiException(422,"GRAPH_LIMIT","当前范围超过 2,000 个节点，请缩小年份或领域范围");
        var result=db.rows("SELECT a.scholar_id AS source,b.scholar_id AS target,COUNT(DISTINCT w.id) AS weight FROM work_revision w JOIN contributor_revision a ON a.work_id=w.id AND a.revision=w.revision JOIN contributor_revision b ON b.work_id=w.id AND b.revision=w.revision AND a.scholar_id<b.scholar_id WHERE "+f.sql()+" GROUP BY a.scholar_id,b.scholar_id ORDER BY a.scholar_id,b.scholar_id LIMIT 10001",f.args().toArray());
        if(result.size()>10000) throw new ApiException(422,"GRAPH_LIMIT","当前范围超过 10,000 条边，请缩小范围");
        return result;
    }
    public Object path(String start,String end,CatalogService.Query q) {
        if(start.isBlank()||end.isBlank()) throw ApiException.bad("请选择起点和终点学者");
        for(String id:List.of(start,end)) if(db.count("SELECT COUNT(*) FROM scholar WHERE id=? AND simulated=?",id,q.dataset().equals("demo"))!=1) throw ApiException.notFound();
        var graph=edges.get(q,this::load);
        Map<String,List<String>> adjacency=new HashMap<>();
        for(var edge:graph) {
            String a=edge.get("source").toString(),b=edge.get("target").toString();
            adjacency.computeIfAbsent(a,k->new ArrayList<>()).add(b);adjacency.computeIfAbsent(b,k->new ArrayList<>()).add(a);
        }
        Map<String,String> parent=new HashMap<>();Map<String,Integer> depth=new HashMap<>();
        var queue=new ArrayDeque<String>();queue.add(start);parent.put(start,null);depth.put(start,0);
        boolean limited=false;
        while(!queue.isEmpty()&&!parent.containsKey(end)) {
            String current=queue.remove();
            if(depth.get(current)>=6) {limited=true;continue;}
            for(String next:adjacency.getOrDefault(current,List.of())) if(!parent.containsKey(next)) {parent.put(next,current);depth.put(next,depth.get(current)+1);queue.add(next);}
        }
        if(!parent.containsKey(end)) return Map.of("found",false,"limited",limited,"revision",q.revision(),"message",limited?"六跳范围内未找到路径，不代表全网不连通":"当前数据范围内不存在共著路径","nodes",List.of(),"edges",List.of());
        List<String> ids=new ArrayList<>();for(String at=end;at!=null;at=parent.get(at)) ids.add(at);Collections.reverse(ids);
        List<Map<String,Object>> nodes=new ArrayList<>(),pathEdges=new ArrayList<>();
        for(String id:ids) nodes.add(db.one("SELECT s.id,s.name,i.name AS institution_name FROM scholar s LEFT JOIN institution i ON s.institution_id=i.id WHERE s.id=?",id));
        var f=catalog.filter(q);
        for(int i=0;i<ids.size()-1;i++) {
            String a=ids.get(i),b=ids.get(i+1);
            var args=new ArrayList<>(f.args());args.add(a);args.add(b);
            var papers=db.rows("SELECT DISTINCT w.id,w.title,w.year FROM work_revision w JOIN contributor_revision a ON a.work_id=w.id AND a.revision=w.revision JOIN contributor_revision b ON b.work_id=w.id AND b.revision=w.revision WHERE "+f.sql()+" AND a.scholar_id=? AND b.scholar_id=? ORDER BY w.year DESC NULLS LAST,w.id LIMIT 20",args.toArray());
            long weight=((Number)graph.stream().filter(e->(e.get("source").equals(a)&&e.get("target").equals(b))||(e.get("source").equals(b)&&e.get("target").equals(a))).findFirst().orElseThrow().get("weight")).longValue();
            pathEdges.add(Map.of("source",a,"target",b,"weight",weight,"evidence",papers,"evidenceTruncated",weight>papers.size()));
        }
        return Map.of("found",true,"limited",false,"revision",q.revision(),"nodes",nodes,"edges",pathEdges,"hops",pathEdges.size(),"message","仅依据当前范围的论文共著关系；每条边最多展示 20 篇证据");
    }
}

@RestController
class GraphController {
    final GraphService graph;final CatalogService catalog;
    GraphController(GraphService graph,CatalogService catalog) {this.graph=graph;this.catalog=catalog;}
    @GetMapping("/api/graph/path")
    Object path(@RequestParam String start,@RequestParam String end,@RequestParam(defaultValue="real") String dataset,
        @RequestParam(defaultValue="") String field,@RequestParam(defaultValue="") String institution,
        @RequestParam(required=false) Integer from,@RequestParam(required=false) Integer to,@RequestParam(required=false) Long revision) {
        return graph.path(start,end,catalog.query("","PAPER","",institution,field,from,to,dataset,"year",0,20,revision));
    }
}
