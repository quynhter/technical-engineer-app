ALTER TABLE document_types ADD COLUMN filename_title TEXT;
ALTER TABLE acts ADD COLUMN filename_title TEXT;
ALTER TABLE projects ADD COLUMN form_set TEXT;
ALTER TABLE projects ADD COLUMN agent_context TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(agent_context));

CREATE TABLE releases (
 id INTEGER PRIMARY KEY,
 project_id INTEGER NOT NULL REFERENCES projects(id),
 act_id INTEGER REFERENCES acts(id),
 generated_id INTEGER UNIQUE REFERENCES generated_documents(id),
 kind TEXT NOT NULL CHECK(kind IN ('docx','xlsx')),
 title TEXT NOT NULL,
 path TEXT NOT NULL,
 sha256 TEXT NOT NULL,
 mode TEXT NOT NULL CHECK(mode IN ('draft','final')),
 selected INTEGER NOT NULL DEFAULT 0 CHECK(selected IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 sheets_count INTEGER CHECK(sheets_count IS NULL OR sheets_count>0)
);
CREATE UNIQUE INDEX releases_selected_act ON releases(act_id) WHERE selected=1 AND act_id IS NOT NULL;
CREATE UNIQUE INDEX releases_selected_xlsx ON releases(project_id) WHERE selected=1 AND kind='xlsx';
INSERT INTO releases(project_id,act_id,generated_id,kind,title,path,sha256,mode,selected,created_at)
 SELECT a.project_id,g.act_id,g.id,'docx',t.name,g.output_path,g.sha256,g.mode,
 g.id=(SELECT MAX(g2.id) FROM generated_documents g2 WHERE g2.act_id=g.act_id),g.generated_at
 FROM generated_documents g JOIN acts a ON a.id=g.act_id JOIN document_types t ON t.code=a.act_type;

CREATE TABLE release_operations (
 id INTEGER PRIMARY KEY,
 release_id INTEGER NOT NULL REFERENCES releases(id),
 old_path TEXT NOT NULL,
 new_path TEXT NOT NULL,
 sha256 TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('prepared','done','cancelled')),
 result TEXT,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE UNIQUE INDEX release_pending_move ON release_operations(release_id) WHERE state='prepared';
CREATE TABLE final_reviews (
 act_id INTEGER PRIMARY KEY REFERENCES acts(id),
 template_sha256 TEXT NOT NULL,
 context_sha256 TEXT NOT NULL,
 note TEXT NOT NULL
);
CREATE TABLE specification_pending (
 id INTEGER PRIMARY KEY,
 project_id INTEGER NOT NULL REFERENCES projects(id),
 attachment_id INTEGER NOT NULL REFERENCES attachments(id),
 source_key TEXT NOT NULL,
 item_json TEXT NOT NULL CHECK(json_valid(item_json)),
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','resolved')),
 UNIQUE(project_id,attachment_id,source_key)
);
