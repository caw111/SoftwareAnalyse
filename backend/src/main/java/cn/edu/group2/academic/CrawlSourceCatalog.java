package cn.edu.group2.academic;

import java.net.URI;
import java.util.*;

/** Reviewed fixed source batches. User input never becomes a destination URL. */
final class CrawlSourceCatalog {
    record Batch(String id,String label,int year,String url,String contentType) {}
    record Source(String id,String name,String sourceName,String outcomeType,String scopeKind,String endpoint,List<Batch> batches) {
        boolean isCrossref() {return scopeKind.equals("CROSSREF_WINDOW");}
    }
    static final List<Source> SOURCES=List.of(
        new Source("crossref","Crossref 论文题录","Crossref","PAPER","CROSSREF_WINDOW","https://api.crossref.org/works",List.of()),
        new Source("cnipa-patents","国家知识产权局 · 专利金奖名单","CNIPA Patent Gold Award List","PATENT","REGISTERED_BATCH","https://www.cnipa.gov.cn/art/2025/6/5/art_552_199973.html",
            List.of(new Batch("cnipa-25-gold-2025","第二十五届中国专利金奖名单（授权日期待补）",2025,"https://www.cnipa.gov.cn/module/download/downfile.jsp?classid=0&showname=%E7%AC%AC%E4%BA%8C%E5%8D%81%E4%BA%94%E5%B1%8A%E4%B8%AD%E5%9B%BD%E4%B8%93%E5%88%A9%E9%87%91%E5%A5%96%E9%A1%B9%E7%9B%AE%E5%90%8D%E5%8D%95.pdf&filename=b712cad8dee344bc8322b4b45291fdf0.pdf","application/pdf"))),
        new Source("lynu-patents","洛阳师范学院 · 授权专利","LYNU Patent Grants","PATENT","REGISTERED_BATCH","https://sites.lynu.edu.cn/kycx/info/1221/5141.htm",
            List.of(new Batch("lynu-grants-2025","2025 年获得授权的专利清单",2025,"https://sites.lynu.edu.cn/kycx/info/1221/5141.htm","text/html"))),
        new Source("nsfc-projects","国家自然科学基金委 · 项目清单","NSFC Life Sciences Projects","PROJECT","REGISTERED_BATCH","https://www.nsfc.gov.cn/p1/2853/3102/72645.html",
            List.of(new Batch("nsfc-life-key-2019","2019 年生命科学部重点项目资助清单",2019,"https://www.nsfc.gov.cn/p1/2853/3102/72645.html","text/html"))),
        new Source("most-awards","科技部 · 国家自然科学奖","MOST National Natural Science Awards","AWARD","REGISTERED_BATCH","https://www.most.gov.cn/cxfw/kjjlcx/kjjl2023/202406/t20240624_191176.html",
            List.of(new Batch("most-natural-science-2023","2023 年度国家自然科学奖获奖项目目录",2023,"https://www.most.gov.cn/cxfw/kjjlcx/kjjl2023/202406/t20240624_191176.html","text/html")))
    );
    static Source source(String id) {return SOURCES.stream().filter(s->s.id().equals(id)).findFirst().orElseThrow(()->ApiException.bad("未登记的采集来源"));}
    static Batch batch(String sourceId,String id) {return source(sourceId).batches().stream().filter(b->b.id().equals(id)).findFirst().orElseThrow(()->ApiException.bad("请选择该来源已登记的公告批次"));}
    static void describe(Map<String,Object> row) {
        var s=source(row.get("id").toString());
        row.put("name",s.name());row.put("sourceName",s.sourceName());row.put("outcomeType",s.outcomeType());row.put("scopeKind",s.scopeKind());
        row.put("endpoint",s.endpoint());row.put("batches",s.batches());row.put("supportsIncremental",s.isCrossref());row.put("supportsSchedule",s.isCrossref());
    }
    static boolean allows(URI uri) {
        if(!"https".equals(uri.getScheme())||uri.getPort()!=-1||uri.getUserInfo()!=null||uri.getFragment()!=null) return false;
        return SOURCES.stream().filter(s->!s.isCrossref()).flatMap(s->s.batches().stream()).anyMatch(b->{
            URI registered=URI.create(b.url());
            return uri.equals(registered)||Objects.equals(uri.getHost(),registered.getHost())&&uri.getRawPath().equals("/robots.txt")&&uri.getRawQuery()==null;
        });
    }
    private CrawlSourceCatalog() {}
}
