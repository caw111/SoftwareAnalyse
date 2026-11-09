ALTER TABLE app_user ADD COLUMN orcid VARCHAR(19) NOT NULL DEFAULT '';
ALTER TABLE app_user ADD COLUMN websites_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE app_user ADD COLUMN about_me TEXT NOT NULL DEFAULT '';
ALTER TABLE app_user ADD COLUMN profile_version INTEGER NOT NULL DEFAULT 0 CHECK (profile_version >= 0);
CREATE INDEX claim_user_updated_idx ON claim(user_id,updated_at,id);
CREATE INDEX claim_updated_idx ON claim(updated_at,id);
