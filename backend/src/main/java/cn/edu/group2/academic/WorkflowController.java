package cn.edu.group2.academic;

import java.util.Map;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
public class WorkflowController {
    final AuthService auth;final ClaimService claims;final ImportService imports;final Db db;
    WorkflowController(AuthService auth,ClaimService claims,ImportService imports,Db db) {this.auth=auth;this.claims=claims;this.imports=imports;this.db=db;}
    @GetMapping("/claims") Object list(HttpServletRequest r,@RequestParam(defaultValue="false") boolean review) {return claims.list(auth.require(r),review);}
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
