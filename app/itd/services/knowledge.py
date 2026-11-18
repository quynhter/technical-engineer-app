"""One canonical set of knowledge sources for every transport."""
from pathlib import Path

from .. import knowledge
from ..integrity import manifest_entries, verify_files
from ..paths import ROOT


def validate_canonical(root):
    root = Path(root).resolve()
    if root == (ROOT / 'app/knowledge').resolve():
        entries = manifest_entries(ROOT / 'app/knowledge-integrity.sha256')
        verify_files(ROOT, entries)
        expected = {name.removeprefix('app/knowledge/') for name in entries}
        actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and p.suffix not in ('.db', '.sqlite', '.sqlite3')}
        if actual != expected:
            raise ValueError('Состав базы знаний не соответствует манифесту целостности')


def execute(ctx, command, args):
    root = args.root
    validate_canonical(root)
    index = knowledge.default_index(ctx.database)
    if command in ('knowledge-status', 'knowledge-validate'):
        return knowledge.status(root, index)
    if command == 'knowledge-index':
        return knowledge.build_index(root, index)
    if command == 'knowledge-show':
        return knowledge.show(root, index, args.id)
    if command == 'knowledge-export':
        return knowledge.export_entries(root, args.output)
    return knowledge.search(root, index, args.query, corpus=args.corpus, kind=args.kind,
                            clause=args.clause, work=args.work, form=args.form, limit=args.limit)
