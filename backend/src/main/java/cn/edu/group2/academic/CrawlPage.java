package cn.edu.group2.academic;

import java.util.List;
import java.util.Map;

/** A bounded publication unit; a registered document is downloaded once and sliced from its frozen body. */
record CrawlPage(String url,String raw,int status,String etag,String lastModified,int received,
    List<ImportService.WorkInput> works,List<Map<String,Object>> exclusions,String nextCursor,boolean finished,
    CrawlDocument document) {
    CrawlPage(String url,String raw,int status,String etag,String lastModified,int received,
        List<ImportService.WorkInput> works,List<Map<String,Object>> exclusions,String nextCursor,boolean finished) {
        this(url,raw,status,etag,lastModified,received,works,exclusions,nextCursor,finished,null);
    }
}

record CrawlDocument(String url,String raw,String contentType,String bodyEncoding,String byteChecksum,
    int status,String etag,String lastModified,int recordCount,String parserVersion,long fetchedAt) {}
