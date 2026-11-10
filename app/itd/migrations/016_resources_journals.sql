-- Единый расход работ, справочники ОЖР и явное подтверждение подписания.
CREATE TABLE work_materials (
 entry_id INTEGER NOT NULL REFERENCES workspace_entries(id),
 resource_id INTEGER NOT NULL REFERENCES resources(id),
 quantity REAL NOT NULL CHECK(quantity>0), unit TEXT NOT NULL,
 fact_id INTEGER NOT NULL REFERENCES work_facts(id),
 PRIMARY KEY(entry_id,resource_id)
);
CREATE TABLE work_material_allocations (
 entry_id INTEGER NOT NULL, resource_id INTEGER NOT NULL,
 supply_id INTEGER NOT NULL REFERENCES supplies(id),
 quantity REAL NOT NULL CHECK(quantity>0),
 PRIMARY KEY(entry_id,resource_id,supply_id),
 FOREIGN KEY(entry_id,resource_id) REFERENCES work_materials(entry_id,resource_id) ON DELETE CASCADE
);
ALTER TABLE workspace_entries ADD COLUMN responsible_id INTEGER REFERENCES signatories(id);
CREATE TABLE special_journals (
 id INTEGER PRIMARY KEY, object_id INTEGER NOT NULL REFERENCES objects(id),
 project_id INTEGER NOT NULL REFERENCES projects(id), name TEXT NOT NULL,
 act_id INTEGER UNIQUE REFERENCES acts(id),
 issued_date TEXT, org_id INTEGER REFERENCES organizations(id),
 keeper_id INTEGER REFERENCES signatories(id), transfer_date TEXT,
 recipient_id INTEGER REFERENCES signatories(id), note TEXT,
 revision INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE act_signatories (
 act_id INTEGER NOT NULL REFERENCES acts(id), role_key TEXT NOT NULL,
 signatory_id INTEGER NOT NULL REFERENCES signatories(id),
 PRIMARY KEY(act_id,role_key)
);
CREATE TABLE act_execution_status (
 act_id INTEGER PRIMARY KEY REFERENCES acts(id),
 state TEXT NOT NULL CHECK(state IN ('draft','signed')),
 work_description TEXT NOT NULL, basis TEXT NOT NULL,
 signers_json TEXT NOT NULL CHECK(json_valid(signers_json)),
 signed_date TEXT, revision INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE resource_imports (
 id TEXT PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
 filename TEXT NOT NULL, sha256 TEXT NOT NULL, content BLOB NOT NULL,
 attachment_id INTEGER REFERENCES attachments(id)
);
CREATE TABLE resource_import_rows (
 project_id INTEGER NOT NULL REFERENCES projects(id), sha256 TEXT NOT NULL,
 sheet TEXT NOT NULL, header_row INTEGER NOT NULL, row_num INTEGER NOT NULL,
 resource_id INTEGER NOT NULL REFERENCES resources(id),
 data_json TEXT NOT NULL CHECK(json_valid(data_json)),
 PRIMARY KEY(project_id,sha256,sheet,header_row,row_num)
);
CREATE INDEX work_materials_resource ON work_materials(resource_id);
CREATE INDEX special_journals_object ON special_journals(object_id);
CREATE UNIQUE INDEX resource_import_same_source_row ON resource_import_rows(project_id,sha256,sheet,row_num);
