CREATE TABLE bundled_document_templates (
 form_set TEXT NOT NULL,
 original_name TEXT NOT NULL,
 code TEXT NOT NULL REFERENCES document_templates(code),
 sha256 TEXT,
 revision INTEGER NOT NULL,
 PRIMARY KEY(form_set,original_name)
);
