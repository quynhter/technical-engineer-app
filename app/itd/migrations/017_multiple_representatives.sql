-- Несколько представителей одной роли. Старые назначения сохраняются.
DROP INDEX signer_role_object;
DROP INDEX signer_role_project;
CREATE UNIQUE INDEX signer_role_object ON signatory_assignments(object_id, role_key, signatory_id) WHERE object_id IS NOT NULL;
CREATE UNIQUE INDEX signer_role_project ON signatory_assignments(project_id, role_key, signatory_id) WHERE project_id IS NOT NULL;
