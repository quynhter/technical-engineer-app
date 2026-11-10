"""Справочники участников и наследование назначений объекта в раздел."""

from .db import required_text


def add_organization(connection, *, full_name, short_name=None, ogrn=None, inn=None,
                     address=None, phone=None, sro_info=None):
    cursor = connection.execute(
        "INSERT INTO organizations (full_name, short_name, ogrn, inn, address, phone, sro_info) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (required_text(full_name, "организация"), short_name, ogrn, inn, address, phone, sro_info),
    )
    return cursor.lastrowid


def add_signatory(connection, *, org_id, fio, position, nrs_id=None, order_doc=None,
                  order_attachment_id=None, note=None, last_name=None, first_name=None, middle_name=None):
    if order_attachment_id is not None:
        attachment = connection.execute("SELECT doc_type FROM attachments WHERE id=?", (order_attachment_id,)).fetchone()
        if attachment is None or attachment["doc_type"] != "order":
            raise ValueError("Основание подписанта должно ссылаться на файл типа order")
    cursor = connection.execute(
        "INSERT INTO signatories (org_id, fio, position, nrs_id, order_doc, order_attachment_id, note, "
        "last_name, first_name, middle_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (org_id, required_text(fio, "ФИО"), required_text(position, "должность"), nrs_id,
         order_doc, order_attachment_id, note, last_name, first_name, middle_name),
    )
    return cursor.lastrowid


def assign(connection, *, entity, entity_id, role_key, object_id=None, project_id=None, multiple=False):
    if entity not in ("organization", "signatory"):
        raise ValueError("Назначить можно организацию или подписанта")
    if (object_id is None) == (project_id is None):
        raise ValueError("Укажите только один уровень назначения: объект или раздел")
    table, column = (("organization_assignments", "org_id") if entity == "organization"
                     else ("signatory_assignments", "signatory_id"))
    scope, scope_id = ("object_id", object_id) if object_id is not None else ("project_id", project_id)
    role_key = required_text(role_key, "роль")
    if entity == 'signatory':
        if not multiple:
            connection.execute(f'DELETE FROM {table} WHERE {scope}=? AND role_key=? AND signatory_id<>?',
                               (scope_id, role_key, entity_id))
        connection.execute(f'INSERT OR IGNORE INTO {table} ({scope},role_key,signatory_id) VALUES(?,?,?)',
                           (scope_id, role_key, entity_id))
        return
    # Существующее назначение заменяется, идентификатор записи сохраняется.
    connection.execute(
        f"INSERT INTO {table} ({scope}, role_key, {column}) VALUES (?, ?, ?) "
        f"ON CONFLICT({scope}, role_key) WHERE {scope} IS NOT NULL DO UPDATE SET {column}=excluded.{column}",
        (scope_id, role_key, entity_id),
    )


def participants_context(connection, project_id):
    project = connection.execute("SELECT object_id FROM projects WHERE id=?", (project_id,)).fetchone()
    if project is None:
        raise ValueError("Раздел не найден")
    organizations = {}
    signatories = {}
    candidates = {}
    for scope, scope_id in (("object_id", project["object_id"]), ("project_id", project_id)):
        for row in connection.execute(
            f"SELECT a.role_key, o.* FROM organization_assignments a JOIN organizations o ON o.id=a.org_id WHERE a.{scope}=? ORDER BY a.id", (scope_id,)
        ):
            organizations[row["role_key"]] = dict(row)
        scope_people = {}
        for row in connection.execute(
            f"SELECT a.role_key, s.* FROM signatory_assignments a JOIN signatories s ON s.id=a.signatory_id WHERE a.{scope}=? ORDER BY a.id", (scope_id,)
        ):
            scope_people.setdefault(row['role_key'], []).append(dict(row))
        for role, people in scope_people.items():
            candidates[role] = people
            # Несколько назначений требуют явного выбора в конкретном акте.
            if len(people) != 1:
                signatories[role] = None
                continue
            row = people[0]
            # Отозванное назначение раздела не должно молча подменяться
            # общим подписантом объекта.
            value = dict(row)
            if value["status"] != "Действует":
                signatories[row["role_key"]] = None
                continue
            org = dict(connection.execute("SELECT * FROM organizations WHERE id=?", (value["org_id"],)).fetchone())
            value["organization"] = org
            if value["last_name"] and value["first_name"]:
                value["fio_short"] = value["last_name"] + " " + value["first_name"][0] + "."
                if value["middle_name"]:
                    value["fio_short"] += " " + value["middle_name"][0] + "."
            else:
                value["fio_short"] = value["fio"]
            signatories[row["role_key"]] = value
    companies = [{"role": role, "name": org["short_name"] or org["full_name"], **org}
                 for role, org in organizations.items()]
    contractor = organizations.get('builder')
    if contractor is None and connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='object_participants'"
    ).fetchone():
        contractors = connection.execute(
            """SELECT o.* FROM object_participants p JOIN organizations o ON o.id=p.org_id
               WHERE p.object_id=? AND p.role_key='builder'""", (project['object_id'],)).fetchall()
        if len(contractors) == 1:
            contractor = dict(contractors[0])
    if contractor is not None:
        organizations.setdefault('general_contractor', contractor)
        if 'general_contractor' not in candidates:
            people = [person for person in candidates.get('builder', [])
                      if person['org_id'] == organizations['general_contractor']['id']]
            if people:
                candidates['general_contractor'] = people
                builder = signatories.get('builder')
                signatories['general_contractor'] = builder if builder and builder['org_id'] == people[0]['org_id'] else None
    periods=[]
    if connection.execute("SELECT 1 FROM sqlite_master WHERE name='participant_periods'").fetchone():
        periods=[dict(r) for r in connection.execute('SELECT * FROM participant_periods WHERE object_id=? ORDER BY id',(project['object_id'],))]
    return {"organizations": organizations, "signatories": signatories, "companies": companies,
            'signatory_candidates': candidates, 'participation_periods':periods}
