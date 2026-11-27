"""The deployed tree starts independently of development and the caller's cwd."""
from contextlib import closing
import json
import os
from pathlib import Path
import queue
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[2]


class RuntimeDistributionTests(unittest.TestCase):
    def test_plain_python_selects_root_environment_and_preserves_arguments(self):
        with tempfile.TemporaryDirectory(prefix='itd-run-environment-') as temporary:
            root = Path(temporary)
            shutil.copy2(ROOT / 'run.py', root / 'run.py')
            python = root / '.venv/bin/python'
            python.parent.mkdir(parents=True)
            python.write_text('#!' + sys.executable + '\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n')
            python.chmod(0o755)
            arguments = ['--db', str(root / 'path with spaces/test.db'), '--port', '8080', '--public']
            result = subprocess.run([sys._base_executable, str(root / 'run.py'), *arguments],
                                    cwd='/', capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [str(root / 'run.py'), *arguments])

    def test_broken_dependencies_show_setup_instructions_without_traceback(self):
        with tempfile.TemporaryDirectory(prefix='itd-run-dependencies-') as temporary:
            root = Path(temporary)
            shutil.copy2(ROOT / 'run.py', root / 'run.py')
            module = root / 'app/itd/web.py'
            module.parent.mkdir(parents=True)
            module.write_text("raise ModuleNotFoundError('pydantic_core._pydantic_core')\n")
            result = subprocess.run([sys.executable, str(root / 'run.py')], cwd='/',
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertIn('pip install -r app/requirements.txt', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertFalse((root / 'db').exists())

    def test_root_launcher_without_development_serves_assets_and_authenticated_api(self):
        with tempfile.TemporaryDirectory(prefix='itd-runtime-') as temporary:
            root = Path(temporary) / 'distribution'
            shutil.copytree(ROOT / 'app', root / 'app',
                            ignore=shutil.ignore_patterns('node_modules', '__pycache__', 'bundle-meta.json', 'TPL_*.docx'))
            shutil.copy2(ROOT / 'run.py', root / 'run.py')
            self.assertFalse((root / 'development').exists())
            database = root / 'data/itd.db'
            templates = root / 'app/templates'
            (templates / 'ОЖР.docx').unlink()
            env = dict(os.environ)
            for name in ('PYTHONPATH', 'ITD_PUBLIC_ORIGIN', 'ITD_TEMPLATE_DIR', 'ITD_TEMPLATE_BUNDLE'):
                env.pop(name, None)
            process = subprocess.Popen(
                [sys.executable, str(root / 'run.py'), '--db', str(database),
                 '--public', '--port', '0', '--no-browser'],
                cwd=temporary, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            lines = queue.Queue()

            def collect():
                for line in process.stdout:
                    lines.put(line)
                lines.put(None)

            reader = threading.Thread(target=collect, daemon=True)
            reader.start()
            try:
                startup = []
                while True:
                    line = lines.get(timeout=30)
                    self.assertIsNotNone(line, ''.join(startup))
                    startup.append(line)
                    if line.startswith('Локальная форма ИТД: '):
                        origin, code = line.split(': ', 1)[1].strip().split('/#')
                        break
                opener = build_opener(ProxyHandler({}))
                for route, content_type in (('/', 'text/html'), ('/design.js', 'javascript'),
                                            ('/design.css', 'text/css'), ('/logo.svg', 'image/svg+xml')):
                    with self.subTest(route=route), opener.open(origin + route, timeout=10) as response:
                        self.assertEqual(response.status, 200)
                        self.assertIn(content_type, response.headers['Content-Type'])
                        self.assertTrue(response.read())
                request = Request(origin + '/api/login', data=json.dumps({'code': code}).encode(),
                                  headers={'Content-Type': 'application/json'})
                with opener.open(request, timeout=10) as response:
                    session = json.load(response)['session']
                with opener.open(Request(origin + '/api/status',
                                         headers={'X-ITD-Token': session}), timeout=10) as response:
                    self.assertEqual(json.load(response)['database'], 'ready')
                self.assertTrue(database.is_file())
                self.assertTrue(database.with_name('itd.db.accounts.sqlite3').is_file())
                self.assertEqual(len(list(templates.glob('TPL_*.docx'))), 35)
                self.assertEqual((templates / 'ОЖР.docx').read_bytes(), (ROOT / 'app/templates/ОЖР.docx').read_bytes())
                with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
                    installed = db.execute('SELECT form_set, count(*) FROM document_templates GROUP BY form_set').fetchall()
                self.assertEqual(dict(installed), {'И 1.13-07': 25, 'Приказ Минстроя №344_пр': 5,
                                                   'СП 77.13330.2016': 5})
                self.assertFalse((root / 'development').exists())
                self.assertFalse((Path(temporary) / 'db').exists())
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                reader.join(timeout=5)
                process.stdout.close()

    def test_network_flags_are_exclusive_and_help_does_not_create_data(self):
        with tempfile.TemporaryDirectory(prefix='itd-run-flags-') as temporary:
            database = Path(temporary) / 'unused.db'
            command = [sys.executable, str(ROOT / 'run.py'), '--db', str(database)]
            result = subprocess.run(command + ['--help'], cwd=temporary, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn('--public', result.stdout)
            result = subprocess.run(command + ['--public', '--host', '127.0.0.1'],
                                    cwd=temporary, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(database.exists())
            for value in ('ftp://example.com', 'http://example.com/path', 'http://user:secret@example.com',
                          'http://example.com:99999', 'http://example.com/#fragment'):
                result = subprocess.run(command + ['--public-origin', value, '--no-browser'],
                                        cwd=temporary, capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(database.exists())
