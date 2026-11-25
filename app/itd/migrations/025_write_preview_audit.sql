ALTER TABLE audit_events ADD COLUMN preview_id TEXT;
ALTER TABLE audit_events ADD COLUMN knowledge_version TEXT;
ALTER TABLE audit_events ADD COLUMN skills_version TEXT;
ALTER TABLE audit_events ADD COLUMN index_status TEXT;
CREATE UNIQUE INDEX audit_events_preview_once ON audit_events(preview_id) WHERE preview_id IS NOT NULL;
