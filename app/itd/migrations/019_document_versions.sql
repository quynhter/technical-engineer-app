-- Самостоятельные карточки версий, снимки подписантов и связь с точным файлом.
CREATE TABLE document_versions (
 id INTEGER PRIMARY KEY,
 act_id INTEGER NOT NULL REFERENCES acts(id),
 ordinal INTEGER NOT NULL CHECK(ordinal>0),
 card_json TEXT NOT NULL CHECK(json_valid(card_json)),
 signers_json TEXT NOT NULL CHECK(json_valid(signers_json)),
 release_id INTEGER REFERENCES releases(id),
 attachment_id INTEGER REFERENCES attachments(id),
 snapshot_json TEXT CHECK(snapshot_json IS NULL OR json_valid(snapshot_json)),
 revision INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 UNIQUE(act_id,ordinal)
);
