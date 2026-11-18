ALTER TABLE audit_events ADD COLUMN actor_id TEXT;
ALTER TABLE audit_events ADD COLUMN actor_role TEXT;
ALTER TABLE audit_events ADD COLUMN source TEXT;
ALTER TABLE audit_events ADD COLUMN on_behalf_of TEXT;
ALTER TABLE audit_events ADD COLUMN result TEXT;
