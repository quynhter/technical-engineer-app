import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from itd.archive import import_file, link_file, publish_project_file, file_type, archived_path
from itd.db import initialize, connect, add_object, add_project
from itd.file_manager import make_plan, apply_plan


class FileManagerTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.db=self.root/'itd.db';self.archive=self.root/'archive'
        initialize(self.db)
        with connect(self.db) as c:
            obj=add_object(c,'Объект')
            self.pid=add_project(c,object_id=obj,section_code='СПС',code='РД',name='Раздел')
            self.other=add_project(c,object_id=obj,section_code='АОВ',code='РД2',name='Другой')
        self.folder=self.root/'ИТД'/'Объект'/'СПС'/'Исходные файлы'

    def add(self,name='Договор.pdf',kind='contract',content=b'contract',publish=True):
        source=self.root/name;source.write_bytes(content)
        with connect(self.db) as c:
            result=import_file(c,archive_root=self.archive,source=source,doc_type=kind,title=name)
            aid=result['id'];link_file(c,attachment_id=aid,entity='project',entity_id=self.pid)
            row=dict(c.execute('SELECT * FROM attachments WHERE id=?',(aid,)).fetchone())
            visible=self.root/publish_project_file(c,attachment_id=aid,project_id=self.pid,archive_root=self.archive) if publish else None
        return aid,visible,archived_path(self.archive,row['storage_path'])

    def plan(self,purpose='check',aid=None):
        return make_plan(self.db,self.pid,purpose,aid,'secret')

    def apply(self,p,types=None):
        return apply_plan(self.db,p['plan'],p['token'],types or {},'secret')

    def test_types_keep_legacy_metadata_and_quality_is_generic(self):
        aid,_,_=self.add(kind='quality')
        with connect(self.db) as c:
            row=c.execute('SELECT * FROM attachments WHERE id=?',(aid,)).fetchone()
            self.assertEqual(file_type(row),'quality');self.assertEqual(row['doc_type'],'other')
        aid,_,_=self.add('Паспорт.pdf','passport',b'passport')
        with connect(self.db) as c:
            self.assertEqual(file_type(c.execute('SELECT * FROM attachments WHERE id=?',(aid,)).fetchone()),'quality')

    def test_delete_is_previewed_signed_and_removes_only_selected_originals(self):
        aid,visible,archived=self.add();other=self.folder/'посторонний.pdf';other.write_bytes(b'other')
        p=self.plan('delete',aid)
        self.assertEqual(p['plan']['actions'][0]['action'],'remove')
        self.assertTrue(visible.exists());self.assertTrue(archived.exists())
        tampered=json.loads(json.dumps(p));tampered['plan']['actions'][0]['id']=999
        with self.assertRaisesRegex(ValueError,'Недействительный'):self.apply(tampered)
        self.apply(p)
        self.assertFalse(visible.exists());self.assertFalse(archived.exists());self.assertTrue(other.exists())
        with connect(self.db) as c:
            self.assertIsNone(c.execute('SELECT * FROM attachments WHERE id=?',(aid,)).fetchone())
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertTrue((self.root/'Договор.pdf').exists())

    def test_shared_file_detaches_selected_section_and_preserves_other_section(self):
        aid,visible,archived=self.add()
        with connect(self.db) as c:
            link_file(c,attachment_id=aid,entity='project',entity_id=self.other)
            other=self.root/publish_project_file(c,attachment_id=aid,project_id=self.other,archive_root=self.archive)
        p=self.plan('delete',aid);self.assertEqual(p['plan']['actions'][0]['action'],'detach');self.apply(p)
        self.assertFalse(visible.exists());self.assertTrue(other.exists());self.assertTrue(archived.exists())
        with connect(self.db) as c:self.assertIsNotNone(c.execute('SELECT * FROM attachments WHERE id=?',(aid,)).fetchone())

    def test_references_protect_business_records_even_when_file_missing(self):
        aid,visible,archived=self.add()
        with connect(self.db) as c:
            obj=c.execute('SELECT object_id FROM projects WHERE id=?',(self.pid,)).fetchone()[0]
            link_file(c,attachment_id=aid,entity='object',entity_id=obj)
        visible.unlink()
        for purpose in ('delete','check'):
            p=self.plan(purpose,aid if purpose=='delete' else None)
            self.assertEqual(p['plan']['actions'],[]);self.assertIn('документы объекта',p['plan']['blocked'][0]['reason'])
        self.assertTrue(archived.exists())

    def test_check_imports_new_files_removes_missing_and_preserves_rd_type(self):
        aid,visible,archived=self.add();visible.unlink()
        added=self.folder/'Сертификат.pdf';added.write_bytes(b'new quality')
        rd=self.folder.parent/'Рабочая документация';rd.mkdir();(rd/'Чертёж.pdf').write_bytes(b'new rd')
        p=self.plan();self.assertEqual(len(p['plan']['actions']),3)
        self.apply(p,{str(added.relative_to(self.root)):'quality'})
        self.assertFalse(archived.exists());self.assertTrue(added.exists())
        with connect(self.db) as c:
            rows=c.execute('SELECT * FROM attachments ORDER BY original_name').fetchall()
            self.assertEqual({file_type(r) for r in rows},{'quality','rd'})
            self.assertEqual(c.execute('SELECT COUNT(*) FROM project_files').fetchone()[0],2)
        self.assertEqual(self.plan()['plan']['actions'],[])

    def test_moved_same_file_is_relinked_without_deleting_archive_or_record(self):
        aid,visible,archived=self.add();moved=visible.with_name('Перемещён.pdf');visible.rename(moved)
        p=self.plan();self.assertEqual([a['action'] for a in p['plan']['actions']],['add']);self.apply(p)
        self.assertTrue(archived.exists());self.assertTrue(moved.exists())
        self.assertEqual(self.plan()['plan']['actions'],[])

    def test_legacy_archive_is_restored_not_deleted(self):
        aid,_,archived=self.add(publish=False)
        p=self.plan();self.assertEqual(p['plan']['actions'][0]['action'],'restore');self.apply(p)
        self.assertTrue(archived.exists());self.assertTrue((self.folder/'Договор.pdf').exists())

    def test_changed_bytes_and_stale_plan_are_not_deleted(self):
        aid,visible,archived=self.add();p=self.plan('delete',aid);visible.write_bytes(b'edited')
        with self.assertRaisesRegex(ValueError,'изменились'):self.apply(p)
        current=self.plan('delete',aid);self.assertEqual(current['plan']['actions'],[])
        self.assertTrue(current['plan']['blocked']);self.assertEqual(visible.read_bytes(),b'edited');self.assertTrue(archived.exists())

    def test_symlink_and_unreadable_folder_abort_before_any_delete(self):
        aid,visible,archived=self.add();external=self.root/'external';external.write_bytes(b'external')
        (self.folder/'ссылка.pdf').symlink_to(external)
        with self.assertRaisesRegex(ValueError,'Ссылки'):self.plan()
        (self.folder/'ссылка.pdf').unlink()
        original=Path.iterdir
        def fail(path):
            if path==self.folder:raise PermissionError('no access')
            return original(path)
        with patch.object(Path,'iterdir',fail):
            with self.assertRaises(PermissionError):self.plan()
        self.assertTrue(archived.exists());self.assertTrue(visible.exists())

    def test_failed_disk_move_restores_staged_files_and_database(self):
        aid,visible,archived=self.add();p=self.plan('delete',aid)
        original=os.replace;calls=[]
        def fail_second(source,target):
            calls.append(source)
            if len(calls)==2:raise OSError('disk error')
            return original(source,target)
        with patch('itd.file_manager.os.replace',side_effect=fail_second):
            with self.assertRaises(OSError):self.apply(p)
        self.assertTrue(visible.exists());self.assertTrue(archived.exists())
        with connect(self.db) as c:
            self.assertIsNotNone(c.execute('SELECT * FROM attachments WHERE id=?',(aid,)).fetchone())
            self.assertEqual(c.execute('SELECT state FROM file_operations').fetchone()[0],'rolled_back')

    def test_interrupted_pending_operation_is_recovered_before_next_check(self):
        aid,visible,archived=self.add();stage=self.root/'work'/'file-operations'/('a'*32);stage.mkdir(parents=True)
        from itd.archive import digest
        move={'path':str(visible.relative_to(self.root)),'saved':'0-0','sha256':digest(visible)}
        with connect(self.db) as c:c.execute("INSERT INTO file_operations(id,state,moves_json) VALUES(?,'pending',?)",('a'*32,json.dumps([move])))
        visible.rename(stage/'0-0')
        self.assertEqual(self.plan()['plan']['actions'],[]);self.assertTrue(visible.exists());self.assertTrue(archived.exists())

    def test_missing_archive_is_repaired_from_visible_file(self):
        aid,visible,archived=self.add();archived.unlink()
        p=self.plan();self.assertEqual([a['action'] for a in p['plan']['actions']],['repair'])
        self.apply(p);self.assertEqual(archived.read_bytes(),visible.read_bytes())
        self.assertNotEqual(archived.stat().st_ino,visible.stat().st_ino)

    def test_existing_hash_keeps_its_type_and_multiple_paths_share_one_record(self):
        aid,visible,archived=self.add()
        copy=visible.with_name('Другая копия.pdf');copy.write_bytes(visible.read_bytes())
        self.apply(self.plan(),{str(copy.relative_to(self.root)):'quality'})
        with connect(self.db) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM attachments').fetchone()[0],1)
            self.assertEqual(file_type(c.execute('SELECT * FROM attachments').fetchone()),'contract')
        self.apply(self.plan('delete',aid))
        self.assertFalse(copy.exists());self.assertFalse(visible.exists());self.assertFalse(archived.exists())


    def test_imported_spreadsheet_blob_does_not_break_check_or_delete_plan(self):
        import hashlib
        aid,visible,archived=self.add('Ведомость.csv','other',b'name;unit\nCable;m')
        content=visible.read_bytes()
        with connect(self.db) as c:
            c.execute('INSERT INTO resource_imports(id,project_id,filename,sha256,content,attachment_id) VALUES(?,?,?,?,?,?)',
                      ('import-with-blob',self.pid,visible.name,hashlib.sha256(content).hexdigest(),content,aid))
        check=self.plan()
        self.assertEqual(check['plan']['actions'],[])
        deletion=self.plan('delete',aid)
        self.assertEqual(deletion['plan']['actions'],[])
        self.assertIn('импорт ведомости',deletion['plan']['blocked'][0]['reason'])
        # The HTTP response carries only JSON values, never the spreadsheet bytes.
        self.assertEqual(json.loads(json.dumps(deletion)),deletion)
        self.apply(deletion)
        self.assertTrue(visible.exists());self.assertTrue(archived.exists())
        with connect(self.db) as c:
            self.assertEqual(c.execute('SELECT content FROM resource_imports').fetchone()[0],content)
        stale=self.plan('delete',aid)
        with connect(self.db) as c:
            c.execute('UPDATE resource_imports SET content=? WHERE id=?',(b'changed binary source','import-with-blob'))
        with self.assertRaisesRegex(ValueError,'изменились'):
            self.apply(stale)
