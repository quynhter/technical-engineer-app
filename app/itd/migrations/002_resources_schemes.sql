CREATE TABLE resources (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    spec_num TEXT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    short_name TEXT,
    type_mark TEXT,
    category TEXT,
    serial_num TEXT,
    manufacturer TEXT,
    supplier TEXT,
    unit TEXT NOT NULL CHECK (length(trim(unit)) > 0),
    qty_proj REAL CHECK (qty_proj IS NULL OR qty_proj >= 0),
    qty_fact REAL CHECK (qty_fact IS NULL OR qty_fact >= 0),
    unit_weight REAL CHECK (unit_weight IS NULL OR unit_weight >= 0),
    note TEXT
);

CREATE INDEX resources_project_idx ON resources(project_id);

CREATE TABLE schemes (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    num TEXT NOT NULL CHECK (length(trim(num)) > 0),
    ref_code TEXT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    sheets_count INTEGER CHECK (sheets_count IS NULL OR sheets_count > 0),
    note TEXT
);

CREATE INDEX schemes_project_idx ON schemes(project_id);
