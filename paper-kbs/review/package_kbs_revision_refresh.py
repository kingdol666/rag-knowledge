"""Refresh the flat review package from the canonical tex/journal_20p sources.

Same intent as package_kbs_revision.py / package_kbs_20p_20261112.py but reads
main_20p.pdf directly (the hmrs_kbs.pdf naming those scripts expect is stale),
so a rerun cannot pull an outdated preview.
"""
from pathlib import Path
import re
import shutil

base = Path(__file__).resolve().parents[1]
src = base / 'tex' / 'journal_20p'
dst = base / 'KBS-Revision-20261112'

names = (['main_20p.tex', 'supplementary.tex', 'supplementary-arm-tables.tex']
         + sorted(p.name for p in sorted(src.glob('n*.tex')))
         + ['refs.bib', 'refs_new_verified.bib', 'highlights.tex'])
copied = []
for name in names:
    s = src / name
    if not s.exists():
        continue
    text = s.read_text(encoding='utf-8')
    if name in ('main_20p.tex', 'supplementary.tex'):
        text = text.replace('\\graphicspath{{figs/}}', '')
    (dst / name).write_text(text, encoding='utf-8')
    copied.append(name)

alltex = '\n'.join((dst / n).read_text(encoding='utf-8')
                   for n in copied if n.endswith('.tex'))
figures = list(dict.fromkeys(
    re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', alltex)))
missing = []
for fig in figures:
    f = src / 'figs' / (fig + '.pdf')
    if f.exists():
        shutil.copy2(f, dst / (fig + '.pdf'))
    else:
        missing.append(fig)

for a, b in [('main_20p.pdf', 'main_20p.pdf'),
             ('main_20p.pdf', 'revision-preview.pdf'),
             ('supplementary.pdf', 'supplementary.pdf'),
             ('supplementary-inventory.pdf', 'supplementary-inventory.pdf')]:
    shutil.copy2(src / a, dst / b)

print(f'{len(copied)} tex/bib files, {len(figures) - len(missing)} figure PDFs, '
      f'missing figures: {missing}')
