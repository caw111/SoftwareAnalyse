package cn.edu.group2.academic;

import java.util.Map;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
public class WorkflowController {
    final AuthService auth;final ClaimService claims;final ImportService imports;final Db db;final ProfileService profiles;
    WorkflowController(AuthService auth,ClaimService claims,ImportService imports,Db db,ProfileService profiles) {this.auth=auth;this.claims=claims;this.imports=imports;this.db=db;this.profiles=profiles;}
    @GetMapping("/claims") Object list(HttpServletRequest r,@RequestParam(defaultValue="false") boolean review,
        @RequestParam(required=false) Integer page,@RequestParam(defaultValue="30") int size) {
        var actor=auth.require(r);return page==null?claims.list(actor,review):claims.page(actor,review,page,size);
    }
    @PostMapping("/me/profile") Object profile(HttpServletRequest r,@Valid @RequestBody ProfileService.Update input) {
        return profiles.update(input,auth.require(r));
    }
    @GetMapping("/admin/statistics") Object statistics(HttpServletRequest r) {
        auth.require(r).admin();
        var summary=db.one("""
            SELECT (SELECT COUNT(*) FROM work) AS catalog_total,
                   (SELECT COUNT(*) FROM app_user) AS users,
                   (SELECT COUNT(*) FROM app_user WHERE role='RESEARCHER') AS researchers,
                   (SELECT COUNT(*) FROM claim WHERE state='PENDING_REVIEW') AS pending_applications,
                   (SELECT COUNT(*) FROM claim WHERE state='UNDER_REVIEW') AS reviewing_applications,
                   (SELECT COUNT(*) FROM claim WHERE state='APPROVED') AS approved_applications,
                   (SELECT COUNT(*) FROM import_task) AS imports,
                   (SELECT revision FROM catalog_release WHERE id=1) AS catalog_revision
            """);
        summary.put("byType",db.rows("SELECT type,COUNT(*) AS count FROM work GROUP BY type ORDER BY type"));
        summary.put("byState",db.rows("SELECT state,COUNT(*) AS count FROM claim GROUP BY state ORDER BY state"));
        summary.put("realCatalogTotal",db.count("SELECT COUNT(*) FROM work WHERE simulated=FALSE"));
        summary.put("demoCatalogTotal",db.count("SELECT COUNT(*) FROM work WHERE simulated=TRUE"));
        return summary;
    }
    @GetMapping("/claims/{id}") Object detail(HttpServletRequest r,@PathVariable String id) {return claims.detail(id,auth.require(r));}
    @PostMapping("/claims") Object create(HttpServletRequest r,@Valid @RequestBody ClaimService.Create input) {return claims.create(input,auth.require(r));}
    @PostMapping("/claims/{id}/actions") Object action(HttpServletRequest r,@PathVariable String id,@Valid @RequestBody ClaimService.Action input) {return claims.action(id,input,auth.require(r));}
    @GetMapping("/me/outcomes") Object outcomes(HttpServletRequest r) {return claims.myOutcomes(auth.require(r));}
    @PostMapping("/admin/imports") Object ingest(HttpServletRequest r,@Valid @RequestBody ImportService.Batch batch) {return imports.ingest(batch,auth.require(r));}
    @GetMapping("/admin/imports") Object imports(HttpServletRequest r) {auth.require(r).admin();return db.rows("SELECT * FROM import_task ORDER BY created_at DESC LIMIT 100");}
    @GetMapping("/admin/audit") Object audit(HttpServletRequest r) {auth.require(r).admin();return db.rows("SELECT * FROM audit_event ORDER BY created_at DESC LIMIT 200");}
    record Institution(@NotBlank @Size(max=80) String id,@NotBlank @Size(max=200) String name) {}
    record Scholar(@NotBlank @Size(max=80) String id,@NotBlank @Size(max=100) String name,@NotBlank @Size(max=80) String institutionId,@NotNull @Size(max=2000) String bio,boolean simulated) {}
    @PostMapping("/admin/institutions") Object institution(HttpServletRequest r,@Valid @RequestBody Institution input) {
        auth.require(r).admin();db.update("INSERT INTO institution VALUES(?,?)",input.id(),input.name());return Map.of("id",input.id());
    }
    @PostMapping("/admin/scholars") Object scholar(HttpServletRequest r,@Valid @RequestBody Scholar input) {
        auth.require(r).admin();db.update("INSERT INTO scholar VALUES(?,?,?,?,?)",input.id(),input.name(),input.institutionId(),input.bio(),input.simulated());return Map.of("id",input.id());
    }
}
