'use strict';
(() => {
 const dialog = createWorkspaceDialog('knowledge-dialog');
 const results = document.getElementById('knowledge-results');
 const message = document.getElementById('knowledge-message');
 const query = document.getElementById('knowledge-query');
 const corpus = document.getElementById('knowledge-corpus');
 const button = document.getElementById('knowledge-search');
 let generation = 0;
 const notice = 'Подготовленные ИИ выдержки. Перед применением проверьте оригинал, редакцию и условия. Связанные формы требуют выбора по составу работ.';
 const corpusNames = {sp77:'СП 77.13330.2016', i_1_13_07:'И 1.13-07', rd78_145_93:'РД 78.145-93', prikaz_344pr:'Приказ №344/пр'};
 const node = (tag, text) => { const n = document.createElement(tag); n.textContent = text; return n; };
 async function request(params) {
  const response = await fetch('/api/knowledge' + (params ? '?' + params : ''), {headers: {'X-ITD-Token': token}});
  const data = await response.json();
  if (!response.ok) throw Error(data.error || 'Не удалось прочитать базу знаний');
  return data;
 }
 async function find() {
  const current = ++generation;
  button.disabled = true;
  results.replaceChildren(); window.ITDDesign?.setLoading(true,results); message.textContent = 'Поиск…';
  try {
   const params = new URLSearchParams({query: query.value});
   if (corpus.value) params.set('corpus', corpus.value);
   const data = await request(params);
   if (current !== generation) return;
   message.textContent = data.count ? `Показано: ${data.count}, не более 20. ${notice}` : 'Ничего не найдено. Попробуйте основу слова, например «изоляц», или другой набор.';
   for (const hit of data.hits) {
    const article = node('article', ''); article.className = 'knowledge-hit';
    article.append(node('h3', `${hit.doc_id} — ${hit.clause}`));
    const content = node('div', ''); content.className = 'knowledge-text';
    let preview = hit.excerpt;
    // Не показываем обрезанную последнюю строку Markdown-таблицы как целую норму.
    if (hit.kind === 'chunk' && preview.length >= 800 && preview.lastIndexOf('\n') > 0) preview = preview.slice(0, preview.lastIndexOf('\n'));
    content.append(renderKnowledgeMarkdown(preview)); article.append(content);
    const more = node('button', 'Полный текст и условия'); more.type = 'button'; more.className = 'secondary';
    more.addEventListener('click', async () => {
     more.disabled = true;
     try {
      const full = await request(new URLSearchParams({id: hit.id}));
      content.replaceChildren(renderKnowledgeMarkdown(full.text));
      if (full.metadata.condition) article.append(node('h4', 'Условия применения'), node('p', full.metadata.condition));
      if (full.itd_forms.length) article.append(node('h4', 'Связанные формы'), renderKnowledgeMarkdown(full.itd_forms.map(form => '- ' + form).join('\n')));
       more.remove();
     } catch (error) { message.textContent = error.message; more.disabled = false; }
    });
    article.append(more); results.append(article);
   }
  } catch (error) { if (current === generation) message.textContent = error.message; }
  finally { if (current === generation) {button.disabled = false;window.ITDDesign?.setLoading(false,results);} }
 }
 document.addEventListener('click', async event => {
  if (!event.target.closest('[data-open-knowledge]')) return;
  dialog.open({focus:query}); message.textContent = 'Чтение каталога…';
  try {
   const data = await request();
   const selected = corpus.value;
   corpus.replaceChildren(new Option('Все наборы', ''));
   for (const [key] of Object.entries(data.corpora)) corpus.add(new Option(corpusNames[key] || key, key));
   corpus.value = selected;
   enhanceSelect(corpus);
   message.textContent = `${data.entries} записей. ${notice}`;
  } catch (error) { message.textContent = error.message; }
 });
 button.addEventListener('click', find);
 query.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); find(); } });
})();
