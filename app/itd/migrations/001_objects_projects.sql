CREATE TABLE objects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0)
);

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE RESTRICT,
    section_code TEXT NOT NULL CHECK (length(trim(section_code)) > 0),
    code TEXT NOT NULL CHECK (length(trim(code)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    city TEXT,
    smr_start TEXT,
    smr_end TEXT,
    pnr_start TEXT,
    pnr_end TEXT,
    UNIQUE (object_id, section_code),
    CHECK (smr_start IS NULL OR smr_end IS NULL OR smr_start <= smr_end),
    CHECK (pnr_start IS NULL OR pnr_end IS NULL OR pnr_start <= pnr_end)
);

CREATE INDEX projects_code_idx ON projects(code);
