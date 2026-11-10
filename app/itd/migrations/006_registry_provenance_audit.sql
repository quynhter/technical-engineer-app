ALTER TABLE document_types ADD COLUMN form_group TEXT NOT NULL DEFAULT 'act' CHECK (form_group IN ('act', 'statement', 'registry'));
ALTER TABLE acts ADD COLUMN sheets_count INTEGER CHECK (sheets_count IS NULL OR sheets_count > 0);
ALTER TABLE acts ADD COLUMN registry_note TEXT;
ALTER TABLE attachments ADD COLUMN sheets_count INTEGER CHECK (sheets_count IS NULL OR sheets_count > 0);
ALTER TABLE attachments ADD COLUMN note TEXT;

CREATE TABLE audit_events (
    id INTEGER PRIMARY KEY,
    occurred_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    operation TEXT NOT NULL,
    entity TEXT,
    entity_id INTEGER,
    before_json TEXT,
    after_json TEXT
);

CREATE TABLE resource_sources (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE RESTRICT,
    attachment_id INTEGER NOT NULL REFERENCES attachments(id) ON DELETE RESTRICT,
    source_key TEXT NOT NULL,
    page INTEGER CHECK (page IS NULL OR page > 0),
    sheet TEXT,
    locator TEXT,
    UNIQUE (project_id, attachment_id, source_key)
);

CREATE TABLE generated_documents (
    id INTEGER PRIMARY KEY,
    act_id INTEGER NOT NULL REFERENCES acts(id) ON DELETE RESTRICT,
    output_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    generated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    mode TEXT NOT NULL CHECK (mode IN ('draft', 'final')),
    context_json TEXT NOT NULL CHECK (json_valid(context_json)),
    template_sha256 TEXT NOT NULL
);
