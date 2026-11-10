-- Подтверждённый факт и согласованный состав комплекта, без изменения прежних записей.
CREATE TABLE work_facts (
 id INTEGER PRIMARY KEY,
 project_id INTEGER NOT NULL REFERENCES projects(id),
 resource_id INTEGER NOT NULL REFERENCES resources(id),
 source_key TEXT NOT NULL,
 location TEXT NOT NULL,
 work_description TEXT NOT NULL,
 quantity REAL CHECK(quantity IS NULL OR quantity>=0),
 unit TEXT NOT NULL,
 start_date TEXT,
 end_date TEXT,
 source TEXT NOT NULL,
 reported_by TEXT NOT NULL,
 attachment_id INTEGER REFERENCES attachments(id),
 status TEXT NOT NULL CHECK(status IN ('pending','confirmed','void')),
 void_reason TEXT,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 UNIQUE(project_id,source_key)
);
CREATE TABLE act_facts (
 act_id INTEGER NOT NULL REFERENCES acts(id),
 fact_id INTEGER NOT NULL REFERENCES work_facts(id),
 PRIMARY KEY(act_id,fact_id)
);
CREATE TABLE package_requirements (
 id INTEGER PRIMARY KEY,
 project_id INTEGER NOT NULL REFERENCES projects(id),
 title TEXT NOT NULL,
 work_scope TEXT NOT NULL,
 basis TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('act','attachment','scheme','xlsx')),
 act_type TEXT REFERENCES document_types(code),
 attachment_type TEXT CHECK(attachment_type IS NULL OR attachment_type IN ('order','certificate','passport','rd','scheme','other')),
 act_id INTEGER REFERENCES acts(id),
 attachment_id INTEGER REFERENCES attachments(id),
 scheme_id INTEGER REFERENCES schemes(id),
 release_id INTEGER REFERENCES releases(id),
 state TEXT NOT NULL DEFAULT 'required' CHECK(state IN ('required','not_applicable')),
 reason TEXT,
 CHECK(state!='not_applicable' OR length(trim(reason))>0)
);
CREATE TABLE quality_reviews (
 id INTEGER PRIMARY KEY,
 resource_id INTEGER NOT NULL REFERENCES resources(id),
 attachment_id INTEGER NOT NULL REFERENCES attachments(id),
 status TEXT NOT NULL CHECK(status IN ('matches','mismatch','uncertain')),
 checked_by TEXT NOT NULL,
 checked_date TEXT NOT NULL,
 source TEXT NOT NULL,
 note TEXT NOT NULL,
 resource_sha256 TEXT NOT NULL,
 attachment_sha256 TEXT NOT NULL
);
CREATE TABLE deliveries (
 id INTEGER PRIMARY KEY,
 project_id INTEGER NOT NULL REFERENCES projects(id),
 release_id INTEGER NOT NULL REFERENCES releases(id),
 recipient TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('sent','remarks','corrected','accepted')),
 revision INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE delivery_events (
 id INTEGER PRIMARY KEY,
 delivery_id INTEGER NOT NULL REFERENCES deliveries(id),
 release_id INTEGER NOT NULL REFERENCES releases(id),
 status TEXT NOT NULL CHECK(status IN ('sent','remarks','corrected','accepted')),
 event_date TEXT NOT NULL,
 source TEXT NOT NULL,
 note TEXT NOT NULL,
 revision INTEGER NOT NULL,
 UNIQUE(delivery_id,revision)
);
CREATE TABLE delivery_remarks (
 id INTEGER PRIMARY KEY,
 delivery_id INTEGER NOT NULL REFERENCES deliveries(id),
 release_id INTEGER NOT NULL REFERENCES releases(id),
 description TEXT NOT NULL,
 source TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','resolved')),
 resolution TEXT,
 resolution_source TEXT,
 resolution_date TEXT,
 resolution_release_id INTEGER REFERENCES releases(id)
);
CREATE INDEX work_facts_project ON work_facts(project_id,resource_id);
CREATE INDEX package_requirements_project ON package_requirements(project_id);
CREATE INDEX quality_reviews_resource ON quality_reviews(resource_id,attachment_id,id);
CREATE INDEX deliveries_project ON deliveries(project_id);
