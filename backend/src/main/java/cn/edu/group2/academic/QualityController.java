package cn.edu.group2.academic;

import java.util.*;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin/quality")
public class QualityController {
 private final Db db;private final AuthService auth;
 public QualityController(Db db,AuthService auth) {this.db=db;this.auth=auth;}
 @GetMapping Object overview(HttpServletRequest request,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size) {
  auth.require(request).admin();
  if(page<0||size<1||size>100) throw ApiException.bad("质量列表分页无效");
  var result=new LinkedHashMap<String,Object>();
  result.put("conflicts",db.rows("SELECT c.*,w.title,s.source_name,s.source_key FROM metadata_conflict c JOIN work w ON w.id=c.work_id JOIN source_record s ON s.id=c.source_id ORDER BY c.created_at DESC,c.id LIMIT ? OFFSET ?",size,(long)page*size));
  result.put("total",db.count("SELECT COUNT(*) FROM metadata_conflict"));result.put("page",page);result.put("size",size);
  result.put("openConflicts",db.count("SELECT COUNT(*) FROM metadata_conflict WHERE state='OPEN'"));
  result.put("unclassified",db.count("SELECT COUNT(*) FROM work w WHERE NOT EXISTS(SELECT 1 FROM work_field f WHERE f.work_id=w.id)"));
  result.put("institutionUnmatched",db.count("SELECT COUNT(*) FROM work w WHERE NOT EXISTS(SELECT 1 FROM work_institution i WHERE i.work_id=w.id)"));
  result.put("withSource",db.count("SELECT COUNT(*) FROM work w WHERE EXISTS(SELECT 1 FROM source_record s WHERE s.work_id=w.id AND s.accepted=TRUE)"));
  result.put("catalogTotal",db.count("SELECT COUNT(*) FROM work"));
  result.put("failedCrawls",db.count("SELECT COUNT(*) FROM crawl_task WHERE state='FAILED'"));
  result.put("generatedAt",Db.now());return result;
 }
}
