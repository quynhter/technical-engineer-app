ALTER TABLE signatories ADD COLUMN short_fio TEXT NOT NULL DEFAULT '';

CREATE TRIGGER signatories_sync_names
AFTER UPDATE OF fio, last_name, first_name, middle_name ON signatories
BEGIN
    -- Старые клиенты могут передать ФИО явно. При правке только частей обновляем его здесь.
    UPDATE signatories
    SET fio = trim(
        coalesce(nullif(trim(NEW.last_name), '') || ' ', '') ||
        coalesce(nullif(trim(NEW.first_name), '') || ' ', '') ||
        coalesce(trim(NEW.middle_name), '')
    )
    WHERE id = NEW.id AND NEW.fio IS OLD.fio
      AND (NEW.last_name IS NOT OLD.last_name OR NEW.first_name IS NOT OLD.first_name
           OR NEW.middle_name IS NOT OLD.middle_name)
      AND coalesce(nullif(trim(NEW.last_name), ''), nullif(trim(NEW.first_name), ''),
                   nullif(trim(NEW.middle_name), '')) IS NOT NULL;

    -- Если отдельные части не заполнены, сокращаем прежнее ФИО в порядке «фамилия имя отчество».
    UPDATE signatories
    SET short_fio = (
        WITH RECURSIVE parts(n, name, rest) AS (
            SELECT 0, '', trim(replace(replace(replace(signatories.fio, char(9), ' '), char(10), ' '), char(13), ' '))
            WHERE coalesce(nullif(trim(last_name), ''), nullif(trim(first_name), ''),
                           nullif(trim(middle_name), '')) IS NULL
            UNION ALL
            SELECT n + 1, substr(rest, 1, instr(rest || ' ', ' ') - 1),
                   ltrim(substr(rest, instr(rest || ' ', ' ') + 1))
            FROM parts WHERE n < 3 AND rest <> ''
        ),
        names(last, first, middle) AS (
            SELECT coalesce(nullif(trim(last_name), ''), max(CASE n WHEN 1 THEN name END)),
                   coalesce(nullif(trim(first_name), ''), max(CASE n WHEN 2 THEN name END)),
                   coalesce(nullif(trim(middle_name), ''), max(CASE n WHEN 3 THEN name END))
            FROM parts
        )
        SELECT trim(coalesce(last, '') ||
                    coalesce(' ' || substr(first, 1, 1) || '.', '') ||
                    coalesce(' ' || substr(middle, 1, 1) || '.', ''))
        FROM names
    )
    WHERE id = NEW.id;
END;

CREATE TRIGGER signatories_fill_initials
AFTER INSERT ON signatories
BEGIN
    UPDATE signatories SET fio = fio WHERE id = NEW.id;
END;

UPDATE signatories SET fio = fio;
