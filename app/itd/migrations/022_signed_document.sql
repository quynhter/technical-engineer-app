-- Подписанный оригинал хранится отдельно от исходного бланка и выпуска DOCX.
ALTER TABLE document_versions ADD COLUMN signed_attachment_id INTEGER REFERENCES attachments(id);
