CREATE TABLE attachments (
    id INTEGER PRIMARY KEY,
    sha256 TEXT NOT NULL UNIQUE CHECK (length(sha256) = 64),
    storage_path TEXT NOT NULL UNIQUE,
    original_name TEXT NOT NULL,
    byte_size INTEGER NOT NULL CHECK (byte_size >= 0),
    doc_type TEXT NOT NULL CHECK (doc_type IN ('order', 'certificate', 'passport', 'rd', 'scheme', 'other')),
    title TEXT NOT NULL,
    doc_num TEXT,
    doc_date TEXT
);

CREATE TABLE organizations (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    short_name TEXT,
    ogrn TEXT, inn TEXT, address TEXT, phone TEXT, sro_info TEXT
);

CREATE TABLE signatories (
    id INTEGER PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    fio TEXT NOT NULL,
    last_name TEXT, first_name TEXT, middle_name TEXT,
    position TEXT NOT NULL,
    nrs_id TEXT,
    order_doc TEXT,
    order_attachment_id INTEGER REFERENCES attachments(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'Действует' CHECK (status IN ('Действует', 'Отозван')),
    note TEXT
);

CREATE TABLE organization_assignments (
    id INTEGER PRIMARY KEY,
    object_id INTEGER REFERENCES objects(id) ON DELETE RESTRICT,
    project_id INTEGER REFERENCES projects(id) ON DELETE RESTRICT,
    role_key TEXT NOT NULL,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    CHECK ((object_id IS NOT NULL) + (project_id IS NOT NULL) = 1)
);
CREATE UNIQUE INDEX org_role_object ON organization_assignments(object_id, role_key) WHERE object_id IS NOT NULL;
CREATE UNIQUE INDEX org_role_project ON organization_assignments(project_id, role_key) WHERE project_id IS NOT NULL;

CREATE TABLE signatory_assignments (
    id INTEGER PRIMARY KEY,
    object_id INTEGER REFERENCES objects(id) ON DELETE RESTRICT,
    project_id INTEGER REFERENCES projects(id) ON DELETE RESTRICT,
    role_key TEXT NOT NULL,
    signatory_id INTEGER NOT NULL REFERENCES signatories(id) ON DELETE RESTRICT,
    CHECK ((object_id IS NOT NULL) + (project_id IS NOT NULL) = 1)
);
CREATE UNIQUE INDEX signer_role_object ON signatory_assignments(object_id, role_key) WHERE object_id IS NOT NULL;
CREATE UNIQUE INDEX signer_role_project ON signatory_assignments(project_id, role_key) WHERE project_id IS NOT NULL;

CREATE TABLE object_attachments (
    object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE RESTRICT,
    attachment_id INTEGER NOT NULL REFERENCES attachments(id) ON DELETE RESTRICT,
    PRIMARY KEY (object_id, attachment_id)
);
CREATE TABLE project_attachments (
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    attachment_id INTEGER NOT NULL REFERENCES attachments(id) ON DELETE RESTRICT,
    PRIMARY KEY (project_id, attachment_id)
);
CREATE TABLE resource_attachments (
    resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE RESTRICT,
    attachment_id INTEGER NOT NULL REFERENCES attachments(id) ON DELETE RESTRICT,
    PRIMARY KEY (resource_id, attachment_id)
);
CREATE TABLE scheme_attachments (
    scheme_id INTEGER NOT NULL REFERENCES schemes(id) ON DELETE RESTRICT,
    attachment_id INTEGER NOT NULL REFERENCES attachments(id) ON DELETE RESTRICT,
    PRIMARY KEY (scheme_id, attachment_id)
);
CREATE TABLE act_attachments (
    act_id INTEGER NOT NULL REFERENCES acts(id) ON DELETE RESTRICT,
    attachment_id INTEGER NOT NULL REFERENCES attachments(id) ON DELETE RESTRICT,
    PRIMARY KEY (act_id, attachment_id)
);
