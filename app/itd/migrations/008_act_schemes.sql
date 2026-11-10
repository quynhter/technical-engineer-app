CREATE TABLE act_schemes (
    act_id INTEGER NOT NULL REFERENCES acts(id) ON DELETE CASCADE,
    scheme_id INTEGER NOT NULL REFERENCES schemes(id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    PRIMARY KEY (act_id, scheme_id),
    UNIQUE (act_id, ordinal)
);

CREATE TRIGGER act_schemes_same_project_insert
BEFORE INSERT ON act_schemes
WHEN (SELECT project_id FROM acts WHERE id = NEW.act_id)
  IS NOT (SELECT project_id FROM schemes WHERE id = NEW.scheme_id)
BEGIN
    SELECT RAISE(ABORT, 'Scheme and act must belong to the same project');
END;

CREATE TRIGGER act_schemes_same_project_update
BEFORE UPDATE ON act_schemes
WHEN (SELECT project_id FROM acts WHERE id = NEW.act_id)
  IS NOT (SELECT project_id FROM schemes WHERE id = NEW.scheme_id)
BEGIN
    SELECT RAISE(ABORT, 'Scheme and act must belong to the same project');
END;

CREATE TRIGGER schemes_keep_project
BEFORE UPDATE OF project_id ON schemes
WHEN EXISTS (SELECT 1 FROM act_schemes WHERE scheme_id = OLD.id)
 AND OLD.project_id != NEW.project_id
BEGIN
    SELECT RAISE(ABORT, 'Linked scheme cannot change project');
END;
