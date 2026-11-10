ALTER TABLE attachments ADD COLUMN file_kind TEXT CHECK(file_kind IS NULL OR file_kind IN ('contract','quality'));
CREATE TABLE project_files (
 project_id INTEGER NOT NULL REFERENCES projects(id),
 attachment_id INTEGER NOT NULL REFERENCES attachments(id),
 path TEXT NOT NULL,
 PRIMARY KEY(project_id,path)
);
CREATE INDEX project_files_attachment ON project_files(attachment_id,project_id);
CREATE TABLE file_operations (
 id TEXT PRIMARY KEY,
 state TEXT NOT NULL CHECK(state IN ('pending','applied','rolled_back')),
 moves_json TEXT NOT NULL CHECK(json_valid(moves_json)),
 created_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
