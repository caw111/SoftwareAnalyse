INSERT INTO crawl_source(id,name,min_interval_ms) VALUES('cnipa-patents','国家知识产权局专利金奖名单',2000);
INSERT INTO crawl_source(id,name,min_interval_ms) VALUES('lynu-patents','洛阳师范学院授权专利',2000);
INSERT INTO crawl_source(id,name,min_interval_ms) VALUES('nsfc-projects','国家自然科学基金委项目清单',2000);
INSERT INTO crawl_source(id,name,min_interval_ms) VALUES('most-awards','科技部国家自然科学奖',2000);

ALTER TABLE crawl_task ADD COLUMN batch_id VARCHAR(80);

-- A fixed input snapshot per task: resuming never mixes different editions of a listing.
CREATE TABLE crawl_document (
 task_id VARCHAR(36) PRIMARY KEY REFERENCES crawl_task(id),
 request_url TEXT NOT NULL, raw_body TEXT NOT NULL,
 content_type VARCHAR(100) NOT NULL, body_encoding VARCHAR(20) NOT NULL,
 response_checksum VARCHAR(64) NOT NULL, byte_checksum VARCHAR(64) NOT NULL,
 http_status INTEGER NOT NULL, etag VARCHAR(1000), last_modified VARCHAR(200),
 record_count INTEGER NOT NULL, parser_version VARCHAR(100) NOT NULL, fetched_at BIGINT NOT NULL
);
