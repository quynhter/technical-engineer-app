import contextlib
import errno
import io
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from itd.web import WorkspaceServer, create_server, serve


class WebStartupTests(unittest.TestCase):
    def test_default_busy_port_falls_back_and_serves_loopback(self):
        calls = []

        def factory(address, database):
            calls.append(address)
            if address[1] == 8765:
                raise OSError(errno.EADDRINUSE, 'Address already in use')
            return WorkspaceServer(address, database)

        with patch('itd.web.WorkspaceServer', side_effect=factory), contextlib.redirect_stdout(io.StringIO()) as output:
            server = create_server(Path('unused.db'))
        self.addCleanup(server.server_close)
        self.assertEqual(calls, [('127.0.0.1', 8765), ('127.0.0.1', 0)])
        self.assertGreater(server.server_port, 0)
        self.assertIn('уже занят', output.getvalue())

    def test_explicit_busy_port_keeps_listener_and_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as folder, socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            port = listener.getsockname()[1]
            database = Path(folder) / 'missing.db'
            with self.assertRaisesRegex(ValueError, '--port 0'):
                serve(database, port, open_browser=False)
            self.assertFalse(database.exists())
            self.assertEqual(listener.getsockname()[1], port)

    def test_port_zero_and_invalid_ports(self):
        server = create_server(Path('unused.db'), 0)
        self.addCleanup(server.server_close)
        self.assertGreater(server.server_port, 0)
        for port in (-1, 65536):
            with self.assertRaisesRegex(ValueError, '65535'):
                create_server(Path('unused.db'), port)

    def test_other_bind_errors_are_not_treated_as_busy_port(self):
        with patch('itd.web.WorkspaceServer', side_effect=PermissionError(errno.EACCES, 'denied')) as factory:
            with self.assertRaises(PermissionError):
                create_server(Path('unused.db'))
            self.assertEqual(factory.call_count, 1)

    def test_database_failure_closes_bound_socket(self):
        with patch('itd.web.create_server') as factory:
            factory.return_value.prepare.side_effect = RuntimeError('migration failed')
            with self.assertRaisesRegex(RuntimeError, 'migration failed'):
                serve(Path('unused.db'), open_browser=False)
            factory.return_value.server_close.assert_called_once()

    def test_both_entry_points_report_explicit_conflict_without_touching_database(self):
        import subprocess
        import sys

        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as folder, socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            port = listener.getsockname()[1]
            for entry in ('cli', 'script'):
                with self.subTest(entry=entry):
                    database = Path(folder) / entry / 'missing.db'
                    command = ([sys.executable, '-m', 'app.itd', '--db', str(database), 'web']
                               if entry == 'cli' else
                               [sys.executable, str(root/'app/scripts/start_web.py'), '--db', str(database)])
                    result = subprocess.run(command + ['--port', str(port), '--no-browser'],
                                            cwd=root, capture_output=True, text=True, timeout=15)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn('уже занят', result.stderr)
                    self.assertIn('--port 0', result.stderr)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertFalse(database.parent.exists())

    def test_both_entry_points_start_with_busy_default_or_port_zero(self):
        import json
        import queue
        import subprocess
        import sys
        import threading
        from urllib.error import HTTPError
        from urllib.request import Request, build_opener, ProxyHandler

        root = Path(__file__).resolve().parents[2]
        # Если 8765 уже занят другим процессом, оставляем его работающим.
        with socket.socket() as listener, tempfile.TemporaryDirectory() as folder:
            try:
                listener.bind(('127.0.0.1', 8765))
                listener.listen()
            except OSError as error:
                if error.errno != errno.EADDRINUSE:
                    raise
            for entry in ('cli', 'script'):
                for ports in ([], ['--port', '0']):
                    with self.subTest(entry=entry, ports=ports):
                        database = Path(folder) / f'{entry}-{len(ports)}.db'
                        command = ([sys.executable, '-m', 'app.itd', '--db', str(database), 'web']
                                   if entry == 'cli' else
                                   [sys.executable, str(root/'app/scripts/start_web.py'), '--db', str(database)])
                        process = subprocess.Popen(command + ports + ['--no-browser'], cwd=root,
                                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                   text=True)
                        lines = queue.Queue()

                        def read_output(stream=process.stdout, target=lines):
                            for line in stream:
                                target.put(line)
                            target.put(None)

                        reader = threading.Thread(target=read_output, daemon=True)
                        reader.start()
                        try:
                            output = []
                            while True:
                                line = lines.get(timeout=15)
                                self.assertIsNotNone(line, ''.join(output))
                                output.append(line)
                                if line.startswith('Локальная форма ИТД: '):
                                    url = line.split(': ', 1)[1].strip()
                                    break
                            origin, token = url.split('/#')
                            self.assertTrue(origin.startswith('http://127.0.0.1:'))
                            self.assertNotEqual(int(origin.rsplit(':', 1)[1]), 8765)
                            opener = build_opener(ProxyHandler({}))
                            login = Request(origin+'/api/login', headers={'Content-Type': 'application/json'},
                                            data=json.dumps({'code': token}).encode())
                            with opener.open(login, timeout=5) as response:
                                session = json.load(response)['session']
                            request = Request(origin+'/api/status', headers={'X-ITD-Token': session})
                            with opener.open(request, timeout=5) as response:
                                self.assertEqual(json.load(response)['database'], 'ready')
                            with self.assertRaises(HTTPError) as denied:
                                opener.open(origin+'/api/status', timeout=5)
                            self.assertEqual(denied.exception.code, 403)
                            denied.exception.close()
                            self.assertTrue(database.is_file())
                            if not ports:
                                self.assertIn('уже занят', ''.join(output))
                        finally:
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait(timeout=5)
                            reader.join(timeout=5)
                            process.stdout.close()
