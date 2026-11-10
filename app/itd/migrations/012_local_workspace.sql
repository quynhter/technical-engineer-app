ALTER TABLE objects ADD COLUMN construction_type TEXT;
ALTER TABLE objects ADD COLUMN address TEXT;
ALTER TABLE objects ADD COLUMN permit_num TEXT;
ALTER TABLE objects ADD COLUMN permit_date TEXT;
ALTER TABLE objects ADD COLUMN permit_authority TEXT;
ALTER TABLE objects ADD COLUMN expertise_num TEXT;
ALTER TABLE objects ADD COLUMN expertise_date TEXT;
ALTER TABLE objects ADD COLUMN expertise_authority TEXT;
ALTER TABLE objects ADD COLUMN work_start TEXT;
ALTER TABLE objects ADD COLUMN work_end TEXT;
ALTER TABLE objects ADD COLUMN gsn_case TEXT;
ALTER TABLE objects ADD COLUMN developer_functions TEXT;
ALTER TABLE objects ADD COLUMN control_self INTEGER NOT NULL DEFAULT 0 CHECK(control_self IN (0,1));
ALTER TABLE objects ADD COLUMN control_external INTEGER NOT NULL DEFAULT 0 CHECK(control_external IN (0,1));
ALTER TABLE objects ADD COLUMN author_supervision INTEGER NOT NULL DEFAULT 0 CHECK(author_supervision IN (0,1));
ALTER TABLE organizations ADD COLUMN postal_code TEXT;
ALTER TABLE organizations ADD COLUMN email TEXT;
ALTER TABLE organizations ADD COLUMN sro_ogrn TEXT;
ALTER TABLE organizations ADD COLUMN sro_inn TEXT;
ALTER TABLE signatories ADD COLUMN email TEXT;
ALTER TABLE signatories ADD COLUMN authority_type TEXT;
ALTER TABLE signatories ADD COLUMN authority_num TEXT;
ALTER TABLE signatories ADD COLUMN authority_date TEXT;

CREATE TABLE object_participants (
    id INTEGER PRIMARY KEY,
    object_id INTEGER NOT NULL REFERENCES objects(id),
    org_id INTEGER NOT NULL REFERENCES organizations(id),
    role_key TEXT NOT NULL,
    UNIQUE(object_id, org_id, role_key)
);
INSERT INTO object_participants(object_id, org_id, role_key)
SELECT object_id, org_id, role_key FROM organization_assignments WHERE object_id IS NOT NULL;

CREATE TABLE workspace_entries (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    kind TEXT NOT NULL CHECK(kind IN ('work','incoming','journal')),
    entry_date TEXT,
    title TEXT NOT NULL CHECK(length(trim(title)) > 0),
    details TEXT,
    conditions TEXT,
    responsible TEXT,
    resource_id INTEGER REFERENCES resources(id),
    attachment_id INTEGER REFERENCES attachments(id),
    act_id INTEGER REFERENCES acts(id),
    quantity REAL CHECK(quantity IS NULL OR quantity >= 0),
    unit TEXT,
    revision INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX workspace_entries_project ON workspace_entries(project_id, kind);
