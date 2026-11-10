import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from itd import knowledge as kb
from itd.__main__ import main
from itd.db import initialize
from itd.web import WorkspaceServer


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'sources'
        (self.root / 'sample').mkdir(parents=True)
        self.index = self.base / 'knowledge.db'
        self.md = self.root / 'sample/one.md'
        self.md.write_text('''---
doc_id: "ТЕСТ"
clause: "4.2"
work_types: ["испытания кабеля"]
itd_forms: ["Протокол"]
keywords: ["изоляция"]
source_page: null
---
Изоляция кабеля. Сноска: только при температуре выше 5 °C.
''', encoding='utf-8')
        self.rule = {'doc_id': 'ТЕСТ', 'clause': '4.2', 'work_category': 'испытания кабеля',
                     'subject': 'кабель', 'parameter': 'изоляция', 'operator': 'gte',
                     'min_value': 0.5, 'max_value': None, 'unit': 'МОм',
                     'condition': 'Только при температуре выше 5 °C', 'required_itd': ['Протокол'],
                     'raw_text': 'Изоляция кабеля не менее 0,5 МОм.'}
        self.jsonl = self.root / 'sample/rules.jsonl'
        self.jsonl.write_text(json.dumps(self.rule, ensure_ascii=False) + '\n', encoding='utf-8')

    def test_search_provenance_conditions_and_filters(self):
        before = self.md.read_bytes()
        result = kb.search(self.root, self.index, 'ИЗОЛЯЦ', corpus='sample', kind='rule',
                           clause='4.2', work='кабеля', form='ПРОТОКОЛ')
        self.assertEqual(result['count'], 1)
        hit = result['hits'][0]
        self.assertEqual(hit['metadata'], self.rule)
        self.assertEqual(hit['source_sha256'], hashlib.sha256(self.jsonl.read_bytes()).hexdigest())
        full = kb.show(self.root, self.index, hit['id'])
        self.assertEqual(full['text'], self.rule['raw_text'])
        self.assertEqual(full['provenance_status'], 'unverified')
        self.assertEqual(self.md.read_bytes(), before)
        self.assertEqual(kb.status(self.root, self.index)['index_status'], 'ready')
        self.assertEqual(kb.search(self.root, self.index, 'изоляц', corpus='other')['count'], 0)

    def test_refresh_removes_deleted_and_updates_modified_sources(self):
        kb.build_index(self.root, self.index)
        self.jsonl.unlink()
        self.md.write_text(self.md.read_text().replace('Изоляция кабеля.', 'Заземление кабеля.'))
        self.assertEqual(kb.status(self.root, self.index)['index_status'], 'stale')
        hit = kb.search(self.root, self.index, 'заземлен')['hits'][0]
        self.assertEqual(hit['kind'], 'chunk')
        self.assertEqual(kb.status(self.root, self.index)['entries'], 1)
        self.assertIn('Сноска:', kb.show(self.root, self.index, hit['id'])['text'])

    def test_bad_input_does_not_replace_index(self):
        kb.build_index(self.root, self.index)
        before = self.index.read_bytes()
        self.jsonl.write_text('{broken}')
        with self.assertRaisesRegex(ValueError, 'rules.jsonl'):
            kb.build_index(self.root, self.index)
        self.assertEqual(self.index.read_bytes(), before)

    def test_does_not_overwrite_business_database(self):
        business = self.base / 'itd.db'
        initialize(business)
        before = business.read_bytes()
        with self.assertRaisesRegex(ValueError, 'перезапись запрещена'):
            kb.build_index(self.root, business)
        self.assertEqual(business.read_bytes(), before)

    def test_untrusted_yaml_invalid_rules_and_symlinks(self):
        original = self.md.read_text()
        self.md.write_text(original.replace('doc_id: "ТЕСТ"', 'doc_id: !!python/object:bad'))
        with self.assertRaises(ValueError):
            kb.load_sources(self.root)
        self.md.write_text(original)
        self.rule['min_value'] = float('nan')
        self.jsonl.write_text(json.dumps(self.rule))
        with self.assertRaises(ValueError):
            kb.load_sources(self.root)
        self.jsonl.unlink()
        target = self.base / 'outside.md'
        target.write_text(original)
        self.jsonl.with_suffix('.md').symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Ссылка'):
            kb.load_sources(self.root)

    def test_fts_query_is_data_and_export_is_lossless(self):
        self.assertEqual(kb.search(self.root, self.index, '" OR NEAR(foo)')['count'], 0)
        for query in ('---', '*'):
            with self.assertRaises(ValueError):
                kb.search(self.root, self.index, query)
        output = self.base / 'export.jsonl'
        kb.export_entries(self.root, output)
        entries = [json.loads(line) for line in output.read_text().splitlines()]
        self.assertEqual(len(entries), 2)
        self.assertEqual(next(r for r in entries if r['kind'] == 'rule')['metadata'], self.rule)
        with self.assertRaises(FileExistsError):
            kb.export_entries(self.root, output)

    def test_cli_works_without_business_db(self):
        db = self.base / 'absent/itd.db'
        stream = io.StringIO()
        with redirect_stdout(stream):
            main(['--db', str(db), 'knowledge-search', '--root', str(self.root), '--query', 'изоляц'])
        self.assertEqual(json.loads(stream.getvalue())['count'], 2)
        self.assertFalse(db.exists())

    def test_all_supplied_corpora_and_multiple_chunks(self):
        rows, _ = kb.load_sources(kb.default_root())
        self.assertEqual(set(r['corpus'] for r in rows), {'sp77', 'i_1_13_07', 'prikaz_344pr', 'rd78_145_93'})
        for corpus in set(r['corpus'] for r in rows):
            self.assertTrue(any(r['kind'] == 'rule' and r['corpus'] == corpus for r in rows))
            self.assertTrue(any(r['kind'] == 'chunk' and r['corpus'] == corpus for r in rows))
        self.md.write_text(self.md.read_text() + '\n' + self.md.read_text().replace('"4.2"', '"4.3"'))
        rows, _ = kb.load_sources(self.root)
        self.assertEqual(sum(r['kind'] == 'chunk' for r in rows), 2)

    def test_web_auth_search_full_text_and_no_business_writes(self):
        db = self.base / 'itd.db'
        initialize(db)
        before = db.read_bytes()
        server = WorkspaceServer(('127.0.0.1', 0), db)
        _, initial_code = server.prepare()
        session = server.accounts.login(initial_code)["session"]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch('itd.knowledge.default_root', return_value=self.root):
                with self.assertRaises(HTTPError) as error:
                    urlopen(server.origin + '/api/knowledge')
                self.assertEqual(error.exception.code, 403)
                def get(path):
                    with urlopen(Request(server.origin + path, headers={'X-ITD-Token': session})) as response:
                        return json.load(response)
                self.assertEqual(get('/api/knowledge')['entries'], 2)
                self.assertEqual(get('/api/knowledge?query=')['count'], 2)
                hit = get('/api/knowledge?query=4.2')['hits'][0]
                from urllib.parse import urlencode
                full = get('/api/knowledge?' + urlencode({'id': hit['id']}))
                self.assertIn('text', full)
                with self.assertRaises(HTTPError):
                    get('/api/knowledge?' + urlencode({'id': '../../secret'}))
        finally:
            server.shutdown(); server.server_close(); thread.join()
        self.assertEqual(db.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
