package cn.edu.group2.academic;

import org.springframework.stereotype.Component;

/** Called inside the import transaction, after the current record and all its relations are complete. */
@Component
public class CatalogRevisionStore {
    private final Db db;
    public CatalogRevisionStore(Db db) {this.db=db;}
    public void publish(String workId,long revision) {
        db.update("UPDATE work_revision SET valid_to=? WHERE id=? AND valid_to IS NULL AND revision<?",revision,workId,revision);
        db.update("""
            INSERT INTO work_revision(id,canonical_key,type,title,search_text,date_value,date_kind,date_precision,year,doi,
                identifier,identifier_type,authority,abstract_text,venue,citation_count,citation_source,oa_status,
                simulated,revision,created_at,details_json)
            SELECT id,canonical_key,type,title,search_text,date_value,date_kind,date_precision,year,doi,
                identifier,identifier_type,authority,abstract_text,venue,citation_count,citation_source,oa_status,
                simulated,revision,created_at,details_json FROM work WHERE id=? AND revision=?
            """,workId,revision);
        db.update("""
            INSERT INTO contributor_revision(work_id,revision,position,scholar_id,name,role,institution_id,orcid,raw_affiliations_json)
            SELECT work_id,?,position,scholar_id,name,role,institution_id,orcid,raw_affiliations_json FROM contributor WHERE work_id=?
            """,revision,workId);
        db.update("INSERT INTO work_institution_revision SELECT work_id,?,institution_id FROM work_institution WHERE work_id=?",revision,workId);
        db.update("INSERT INTO work_field_revision SELECT work_id,?,field_name FROM work_field WHERE work_id=?",revision,workId);
    }
}
