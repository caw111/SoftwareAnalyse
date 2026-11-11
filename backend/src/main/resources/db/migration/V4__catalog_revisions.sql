-- Public records keep a stable work ID; immutable content snapshots preserve old release queries.
ALTER TABLE work ADD COLUMN primary_source_name VARCHAR(200);
ALTER TABLE work ADD COLUMN primary_source_key VARCHAR(200);
ALTER TABLE work ADD COLUMN metadata_hash VARCHAR(64);
ALTER TABLE work ADD COLUMN source_updated_at BIGINT;
ALTER TABLE work ADD COLUMN metadata_locked BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE work SET primary_source_name=(SELECT s.source_name FROM source_record s WHERE s.work_id=work.id ORDER BY s.fetched_at,s.id LIMIT 1),
                primary_source_key=(SELECT s.source_key FROM source_record s WHERE s.work_id=work.id ORDER BY s.fetched_at,s.id LIMIT 1);
ALTER TABLE contributor ADD COLUMN orcid VARCHAR(80);
ALTER TABLE contributor ADD COLUMN raw_affiliations_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE source_record ADD COLUMN accepted BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE source_record ADD COLUMN source_updated_at BIGINT;
ALTER TABLE source_record ADD COLUMN normalized_json TEXT;
ALTER TABLE import_task ADD COLUMN updated INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_task ADD COLUMN unchanged INTEGER NOT NULL DEFAULT 0;
ALTER TABLE import_task ADD COLUMN conflicts INTEGER NOT NULL DEFAULT 0;
CREATE TABLE source_head (
 source_name VARCHAR(200) NOT NULL, source_key VARCHAR(200) NOT NULL,
 work_id VARCHAR(36) NOT NULL REFERENCES work(id), last_source_id VARCHAR(36) NOT NULL REFERENCES source_record(id),
 last_seen_at BIGINT NOT NULL,
 PRIMARY KEY(source_name,source_key)
);
INSERT INTO source_head(source_name,source_key,work_id,last_source_id,last_seen_at)
 SELECT source_name,source_key,work_id,id,fetched_at FROM
 (SELECT s.*,ROW_NUMBER() OVER(PARTITION BY source_name,source_key ORDER BY fetched_at DESC,id DESC) AS row_num FROM source_record s) ranked
 WHERE row_num=1;
CREATE TABLE metadata_conflict (
 id VARCHAR(36) PRIMARY KEY, work_id VARCHAR(36) NOT NULL REFERENCES work(id),
 source_id VARCHAR(36) NOT NULL REFERENCES source_record(id), base_revision BIGINT NOT NULL,
 reason VARCHAR(80) NOT NULL, state VARCHAR(20) NOT NULL DEFAULT 'OPEN', created_at BIGINT NOT NULL,
 UNIQUE(work_id,source_id,reason)
);
CREATE INDEX metadata_conflict_queue_idx ON metadata_conflict(state,created_at);
CREATE TABLE work_revision (
 id VARCHAR(36) NOT NULL REFERENCES work(id), canonical_key VARCHAR(500) NOT NULL,
 type VARCHAR(12) NOT NULL, title VARCHAR(1000) NOT NULL, search_text TEXT NOT NULL,
 date_value VARCHAR(10), date_kind VARCHAR(30) NOT NULL, date_precision VARCHAR(10), year INTEGER,
 doi VARCHAR(300), identifier VARCHAR(200), identifier_type VARCHAR(80), authority VARCHAR(200),
 abstract_text TEXT NOT NULL, venue VARCHAR(300) NOT NULL, citation_count INTEGER,
 citation_source VARCHAR(200), oa_status VARCHAR(20) NOT NULL, simulated BOOLEAN NOT NULL,
 revision BIGINT NOT NULL, created_at BIGINT NOT NULL, details_json TEXT NOT NULL,
 valid_to BIGINT, PRIMARY KEY(id,revision), CHECK(valid_to IS NULL OR valid_to>revision)
);
CREATE INDEX work_revision_filter_idx ON work_revision(simulated,type,year,revision,valid_to);
CREATE INDEX work_revision_valid_idx ON work_revision(revision,valid_to,id);
CREATE INDEX work_revision_doi_idx ON work_revision(doi,revision);
CREATE TABLE contributor_revision (
 work_id VARCHAR(36) NOT NULL, revision BIGINT NOT NULL, position INTEGER NOT NULL,
 scholar_id VARCHAR(80) REFERENCES scholar(id), name VARCHAR(100) NOT NULL, role VARCHAR(40) NOT NULL,
 institution_id VARCHAR(80) REFERENCES institution(id), orcid VARCHAR(80), raw_affiliations_json TEXT NOT NULL,
 PRIMARY KEY(work_id,revision,position), FOREIGN KEY(work_id,revision) REFERENCES work_revision(id,revision)
);
CREATE INDEX contributor_revision_scholar_idx ON contributor_revision(scholar_id,institution_id,work_id,revision);
CREATE TABLE work_institution_revision (
 work_id VARCHAR(36) NOT NULL, revision BIGINT NOT NULL, institution_id VARCHAR(80) NOT NULL REFERENCES institution(id),
 PRIMARY KEY(work_id,revision,institution_id), FOREIGN KEY(work_id,revision) REFERENCES work_revision(id,revision)
);
CREATE INDEX work_institution_revision_institution_idx ON work_institution_revision(institution_id,work_id,revision);
CREATE TABLE work_field_revision (
 work_id VARCHAR(36) NOT NULL, revision BIGINT NOT NULL, field_name VARCHAR(100) NOT NULL,
 PRIMARY KEY(work_id,revision,field_name), FOREIGN KEY(work_id,revision) REFERENCES work_revision(id,revision)
);
CREATE INDEX work_field_revision_name_idx ON work_field_revision(field_name,work_id,revision);
INSERT INTO work_revision(id,canonical_key,type,title,search_text,date_value,date_kind,date_precision,year,doi,identifier,identifier_type,authority,abstract_text,venue,citation_count,citation_source,oa_status,simulated,revision,created_at,details_json)
 SELECT id,canonical_key,type,title,search_text,date_value,date_kind,date_precision,year,doi,identifier,identifier_type,authority,abstract_text,venue,citation_count,citation_source,oa_status,simulated,revision,created_at,details_json FROM work;
INSERT INTO contributor_revision SELECT c.work_id,w.revision,c.position,c.scholar_id,c.name,c.role,c.institution_id,c.orcid,c.raw_affiliations_json FROM contributor c JOIN work w ON w.id=c.work_id;
INSERT INTO work_institution_revision SELECT wi.work_id,w.revision,wi.institution_id FROM work_institution wi JOIN work w ON w.id=wi.work_id;
INSERT INTO work_field_revision SELECT f.work_id,w.revision,f.field_name FROM work_field f JOIN work w ON w.id=f.work_id;

CREATE TABLE source_processing (
 id VARCHAR(36) PRIMARY KEY, source_id VARCHAR(36) NOT NULL REFERENCES source_record(id),
 parser_version VARCHAR(100) NOT NULL, rule_version VARCHAR(100) NOT NULL,
 normalized_hash VARCHAR(64) NOT NULL, normalized_json TEXT NOT NULL,
 result VARCHAR(30) NOT NULL, content_revision BIGINT NOT NULL, created_at BIGINT NOT NULL,
 UNIQUE(source_id,parser_version,rule_version,normalized_hash)
);
CREATE INDEX source_processing_source_idx ON source_processing(source_id,created_at);
