"""The nine approved agent contracts, independent of ignored db/work snapshots."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote

from itd.integrity import manifest_entries, verify_files


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / 'fixtures/agent_contract'


class AgentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='itd-contract-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.folder = Path(cls.temp.name)
        cls.expected = json.loads((FIXTURES / 'cli-contract.json').read_text())
        cls.helps = {name: cls.cli(*([] if name == '<root>' else [name]), '--help')
                     for name in cls.expected}

    @classmethod
    def cli(cls, *args):
        result = subprocess.run([sys.executable, '-m', 'itd', '--agent',
                                 '--db', str(cls.folder / 'unused.db'),
                                 '--itd-root', str(cls.folder / 'unused-itd'), *args],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise AssertionError(result.stderr)
        if (cls.folder / 'unused.db').exists() or (cls.folder / 'unused-itd').exists():
            raise AssertionError('Help created business data')
        return result.stdout

    def test_01_required_knowledge_commands(self):
        for name in ('knowledge-status', 'knowledge-search', 'knowledge-show',
                     'knowledge-validate', 'knowledge-index'):
            self.assertIn(name, self.helps)

    def test_02_required_global_flags(self):
        self.assertTrue({'--db', '--itd-root', '--agent'} <=
                        set(re.findall(r'--[a-z][a-z0-9-]*', self.helps['<root>'])))

    def test_03_all_commands_and_flags_remain(self):
        self.assertEqual(len(self.expected) - 1, 65)
        for name, expected in self.expected.items():
            with self.subTest(command=name):
                self.assertTrue(set(re.findall(r'--[a-z][a-z0-9-]*', expected)) <=
                                set(re.findall(r'--[a-z][a-z0-9-]*', self.helps[name])))

    def test_04_all_template_and_form_paths(self):
        entries = manifest_entries(FIXTURES / 'templates.txt')
        self.assertEqual(len(entries), 13)
        for name in entries:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_05_current_skill_links_to_templates_and_forms(self):
        for doc in (ROOT / 'ai/skills').rglob('*.md'):
            for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', doc.read_text()):
                if '://' in link or link.startswith('#'):
                    continue
                path = (doc.parent / unquote(link.split('#')[0])).resolve()
                if path.is_relative_to(ROOT / 'app/templates') or path.is_relative_to(ROOT / 'app/forms'):
                    self.assertTrue(path.exists(), str(path))

    def test_06_help_creates_neither_database_nor_tree(self):
        self.cli('--help')
        self.assertFalse((self.folder / 'unused.db').exists())
        self.assertFalse((self.folder / 'unused-itd').exists())

    def test_07_all_source_hashes_and_corrupt_pdf_rejection(self):
        entries = manifest_entries(ROOT / 'ai/knowledge-integrity.sha256')
        self.assertEqual(len(entries), 22294)
        verify_files(ROOT, entries)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'original.pdf'
            path.write_bytes(b'%PDF-test-original')
            expected = {'original.pdf': hashlib.sha256(path.read_bytes()).hexdigest()}
            verify_files(folder, expected)
            path.write_bytes(b'%PDF-corrupt')
            with self.assertRaisesRegex(ValueError, 'целостность'):
                verify_files(folder, expected)
            path.unlink()
            with self.assertRaises(ValueError):
                verify_files(folder, expected)
            path.write_text('version https://git-lfs.github.com/spec/v1\n')
            with self.assertRaisesRegex(ValueError, 'LFS'):
                verify_files(folder, expected)

    def test_08_agent_log_format(self):
        # Exercise the real CLI/configure implementation in a fresh interpreter.
        code = '''import pathlib, sys
from unittest.mock import patch
from itd.__main__ import main
with patch('itd.paths.ROOT', pathlib.Path(sys.argv[1])):
    main(['--agent', '--db', sys.argv[2], 'template-schema'])
'''
        result = subprocess.run([sys.executable, '-c', code, str(self.folder),
                                 str(self.folder / 'unused.db')], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = (self.folder / 'logs/ai.log').read_text().splitlines()
        self.assertRegex(lines[0], r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3} INFO Агент запустил команду template-schema$')
        self.assertTrue(lines[-1].endswith('INFO Команда агента template-schema завершена'))
        self.assertEqual(len(lines), 2)

    def test_09_document_paths_and_known_missing_originals(self):
        # MCP transports, skills and generated documentation share one catalogue (З1/З5).
        from itd.tools import TOOLS, documentation
        mcp_doc = (ROOT / 'ai/docs/mcp.md').read_text()
        self.assertIn(documentation(), mcp_doc)
        reads = [tool for tool in TOOLS if tool.access == 'read']
        writes = [tool for tool in TOOLS if tool.access == 'write']
        self.assertTrue(all(tool.role == 'viewer' for tool in reads))
        self.assertTrue(all(tool.role == 'editor' for tool in writes))
        self.assertFalse(any(tool.name.startswith(('apply', 'confirm')) for tool in TOOLS))
        for name in ('AGENTS.md', 'README.md', 'ai/skills/ai-technical-engineer/SKILL.md'):
            self.assertIn('docs/mcp.md', (ROOT / name).read_text(), name)
            self.assertIn('docs/assistants.md', (ROOT / name).read_text(), name)
        for name in ('assistants', 'threads', 'messages'):
            self.assertIn(name, (ROOT / 'ai/MAP.md').read_text())
        self.assertTrue((ROOT / 'app/llm-providers.example.json').is_file())
        # New account schema and remote credentials are documented together (З1).
        for name in ('AGENTS.md', 'README.md', 'ai/skills/ai-technical-engineer/SKILL.md', 'ai/MAP.md'):
            content = (ROOT / name).read_text()
            self.assertIn('api_tokens', content, name)
        for name in ('AGENTS.md', 'README.md', 'ai/skills/ai-technical-engineer/SKILL.md'):
            self.assertIn('Authorization: Bearer', (ROOT / name).read_text(), name)
        expected = json.loads((FIXTURES / 'paths.json').read_text())
        known = set(expected['known_missing_originals'])
        self.assertEqual(len(known), 89)
        for name in expected['required']:
            self.assertTrue((ROOT / name).exists(), name)
        docs = [ROOT / 'AGENTS.md', ROOT / 'README.md', ROOT / 'ai/MAP.md',
                *(ROOT / 'ai/skills').rglob('*.md')]
        for doc in docs:
            for token in re.findall(r'`([^`]+)`', doc.read_text()):
                if token.startswith(('app/', 'ai/skills/')) and not any(c in token for c in '<>*{}…'):
                    # Shell examples contain options; literal repository paths do not.
                    if ' --' not in token and ' |' not in token and '\n' not in token:
                        path = ROOT / token
                        self.assertTrue(path.exists() or token in known, token)
            for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', doc.read_text()):
                if '://' in link or link.startswith('#'):
                    continue
                path = (doc.parent / unquote(link.split('#')[0])).resolve()
                if not path.exists():
                    self.assertIn(str(path.relative_to(ROOT)), known)


if __name__ == '__main__':
    unittest.main()
