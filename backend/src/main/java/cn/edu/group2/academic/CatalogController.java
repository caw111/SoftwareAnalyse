package cn.edu.group2.academic;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
public class CatalogController {
    private final CatalogService catalog;
    CatalogController(CatalogService catalog) {this.catalog=catalog;}
    @GetMapping({"/works","/statistics"})
    Object search(jakarta.servlet.http.HttpServletRequest request,
        @RequestParam(defaultValue="") String q,@RequestParam(defaultValue="") String type,
        @RequestParam(defaultValue="") String scholar,@RequestParam(defaultValue="") String institution,
        @RequestParam(defaultValue="") String field,@RequestParam(required=false) Integer from,@RequestParam(required=false) Integer to,
        @RequestParam(defaultValue="real") String dataset,@RequestParam(defaultValue="year") String sort,
        @RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size,@RequestParam(required=false) Long revision) {
        var query=catalog.query(q,type,scholar,institution,field,from,to,dataset,sort,page,size,revision);
        return request.getRequestURI().endsWith("statistics")?catalog.stats(query):catalog.search(query);
    }
    @GetMapping("/works/{id}") Object detail(@PathVariable String id,@RequestParam(required=false) Long revision) {return catalog.detail(id,revision);}
    @GetMapping("/scholars") Object scholars(@RequestParam(defaultValue="") String q,@RequestParam(defaultValue="real") String dataset) {return catalog.scholars(q,dataset);}
    @GetMapping("/reference") Object reference() {return catalog.referenceData();}
}
