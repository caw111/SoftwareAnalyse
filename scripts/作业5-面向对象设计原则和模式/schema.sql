-- 学术成果分享平台目标数据库设计模型。独立 PostgreSQL 空库使用。
BEGIN;
CREATE TABLE app_user (
  id uuid PRIMARY KEY, username varchar(80) UNIQUE NOT NULL, password_hash text NOT NULL,
  role varchar(12) NOT NULL CHECK (role IN ('USER','RESEARCHER','ADMIN')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE institution (
  id uuid PRIMARY KEY, name varchar(200) NOT NULL, ror varchar(64) UNIQUE
);
CREATE INDEX institution_name_idx ON institution(name);
CREATE TABLE scholar (
  id uuid PRIMARY KEY, name varchar(100) NOT NULL, orcid varchar(19),
  institution_id uuid REFERENCES institution, public_profile jsonb NOT NULL DEFAULT '{}',
  dataset varchar(4) NOT NULL CHECK (dataset IN ('real','demo')),
  UNIQUE(dataset, orcid)
);
CREATE INDEX scholar_name_idx ON scholar(dataset,name);
CREATE INDEX scholar_institution_idx ON scholar(institution_id);
CREATE TABLE discipline (
  id varchar(40) PRIMARY KEY, name varchar(100) NOT NULL,
  parent_id varchar(40) REFERENCES discipline CHECK (parent_id <> id)
);
CREATE INDEX discipline_parent_idx ON discipline(parent_id);
CREATE TABLE work (
  id uuid PRIMARY KEY, dataset varchar(4) NOT NULL CHECK (dataset IN ('real','demo')),
  type varchar(8) NOT NULL CHECK (type IN ('PAPER','PATENT','PROJECT','AWARD')),
  canonical_key varchar(500) NOT NULL, blocked_at timestamptz,
  UNIQUE(dataset,canonical_key)
);
CREATE INDEX work_dataset_type_idx ON work(dataset,type);
CREATE TABLE work_revision (
  work_id uuid NOT NULL REFERENCES work, valid_from bigint NOT NULL CHECK (valid_from >= 1),
  valid_to bigint CHECK (valid_to > valid_from),
  title varchar(1000) NOT NULL CHECK (length(btrim(title)) > 0), abstract_text text,
  publish_year smallint CHECK (publish_year BETWEEN 1000 AND 9999),
  date_value varchar(10), date_kind varchar(30), date_precision varchar(5),
  citation_count int CHECK (citation_count >= 0), citation_source varchar(120),
  details jsonb NOT NULL CHECK (jsonb_typeof(details) = 'object'),
  PRIMARY KEY(work_id,valid_from),
  CHECK (
    (date_value IS NULL AND date_kind IS NULL AND date_precision IS NULL AND publish_year IS NULL)
    OR (
      date_value IS NOT NULL AND date_kind IS NOT NULL AND date_precision IS NOT NULL AND publish_year IS NOT NULL
      AND left(date_value,4) = publish_year::text
      AND CASE date_precision
            WHEN 'YEAR' THEN date_value ~ '^[0-9]{4}$'
            WHEN 'MONTH' THEN date_value ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'
            WHEN 'DAY' THEN date_value ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$'
            ELSE FALSE
          END
    )
  )
);
-- btree_gist 提供 uuid 等值比较，与版本区间 GiST 联合排斥。
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE work_revision ADD CONSTRAINT work_revision_no_overlap
  EXCLUDE USING gist (work_id WITH =, int8range(valid_from,valid_to,'[)') WITH &&);
CREATE UNIQUE INDEX work_revision_current_idx ON work_revision(work_id) WHERE valid_to IS NULL;
CREATE INDEX work_revision_year_idx ON work_revision(publish_year,valid_from,valid_to);
CREATE TABLE work_scholar (
  work_id uuid NOT NULL, valid_from bigint NOT NULL, position int NOT NULL CHECK(position > 0),
  scholar_id uuid REFERENCES scholar, contributor_name varchar(100) NOT NULL,
  role varchar(20) NOT NULL CHECK (role IN ('AUTHOR','INVENTOR','PI','AWARDEE','MEMBER')),
  institution_id uuid REFERENCES institution,
  PRIMARY KEY(work_id,valid_from,position),
  FOREIGN KEY(work_id,valid_from) REFERENCES work_revision
);
CREATE INDEX work_scholar_filter_idx ON work_scholar(scholar_id,institution_id,work_id,valid_from);
CREATE INDEX work_scholar_institution_idx ON work_scholar(institution_id,work_id,valid_from);
CREATE TABLE work_discipline (
  work_id uuid NOT NULL, valid_from bigint NOT NULL, discipline_id varchar(40) NOT NULL REFERENCES discipline,
  PRIMARY KEY(work_id,valid_from,discipline_id),
  FOREIGN KEY(work_id,valid_from) REFERENCES work_revision
);
CREATE INDEX work_discipline_filter_idx ON work_discipline(discipline_id,work_id,valid_from);
CREATE TABLE work_institution (
  work_id uuid NOT NULL, valid_from bigint NOT NULL, institution_id uuid NOT NULL REFERENCES institution,
  PRIMARY KEY(work_id,valid_from,institution_id),
  FOREIGN KEY(work_id,valid_from) REFERENCES work_revision
);
CREATE INDEX work_institution_filter_idx ON work_institution(institution_id,work_id,valid_from);
CREATE TABLE claim (
  id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES app_user,
  target_scholar_id uuid NOT NULL REFERENCES scholar,
  state varchar(24) NOT NULL CHECK (state IN ('DRAFT','PENDING_VERIFICATION','VERIFYING','PENDING_REVIEW',
    'UNDER_REVIEW','NEED_MORE_INFO','APPROVED','REJECTED','WITHDRAWN')),
  version int NOT NULL DEFAULT 0 CHECK (version >= 0),
  material_version int NOT NULL DEFAULT 0 CHECK (material_version >= 0),
  reviewer_id uuid REFERENCES app_user, lease_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (state <> 'UNDER_REVIEW' OR (reviewer_id IS NOT NULL AND lease_until IS NOT NULL))
);
CREATE UNIQUE INDEX claim_open_idx ON claim(user_id,target_scholar_id)
  WHERE state NOT IN ('APPROVED','REJECTED','WITHDRAWN');
CREATE INDEX claim_user_idx ON claim(user_id,created_at DESC,id);
CREATE INDEX claim_queue_idx ON claim(state,created_at,id);
CREATE TABLE portal_binding (
  user_id uuid PRIMARY KEY REFERENCES app_user, scholar_id uuid UNIQUE NOT NULL REFERENCES scholar,
  claim_id uuid UNIQUE NOT NULL REFERENCES claim
);
CREATE TABLE source_watermark (
  source_code varchar(40) NOT NULL, scope_key varchar(100) NOT NULL,
  synced_through timestamptz NOT NULL, PRIMARY KEY(source_code,scope_key)
);
CREATE TABLE crawl_task (
  id uuid PRIMARY KEY, source_code varchar(40) NOT NULL, scope_key varchar(100) NOT NULL,
  created_by uuid NOT NULL REFERENCES app_user, idempotency_key varchar(100) NOT NULL,
  request_hash char(64) NOT NULL, repeated_from uuid REFERENCES crawl_task,
  window_start timestamptz NOT NULL, window_end timestamptz NOT NULL CHECK (window_end > window_start),
  rule_version varchar(40) NOT NULL, cursor text, attempt_no int NOT NULL DEFAULT 0 CHECK (attempt_no >= 0),
  lease_token uuid, lease_until timestamptz, next_run_at timestamptz NOT NULL DEFAULT now(),
  state varchar(10) NOT NULL CHECK (state IN ('PENDING','RUNNING','SUCCESS','FAILED','RETRYING','STOPPED')),
  stop_requested boolean NOT NULL DEFAULT false, fetched_pages int NOT NULL DEFAULT 0 CHECK (fetched_pages >= 0),
  processed_records int NOT NULL DEFAULT 0 CHECK (processed_records >= 0),
  failed_records int NOT NULL DEFAULT 0 CHECK (failed_records >= 0),
  last_error text, completed_fact_version bigint, created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(created_by,idempotency_key),
  CHECK (state <> 'RUNNING' OR (lease_token IS NOT NULL AND lease_until IS NOT NULL))
);
CREATE INDEX crawl_runnable_idx ON crawl_task(state,next_run_at,id) WHERE state IN ('PENDING','RETRYING');
CREATE INDEX crawl_expired_lease_idx ON crawl_task(lease_until) WHERE state='RUNNING';
CREATE INDEX crawl_source_idx ON crawl_task(source_code,created_at DESC);
CREATE TABLE crawl_page (
  task_id uuid NOT NULL REFERENCES crawl_task, page_no int NOT NULL CHECK(page_no >= 0),
  raw_object_key text NOT NULL, checksum char(64) NOT NULL, next_cursor text,
  processed_at timestamptz, PRIMARY KEY(task_id,page_no)
);
CREATE TABLE source_snapshot (
  id uuid PRIMARY KEY, source_code varchar(40) NOT NULL, source_key varchar(200) NOT NULL,
  checksum char(64) NOT NULL, source_url text, raw_object_key text NOT NULL,
  fetched_at timestamptz NOT NULL, UNIQUE(source_code,source_key,checksum)
);
CREATE TABLE source_observation (
  task_id uuid NOT NULL, page_no int NOT NULL, snapshot_id uuid NOT NULL REFERENCES source_snapshot,
  work_id uuid, valid_from bigint, rule_version varchar(40) NOT NULL,
  PRIMARY KEY(task_id,page_no,snapshot_id),
  FOREIGN KEY(task_id,page_no) REFERENCES crawl_page,
  FOREIGN KEY(work_id,valid_from) REFERENCES work_revision MATCH FULL
);
CREATE INDEX source_observation_work_idx ON source_observation(work_id,valid_from);
CREATE TABLE audit_log (
  id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  actor_id uuid REFERENCES app_user, object_type varchar(30) NOT NULL, object_id uuid NOT NULL,
  action varchar(30) NOT NULL, before_state varchar(24), after_state varchar(24),
  reason text, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_object_idx ON audit_log(object_type,object_id,created_at,id);
CREATE TABLE fact_clock (id int PRIMARY KEY CHECK (id = 1), version bigint NOT NULL CHECK (version >= 0));
INSERT INTO fact_clock VALUES (1,0);
CREATE TABLE outbox_event (
  id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, fact_version bigint NOT NULL,
  event_type varchar(30) NOT NULL, object_id uuid NOT NULL, payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(), published_at timestamptz,
  UNIQUE(fact_version,event_type,object_id)
);
CREATE INDEX outbox_pending_idx ON outbox_event(fact_version,id) WHERE published_at IS NULL;
CREATE TABLE public_release (
  revision bigint PRIMARY KEY, fact_cutoff bigint NOT NULL, es_index varchar(80) UNIQUE NOT NULL,
  state varchar(10) NOT NULL CHECK(state IN ('BUILDING','READY','FAILED','RETIRED')),
  created_at timestamptz NOT NULL DEFAULT now(), ready_at timestamptz, retires_at timestamptz
);
CREATE TABLE release_pointer (
  id int PRIMARY KEY CHECK (id=1), revision bigint NOT NULL REFERENCES public_release
);
CREATE TABLE stat_bucket (
  revision bigint NOT NULL REFERENCES public_release,
  dataset varchar(4) NOT NULL CHECK (dataset IN ('real','demo')),
  dimension varchar(30) NOT NULL, bucket_key varchar(160) NOT NULL,
  work_count bigint NOT NULL CHECK (work_count >= 0),
  denominator bigint NOT NULL CHECK (denominator >= work_count),
  PRIMARY KEY(revision,dataset,dimension,bucket_key)
);
CREATE TABLE coauthor_edge (
  revision bigint NOT NULL REFERENCES public_release,
  dataset varchar(4) NOT NULL CHECK (dataset IN ('real','demo')),
  scholar_low uuid NOT NULL REFERENCES scholar, scholar_high uuid NOT NULL REFERENCES scholar,
  evidence_work_ids uuid[] NOT NULL, paper_count int NOT NULL CHECK (paper_count > 0),
  CHECK (scholar_low < scholar_high),
  PRIMARY KEY(revision,dataset,scholar_low,scholar_high)
);
CREATE INDEX coauthor_reverse_idx ON coauthor_edge(revision,dataset,scholar_high);
CREATE TABLE portal_snapshot (
  revision bigint NOT NULL REFERENCES public_release,
  scholar_id uuid NOT NULL REFERENCES scholar,
  display_name varchar(100) NOT NULL, institution_label varchar(200),
  profile jsonb NOT NULL CHECK (jsonb_typeof(profile)='object'),
  PRIMARY KEY(revision,scholar_id)
);
CREATE TABLE claim_evidence (
  id uuid PRIMARY KEY, claim_id uuid NOT NULL REFERENCES claim, uploader_id uuid NOT NULL REFERENCES app_user,
  object_key text NOT NULL UNIQUE, checksum char(64) NOT NULL, expires_at timestamptz NOT NULL,
  scan_state varchar(12) NOT NULL CHECK (scan_state IN ('PASSED','REJECTED')),
  UNIQUE(claim_id,id)
);
CREATE TABLE claim_material (
  claim_id uuid NOT NULL REFERENCES claim,
  material_version int NOT NULL CHECK (material_version > 0),
  evidence_id uuid NOT NULL,
  submitted_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(claim_id, material_version),
  FOREIGN KEY(claim_id,evidence_id) REFERENCES claim_evidence(claim_id,id)
);
CREATE TABLE quality_case (
  id uuid PRIMARY KEY, snapshot_id uuid NOT NULL REFERENCES source_snapshot,
  rule_version varchar(40) NOT NULL, kind varchar(20) NOT NULL,
  candidate_work_id uuid REFERENCES work, reasons jsonb NOT NULL,
  state varchar(10) NOT NULL CHECK(state IN ('OPEN','RESOLVED')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX quality_open_idx ON quality_case(created_at,id) WHERE state='OPEN';
COMMIT;
