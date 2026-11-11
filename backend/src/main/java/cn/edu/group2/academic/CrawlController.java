package cn.edu.group2.academic;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin/crawl")
public class CrawlController {
    private final AuthService auth;private final CrawlStore store;private final CrossrefClient client;
    CrawlController(AuthService auth,CrawlStore store,CrossrefClient client) {this.auth=auth;this.store=store;this.client=client;}
    @GetMapping("/sources") Object sources(HttpServletRequest request) {
        auth.require(request).admin();var sources=store.sources();
        sources.forEach(s->{s.put("endpoint",CrossrefClient.ENDPOINT+"/works");s.put("contactConfigured",client.contactConfigured());});return sources;
    }
    @PostMapping("/sources/{id}/settings") Object settings(HttpServletRequest request,@PathVariable String id,@Valid @RequestBody CrawlStore.Settings body) {return store.settings(id,body,auth.require(request));}
    @GetMapping("/checkpoints") Object checkpoints(HttpServletRequest request) {auth.require(request).admin();return store.checkpoints();}
    @GetMapping("/tasks") Object tasks(HttpServletRequest request,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size) {auth.require(request).admin();return store.list(page,size);}
    @PostMapping("/tasks") Object create(HttpServletRequest request,@Valid @RequestBody CrawlStore.Create body) {return store.create(body,auth.require(request));}
    @GetMapping("/tasks/{id}") Object detail(HttpServletRequest request,@PathVariable String id) {auth.require(request).admin();return store.detail(id);}
    @GetMapping("/tasks/{id}/pages/{page}") Object page(HttpServletRequest request,@PathVariable String id,@PathVariable int page) {auth.require(request).admin();return store.rawPage(id,page);}
    @PostMapping("/tasks/{id}/actions") Object action(HttpServletRequest request,@PathVariable String id,@Valid @RequestBody CrawlStore.Action body) {return store.action(id,body,auth.require(request));}
}
