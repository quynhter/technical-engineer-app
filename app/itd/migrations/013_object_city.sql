-- Город объекта хранится отдельно от реквизитов раздела.
ALTER TABLE objects ADD COLUMN city TEXT;
