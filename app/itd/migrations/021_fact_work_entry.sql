ALTER TABLE work_facts ADD COLUMN work_entry_id INTEGER REFERENCES workspace_entries(id) ON DELETE SET NULL;
