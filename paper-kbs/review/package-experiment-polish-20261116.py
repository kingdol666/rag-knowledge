"""Build a portable Overleaf source archive for the experiment revision."""
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'paper-kbs/tex/journal_20p'
DST = ROOT / 'paper-kbs/overleaf-experiment-polish-20261116'
ZIP = ROOT / 'paper-kbs/HMRS-Overleaf-experiment-polish-20261116.zip'
if DST.exists():
    raise SystemExit(f'Refusing to overwrite existing package directory: {DST}')
DST.mkdir(parents=True)
queue = ['main_20p.tex', 'supplementary.tex']
seen = set()
while queue:
    name = queue.pop()
    if name in seen:
        continue
    path = SRC / name
    if not path.exists():
        raise SystemExit(f'Missing TeX input: {path}')
    seen.add(name)
    text = path.read_text(encoding='utf-8')
    for include in re.findall(r'\\input\{([^}]+)\}', text):
        queue.append(include if include.endswith('.tex') else include + '.tex')
    for include in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', text):
        base = SRC / 'figs' / include
        candidates = [base] if base.suffix else [base.with_suffix(x) for x in ('.pdf', '.png', '.jpg')]
        figure = next((p for p in candidates if p.exists()), None)
        if figure is None:
            raise SystemExit(f'Missing figure {include} in {name}')
        target = DST / figure.relative_to(SRC)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(figure, target)
extras = {'refs.bib', 'refs_new_verified.bib', 'main_20p.pdf', 'supplementary.pdf', 'supplementary-inventory.pdf', 'supp_traces_followup.csv', 'supp_traces_frozen.csv', 'supp_traces_floor.csv'}
for name in sorted(seen | extras):
    shutil.copy2(SRC / name, DST / name)
editable = ROOT / 'paper-kbs/figure-reconstruction-20261116'
if editable.exists():
    for f in editable.rglob('*.drawio'):
        target = DST / 'editable-figures' / f.relative_to(editable)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
draw = SRC / 'figs/fig_tiered_drawio_20261116.drawio'
if draw.exists():
    (DST / 'editable-figures').mkdir(exist_ok=True)
    shutil.copy2(draw, DST / 'editable-figures' / draw.name)
for script in ('build_fig_r3_content_followup.py', 'build_fig_ladder_optimization.py'):
    f = SRC / 'figs' / script
    if f.exists():
        shutil.copy2(f, DST / 'figs' / script)
shutil.copy2(ROOT / 'paper-kbs/review/EXPERIMENT-EVIDENCE-AUDIT-20261116.md', DST / 'EXPERIMENT-EVIDENCE-AUDIT-20261116.md')
(DST / 'README.txt').write_text('Overleaf: upload ZIP, set main_20p.tex as main document, use pdfLaTeX and BibTeX. supplementary.tex is a separate document. The 20-page, two-column PDF is a review preview; consult the journal author guide for current submission requirements. Author details and declarations need author verification. See EXPERIMENT-EVIDENCE-AUDIT-20261116.md for study limitations.\n', encoding='utf-8')
if ZIP.exists():
    raise SystemExit(f'Refusing to overwrite existing archive: {ZIP}')
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(DST.rglob('*')):
        if path.is_file():
            archive.write(path, path.relative_to(DST))
with zipfile.ZipFile(ZIP) as archive:
    assert archive.testzip() is None
print(f'{ZIP} | tex files={len(seen)} | figures={len(list((DST / "figs").glob("*.pdf")))} | size={ZIP.stat().st_size}')
