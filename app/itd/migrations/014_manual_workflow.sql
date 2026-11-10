-- Общий ручной/агентный учёт. Прежние деловые значения не заполняются.
ALTER TABLE objects ADD COLUMN display_name TEXT;
CREATE TABLE object_units (
 id INTEGER PRIMARY KEY, object_id INTEGER NOT NULL REFERENCES objects(id),
 name TEXT NOT NULL, code TEXT, genplan_num TEXT
);
ALTER TABLE projects ADD COLUMN unit_id INTEGER REFERENCES object_units(id);
ALTER TABLE projects ADD COLUMN designer_org_id INTEGER REFERENCES organizations(id);
CREATE TABLE participant_periods (
 id INTEGER PRIMARY KEY, object_id INTEGER NOT NULL REFERENCES objects(id),
 org_id INTEGER NOT NULL REFERENCES organizations(id), active_from TEXT, active_to TEXT,
 basis TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
 UNIQUE(object_id,org_id), CHECK(active_from IS NULL OR active_to IS NULL OR active_from<=active_to)
);
CREATE TABLE supplies (
 id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
 resource_id INTEGER NOT NULL REFERENCES resources(id), source_key TEXT NOT NULL,
 batch_num TEXT, supply_date TEXT, quantity REAL CHECK(quantity IS NULL OR quantity>=0),
 unit TEXT NOT NULL, supplier TEXT, source TEXT NOT NULL,
 attachment_id INTEGER REFERENCES attachments(id),
 status TEXT NOT NULL CHECK(status IN ('pending','accepted','rejected','void')),
 note TEXT, revision INTEGER NOT NULL DEFAULT 1, UNIQUE(project_id,source_key)
);
CREATE TABLE act_materials (
 act_id INTEGER NOT NULL REFERENCES acts(id), supply_id INTEGER NOT NULL REFERENCES supplies(id),
 quantity REAL NOT NULL CHECK(quantity>0), PRIMARY KEY(act_id,supply_id)
);
ALTER TABLE workspace_entries ADD COLUMN work_type TEXT;
ALTER TABLE workspace_entries ADD COLUMN work_fields TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(work_fields) AND json_type(work_fields)='object');
CREATE TABLE act_entry_sources (
 act_id INTEGER NOT NULL REFERENCES acts(id), entry_id INTEGER NOT NULL REFERENCES workspace_entries(id),
 source_json TEXT NOT NULL, PRIMARY KEY(act_id,entry_id)
);
-- Фиксируем существующие связи, не подменяя содержание старых актов.
INSERT INTO act_entry_sources(act_id,entry_id,source_json)
SELECT act_id,id,json_object('revision',revision) FROM workspace_entries WHERE act_id IS NOT NULL;
CREATE TABLE act_journals (
 act_id INTEGER PRIMARY KEY REFERENCES acts(id), entry_kind TEXT NOT NULL,
 work_type TEXT, mapping TEXT NOT NULL CHECK(json_valid(mapping))
);
CREATE INDEX supplies_project ON supplies(project_id,resource_id);
