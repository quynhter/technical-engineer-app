import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(process.env.ITD_NODE_MODULES
  ? path.join(process.env.ITD_NODE_MODULES, '..', 'itd-resolver.cjs') : import.meta.url);
const { FileBlob, SpreadsheetFile } = await import(require.resolve('@oai/artifact-tool'));
const payload = JSON.parse(await fs.readFile(process.argv[2], 'utf8'));
const output = process.argv[3];
const previewDir = process.argv[4];
const literal = value => typeof value === 'string' && value.startsWith('=') ? "'" + value : value;
const rows = payload.rows.map(row => row.map(literal));
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(payload.template_path));
const sheet = wb.worksheets.getItemAt(0);
const last = Math.max(8, rows.length + 7);
sheet.getRange('B3').values = [[literal(payload.object_name)]];
sheet.getRange('B4').values = [[literal(payload.section_label)]];
sheet.getRange('B3:I4').format.wrapText = true;
sheet.getRange('A3:I3').format.rowHeight = payload.layout.object_height;
sheet.getRange('A4:I4').format.rowHeight = payload.layout.section_height;
sheet.getRange('A6:I6').format.rowHeight = payload.layout.header_height;
// Extend the actual template body style before filling values.
for (let index = 9; index <= last; index++) {
  sheet.getRange(`A${index}:I${index}`).copyFrom(sheet.getRange('A8:I8'), 'all');
}
if (rows.length) {
  sheet.getRange(`A8:I${last}`).values = rows;
  sheet.getRange(`A8:I${last}`).format.wrapText = true;
  sheet.getRange(`G8:H${last}`).setNumberFormat('General');
  for (const col of ['A','B','C','D','E','F','I']) {
    sheet.getRange(`${col}8:${col}${last}`).setNumberFormat('@');
  }
} else {
  sheet.getRange('C8').values = [['Ресурсы пока не внесены']];
  sheet.getRange('A8:I8').format.rowHeight = 28;
}
rows.forEach((_, index) => {
  sheet.getRange(`A${index + 8}:I${index + 8}`).format.rowHeight = payload.layout.row_heights[index];
});
sheet.freezePanes.unfreeze();
sheet.freezePanes.freezeRows(7);
wb.recalculate();
const check = await wb.inspect({ kind: 'table', range: `${sheet.name}!F6:I10`,
  include: 'values,formulas', tableMaxRows: 4, tableMaxCols: 4, maxChars: 1200 });
console.log(check.ndjson);
const errors = await wb.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',
  options: { useRegex: true, maxResults: 10 }, maxChars: 800 });
console.log(errors.ndjson);
if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  for (const [name, range] of [['overview', `A1:I${Math.min(last, 12)}`]]) {
    const preview = await wb.render({ sheetName: sheet.name, range, scale: 1, format: 'png' });
    await fs.writeFile(path.join(previewDir, name + '.png'), new Uint8Array(await preview.arrayBuffer()));
  }
}
await (await SpreadsheetFile.exportXlsx(wb)).save(output);
