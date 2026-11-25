CREATE TABLE document_templates (
 code TEXT PRIMARY KEY REFERENCES document_types(code),
 form_set TEXT NOT NULL,
 original_name TEXT NOT NULL,
 revision INTEGER NOT NULL DEFAULT 1,
 deleted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE files (
 id TEXT PRIMARY KEY,
 project_id INTEGER NOT NULL REFERENCES projects(id),
 name TEXT NOT NULL,
 sha256 TEXT NOT NULL,
 act_id INTEGER REFERENCES acts(id),
 release_id INTEGER UNIQUE REFERENCES releases(id) ON DELETE CASCADE,
 attachment_id INTEGER REFERENCES attachments(id) ON DELETE CASCADE,
 UNIQUE(project_id,attachment_id)
);
CREATE TABLE removed_storage_files (id TEXT PRIMARY KEY, sha256 TEXT NOT NULL);
CREATE TRIGGER release_storage_file AFTER DELETE ON files
BEGIN
    INSERT OR IGNORE INTO removed_storage_files(id,sha256) VALUES(OLD.id,OLD.sha256);
END;
