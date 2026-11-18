-- Keep source identities, published works, frozen documents, pages and audit history readable.
-- The source row lock serializes this cutover with workers' request/commit transactions.
UPDATE crawl_source SET enabled=FALSE,schedule_enabled=FALSE,config_version=config_version+1,
 lease_token=NULL,lease_until=NULL,next_schedule_at=0
 WHERE id='lynu-patents';

INSERT INTO crawl_task_log(task_id,attempt,action,before_state,after_state,message,created_at)
 SELECT id,attempt,'SOURCE_DEPRECATED',state,'STOPPED',
 'LYNU source retired; previously committed records and source evidence are preserved.',
 CAST(EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)*1000 AS BIGINT)
 FROM crawl_task WHERE source_id='lynu-patents' AND state IN ('PENDING','RUNNING','RETRYING');

UPDATE crawl_task SET state='STOPPED',runnable=FALSE,stop_requested=TRUE,version=version+1,
 lease_token=NULL,lease_until=NULL,error_code='SOURCE_DEPRECATED',completion_reason='SOURCE_DEPRECATED',
 error_message='LYNU source retired; existing records and audit history remain available.',
 updated_at=CAST(EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)*1000 AS BIGINT),
 completed_at=CAST(EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)*1000 AS BIGINT)
 WHERE source_id='lynu-patents' AND state IN ('PENDING','RUNNING','RETRYING');
