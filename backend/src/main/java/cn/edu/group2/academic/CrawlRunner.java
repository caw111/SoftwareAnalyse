package cn.edu.group2.academic;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.*;
import org.springframework.context.annotation.Configuration;
import org.springframework.stereotype.Service;

@Configuration
@EnableScheduling
class CrawlScheduling {}

@Service
public class CrawlRunner {
    private final CrawlStore store;private final CrossrefClient client;private final boolean enabled;
    CrawlRunner(CrawlStore store,CrossrefClient client,@Value("${app.crawl.worker-enabled:true}") boolean enabled) {this.store=store;this.client=client;this.enabled=enabled;}
    @Scheduled(fixedDelayString="${app.crawl.poll-ms:2000}")
    public void tick() {
        if(!enabled) return;
        try {store.scheduleDue();executeOne();}
        catch(RuntimeException e) {org.slf4j.LoggerFactory.getLogger(CrawlRunner.class).warn("Crawl scheduler deferred: {}",e.getClass().getSimpleName());}
    }
    boolean executeOne() {
        var lease=store.claimNext();if(lease==null) return false;
        try {store.commit(lease,client.fetch(lease));}
        catch(CrawlFailure e) {store.fail(lease,e);}
        catch(ApiException e) {store.fail(lease,new CrawlFailure("PROCESSING_REJECTED","规范处理校验失败，原页面未提交："+e.getMessage(),false));}
        catch(RuntimeException e) {store.fail(lease,new CrawlFailure("PROCESSING_FAILURE","页面处理或数据库提交失败，将从已提交断点重试",true));}
        return true;
    }
}
