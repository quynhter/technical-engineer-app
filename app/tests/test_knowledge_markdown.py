"""Проверка читаемого Markdown и неисполняемого входа без браузерных библиотек."""
import shutil
import subprocess
import unittest
from pathlib import Path


class KnowledgeMarkdownTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Для DOM-проверки Markdown нужен Node.js')
    def test_tables_lists_emphasis_and_untrusted_text(self):
        renderer = Path(__file__).resolve().parents[1] / 'itd/web_assets/knowledge-markdown.js'
        result = subprocess.run(['node', '-e', r'''
const assert = require('node:assert/strict');
const {renderKnowledgeMarkdown} = require(process.argv[1]);
class Element {
 constructor(tag, value='') { this.tag=tag; this.value=value; this.children=[]; this.attrs={}; }
 set textContent(value) { this.children=[]; this.value=value; }
 append(...children) { this.children.push(...children); }
 setAttribute(key,value) { this.attrs[key]=value; }
 set innerHTML(value) { throw Error('Untrusted HTML must not be parsed'); }
}
const doc = {createElement: tag => new Element(tag), createTextNode: value => new Element('#text',value), createDocumentFragment: () => new Element('#fragment')};
const source = '# Испытания\n\n**Важно:** условия *применения*.\n\n| Параметр | Допуск |\n|---|---|\n| Температура | ≥ 5 °C |\n| Сноска | Только при **условии** |\n\n- Первый пункт\n- Второй пункт\n\n3. Третий\n4. Четвёртый\n\n> Примечание\n\n```text\n<script>alert(1)</script>\n```\n\n[Оригинал](https://example.com/doc) [Опасная ссылка](javascript:alert)\n\n<img src=x onerror=alert(1)>';
const tree = renderKnowledgeMarkdown(source,doc);
const walk = n => [n,...n.children.flatMap(walk)];
const all = walk(tree), tags = tag => all.filter(n=>n.tag===tag);
assert.equal(tags('table').length,1); assert.equal(tags('th').length,2); assert.equal(tags('td').length,4);
assert.equal(tags('ul').length,1); assert.equal(tags('ol')[0].attrs.start,'3'); assert.equal(tags('li').length,4);
assert.equal(tags('strong').length,2); assert.equal(tags('em').length,1);
assert.equal(tags('blockquote').length,1); assert.equal(tags('pre').length,1);
assert.equal(tags('a').length,1); assert.equal(tags('a')[0].attrs.href,'https://example.com/doc');
assert.equal(tags('script').length,0); assert.equal(tags('img').length,0);
assert.ok(all.some(n=>n.value==='<img src=x onerror=alert(1)>'));
assert.ok(all.some(n=>n.value==='≥ 5 °C'));
assert.ok(all.some(n=>n.value==='<script>alert(1)</script>'));
// Без потери текста при незакрытом блоке кода и экранированной черте таблицы.
assert.ok(walk(renderKnowledgeMarkdown('```\nданные',doc)).some(n=>n.value==='данные'));
assert.ok(walk(renderKnowledgeMarkdown('| A | B |\n|---|---|\n| x\\|y | z |',doc)).some(n=>n.value==='x|y'));
''', str(renderer)], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
