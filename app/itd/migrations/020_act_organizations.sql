-- Явный выбор организации для роли конкретного документа.
CREATE TABLE act_organizations (
 act_id INTEGER NOT NULL REFERENCES acts(id),
 role_key TEXT NOT NULL,
 org_id INTEGER NOT NULL REFERENCES organizations(id),
 PRIMARY KEY(act_id,role_key)
);
