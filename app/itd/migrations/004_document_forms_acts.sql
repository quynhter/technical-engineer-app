CREATE TABLE document_types (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE CHECK (length(trim(code)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    fields TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(fields) AND json_type(fields) = 'array')
);

CREATE TABLE document_counters (
    project_id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE RESTRICT,
    last_number INTEGER NOT NULL CHECK (last_number >= 0)
);

CREATE TABLE acts (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    act_type TEXT NOT NULL REFERENCES document_types(code) ON DELETE RESTRICT,
    sequence_no INTEGER NOT NULL CHECK (sequence_no > 0),
    act_num TEXT NOT NULL,
    date_signed TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    fields TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(fields) AND json_type(fields) = 'array'),
    UNIQUE (project_id, sequence_no),
    UNIQUE (project_id, act_num)
);

CREATE INDEX acts_project_idx ON acts(project_id);

CREATE TABLE act_resources (
    act_id INTEGER NOT NULL REFERENCES acts(id) ON DELETE CASCADE,
    resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    PRIMARY KEY (act_id, resource_id),
    UNIQUE (act_id, ordinal)
);

CREATE TRIGGER act_resources_same_project_insert
BEFORE INSERT ON act_resources
WHEN (SELECT project_id FROM acts WHERE id = NEW.act_id)
  IS NOT (SELECT project_id FROM resources WHERE id = NEW.resource_id)
BEGIN
    SELECT RAISE(ABORT, 'Resource and act must belong to the same project');
END;

CREATE TRIGGER act_resources_same_project_update
BEFORE UPDATE ON act_resources
WHEN (SELECT project_id FROM acts WHERE id = NEW.act_id)
  IS NOT (SELECT project_id FROM resources WHERE id = NEW.resource_id)
BEGIN
    SELECT RAISE(ABORT, 'Resource and act must belong to the same project');
END;

CREATE TRIGGER resources_keep_project
BEFORE UPDATE OF project_id ON resources
WHEN EXISTS (SELECT 1 FROM act_resources WHERE resource_id = OLD.id)
 AND OLD.project_id != NEW.project_id
BEGIN
    SELECT RAISE(ABORT, 'Linked resource cannot change project');
END;

CREATE TRIGGER acts_keep_project
BEFORE UPDATE OF project_id ON acts
WHEN OLD.project_id != NEW.project_id
BEGIN
    SELECT RAISE(ABORT, 'Act cannot change project');
END;
