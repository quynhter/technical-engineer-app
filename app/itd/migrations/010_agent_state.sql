CREATE TABLE agent_state (
 id INTEGER PRIMARY KEY CHECK(id=1),
 project_id INTEGER NOT NULL REFERENCES projects(id)
);
