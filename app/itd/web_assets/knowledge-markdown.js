'use strict';
// Небольшой DOM-рендерер используемого в базе подмножества Markdown.
// HTML из источника всегда остаётся текстом; внешних зависимостей нет.
function renderKnowledgeMarkdown(text, ownerDocument = document) {
 const make = tag => ownerDocument.createElement(tag);
 const literal = (parent, value) => parent.append(ownerDocument.createTextNode(value));
 function inline(parent, value) {
  const pattern = /(`[^`\n]+`|\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|\[[^\]\n]+\]\([^\s)]+\))/g;
  let cursor = 0;
  for (const match of value.matchAll(pattern)) {
   literal(parent, value.slice(cursor, match.index));
   const token = match[0];
   let child;
   if (token.startsWith('`')) { child = make('code'); child.textContent = token.slice(1, -1); }
   else if (token.startsWith('**') || token.startsWith('__')) { child = make('strong'); inline(child, token.slice(2, -2)); }
   else if (token.startsWith('*')) { child = make('em'); inline(child, token.slice(1, -1)); }
   else {
    const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
    // Ссылки с активными схемами, file/data и относительные пути не открываем.
    if (/^https?:\/\//i.test(link[2])) {
     child = make('a'); child.setAttribute('href', link[2]); child.setAttribute('target', '_blank'); child.setAttribute('rel', 'noopener noreferrer'); inline(child, link[1]);
    } else { child = make('span'); literal(child, link[1]); }
   }
   parent.append(child); cursor = match.index + token.length;
  }
  literal(parent, value.slice(cursor));
 }
 const lines = String(text).replace(/\r\n?/g, '\n').split('\n');
 const output = ownerDocument.createDocumentFragment();
 const cells = line => line.trim().replace(/^\|/, '').replace(/\|$/, '').split(/(?<!\\)\|/).map(v => v.trim().replace(/\\\|/g, '|'));
 const separator = line => line && line.includes('|') && cells(line).every(v => /^:?-{3,}:?$/.test(v));
 const listItem = line => /^\s*(?:[-+*]|\d+[.)])\s+/.test(line);
 const special = (line, next) => !line.trim() || /^\s*(?:#{1,6}\s|```|>\s?|(?:-{3,}|\*{3,})\s*$)/.test(line) || listItem(line) || separator(next);
 let i = 0;
 while (i < lines.length) {
  const line = lines[i];
  if (!line.trim()) { i++; continue; }
  if (/^\s*```/.test(line)) {
   const pre = make('pre'), code = make('code'), content = []; i++;
   while (i < lines.length && !/^\s*```/.test(lines[i])) content.push(lines[i++]);
   code.textContent = content.join('\n'); pre.append(code); output.append(pre); if (i < lines.length) i++; continue;
  }
  if (line.includes('|') && separator(lines[i + 1])) {
   const wrap = make('div'); wrap.className = 'table-scroll';
   const table = make('table'), head = make('thead'), tr = make('tr');
   const headers = cells(line);
   for (const value of headers) { const th = make('th'); th.setAttribute('scope', 'col'); inline(th, value); tr.append(th); }
   head.append(tr); table.append(head); const body = make('tbody'); i += 2;
   while (i < lines.length && lines[i].trim() && lines[i].includes('|')) {
    const row = make('tr'), values = cells(lines[i++]);
    for (let c = 0; c < Math.max(headers.length, values.length); c++) { const td = make('td'); inline(td, values[c] || ''); row.append(td); }
    body.append(row);
   }
   table.append(body); wrap.append(table); output.append(wrap); continue;
  }
  const heading = /^\s*(#{1,6})\s+(.+)$/.exec(line);
  if (heading) { const h = make('h' + Math.min(6, Math.max(4, heading[1].length))); inline(h, heading[2]); output.append(h); i++; continue; }
  if (/^\s*(?:-{3,}|\*{3,})\s*$/.test(line)) { output.append(make('hr')); i++; continue; }
  if (listItem(line)) {
   const ordered = /^\s*\d/.test(line), list = make(ordered ? 'ol' : 'ul');
   if (ordered) list.setAttribute('start', line.trim().match(/^\d+/)[0]);
   while (i < lines.length && listItem(lines[i]) && /^\s*\d/.test(lines[i]) === ordered) {
    const item = make('li'); inline(item, lines[i++].replace(/^\s*(?:[-+*]|\d+[.)])\s+/, '')); list.append(item);
   }
   output.append(list); continue;
  }
  if (/^\s*>/.test(line)) { const quote = make('blockquote'); inline(quote, line.replace(/^\s*>\s?/, '')); output.append(quote); i++; continue; }
  const p = make('p'), content = [line]; i++;
  while (i < lines.length && !special(lines[i], lines[i + 1])) content.push(lines[i++]);
  inline(p, content.join('\n')); output.append(p);
 }
 return output;
}
if (typeof module !== 'undefined' && module.exports) module.exports = {renderKnowledgeMarkdown};
