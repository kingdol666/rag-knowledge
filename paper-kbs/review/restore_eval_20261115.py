"""Restore the 9 evaluation-section files rewritten on 2026-11-15 11:27-11:37
back to the accepted 2026-11-13 state, using the KBS-Revision-20261112 review
package (refreshed 2026-11-13 02:31, verified to carry the post-acceptance
state) as the restore source.

The rewritten versions are backed up first so today's integration of the
100-paper rerun numbers is not lost.
"""
from pathlib import Path
import shutil

base = Path(__file__).resolve().parents[1]
live = base / 'tex' / 'journal_20p'
pkg = base / 'KBS-Revision-20261112'
stamp = '20261115'
backup = base / 'review' / f'backup-eval-rewrite-{stamp}'

files = ['n8a_eval.tex', 'n8b_eval.tex', 'n8c_eval.tex', 'n9_discussion.tex',
         'n10_threats.tex', 'n11_conclusion.tex', 'main_20p.tex',
         'supplementary.tex', 'supplementary-arm-tables.tex',
         'main_20p.pdf', 'supplementary.pdf']

backup.mkdir(parents=True, exist_ok=True)
for name in files:
    shutil.copy2(live / name, backup / name)

restored = []
for name in files:
    shutil.copy2(pkg / name, live / name)
    restored.append(name)

# One cosmetic comment line landed in n8c after the last package refresh
# (label-map wording); re-apply it so source and history stay consistent.
n8c = live / 'n8c_eval.tex'
text = n8c.read_text(encoding='utf-8')
text = text.replace(
    '%%   sec:e5 -> E6 | sec:sysarms -> E7 | sec:e6 -> E8 | sec:e7+sec:e8 -> E9',
    '%%   sec:e5 -> E6 | sec:sysarms -> E7 | sec:e6 -> E8 | sec:e7 -> E9 '
    '(merges former E7+E8)')
n8c.write_text(text, encoding='utf-8', newline='\n')

print(f'backed up {len(files)} files -> {backup.name}')
print(f'restored {len(restored)} files from {pkg.name}')
