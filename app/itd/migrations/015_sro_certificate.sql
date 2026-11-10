-- Необязательные реквизиты свидетельства СРО организации.
ALTER TABLE organizations ADD COLUMN sro_certificate_num TEXT;
ALTER TABLE organizations ADD COLUMN sro_certificate_date TEXT;
