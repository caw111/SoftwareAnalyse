CREATE TABLE search_document (
 work_id VARCHAR(36) NOT NULL, revision BIGINT NOT NULL,
 token_count DOUBLE PRECISION NOT NULL, text_present BOOLEAN NOT NULL,
 rule_version VARCHAR(50) NOT NULL,
 PRIMARY KEY(work_id,revision),
 FOREIGN KEY(work_id,revision) REFERENCES work_revision(id,revision)
);
CREATE TABLE search_term (
 work_id VARCHAR(36) NOT NULL, revision BIGINT NOT NULL,
 term VARCHAR(120) NOT NULL, weighted_tf DOUBLE PRECISION NOT NULL,
 text_term BOOLEAN NOT NULL,
 PRIMARY KEY(work_id,revision,term),
 FOREIGN KEY(work_id,revision) REFERENCES search_document(work_id,revision)
);
CREATE INDEX search_term_lookup_idx ON search_term(term,work_id,revision);
