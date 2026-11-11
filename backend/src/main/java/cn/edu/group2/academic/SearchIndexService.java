package cn.edu.group2.academic;

import java.util.*;
import org.springframework.boot.*;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

@Service
@Order(0)
public class SearchIndexService implements ApplicationRunner {
    public static final String RULE_VERSION="weighted-bm25-v1";
    private final Db db;
    private final TransactionTemplate tx;
    public SearchIndexService(Db db,PlatformTransactionManager manager) {this.db=db;this.tx=new TransactionTemplate(manager);}
    /** Caller holds publication lock and transaction: a failed index never publishes new metadata. */
    public void index(String workId,long revision) {
        var row=db.one("SELECT * FROM work_revision WHERE id=? AND revision=?",workId,revision);
        var tf=new TreeMap<String,Double>();var textTerms=new HashSet<String>();
        add(tf,textTerms,Objects.toString(row.get("title"),""),4,true);
        add(tf,textTerms,Objects.toString(row.get("abstractText"),""),1,true);
        add(tf,textTerms,Objects.toString(row.get("venue"),""),2,false);
        add(tf,textTerms,Objects.toString(row.get("doi"),"")+" "+Objects.toString(row.get("identifier"),""),6,false);
        for(var person:db.rows("SELECT name FROM contributor_revision WHERE work_id=? AND revision=?",workId,revision)) add(tf,textTerms,person.get("name").toString(),2.5,false);
        for(var field:db.rows("SELECT field_name FROM work_field_revision WHERE work_id=? AND revision=?",workId,revision)) add(tf,textTerms,field.get("fieldName").toString(),2,false);
        double length=Math.max(1,tf.values().stream().mapToDouble(Double::doubleValue).sum());
        db.update("DELETE FROM search_term WHERE work_id=? AND revision=?",workId,revision);
        db.update("DELETE FROM search_document WHERE work_id=? AND revision=?",workId,revision);
        db.update("INSERT INTO search_document VALUES(?,?,?,?,?)",workId,revision,length,!textTerms.isEmpty(),RULE_VERSION+"/"+SearchTerms.VERSION);
        // JDBC batching bounds round-trips; all postings remain in the caller's transaction.
        var batch=tf.entrySet().stream().map(e->new Object[]{workId,revision,e.getKey(),e.getValue(),textTerms.contains(e.getKey())&&SearchTerms.isHotspot(e.getKey())}).toList();
        db.jdbc.batchUpdate("INSERT INTO search_term VALUES(?,?,?,?,?)",batch);
    }
    private static void add(Map<String,Double> tf,Set<String> textTerms,String value,double weight,boolean text) {
        for(String term:SearchTerms.tokens(value)) {tf.merge(term,weight,Double::sum);if(text)textTerms.add(term);}
    }
    @Override public void run(ApplicationArguments arguments) {
        // Migrated installations get a bounded, restartable index rebuild before readiness.
        while(Boolean.TRUE.equals(tx.execute(status->{
            db.one("SELECT revision FROM catalog_release WHERE id=1 FOR UPDATE");
            var missing=db.rows("SELECT w.id,w.revision FROM work_revision w WHERE NOT EXISTS(SELECT 1 FROM search_document d WHERE d.work_id=w.id AND d.revision=w.revision) ORDER BY w.revision,w.id LIMIT 100");
            for(var row:missing) index(row.get("id").toString(),((Number)row.get("revision")).longValue());
            return !missing.isEmpty();
        }))) { /* Each committed batch can be resumed by another replica. */ }
    }
    public record Ranking(String sql,List<Object> args) {}
    public Ranking ranking(long revision,boolean simulated,List<String> terms) {
        String marks=String.join(",",Collections.nCopies(terms.size(),"?"));
        String sql="""
            WITH corpus AS (
              SELECT d.work_id,d.revision,d.token_count FROM search_document d
              JOIN work_revision v ON v.id=d.work_id AND v.revision=d.revision
              WHERE v.revision<=? AND (v.valid_to IS NULL OR v.valid_to>?) AND v.simulated=?
            ), population AS (SELECT COUNT(*) AS n,COALESCE(AVG(token_count),1) AS avgdl FROM corpus),
            frequency AS (
              SELECT t.term,COUNT(*) AS df FROM search_term t JOIN corpus c ON c.work_id=t.work_id AND c.revision=t.revision
              WHERE t.term IN (%s) GROUP BY t.term
            ), relevance AS (
              SELECT t.work_id,t.revision,SUM(LN(1.0+(p.n-f.df+0.5)/(f.df+0.5)) *
                (t.weighted_tf*2.2)/(t.weighted_tf+1.2*(0.25+0.75*d.token_count/p.avgdl))) AS score
              FROM search_term t JOIN corpus d ON d.work_id=t.work_id AND d.revision=t.revision
              JOIN frequency f ON f.term=t.term CROSS JOIN population p
              GROUP BY t.work_id,t.revision HAVING COUNT(*)=?
            )
            """.formatted(marks);
        var args=new ArrayList<Object>(List.of(revision,revision,simulated));args.addAll(terms);args.add(terms.size());
        return new Ranking(sql,args);
    }
}
