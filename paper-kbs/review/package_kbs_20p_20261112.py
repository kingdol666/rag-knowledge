"""Make a self-contained, flat 20-page review package without overwriting history."""
from pathlib import Path
import re
import shutil

base=Path(__file__).resolve().parents[1]
src=base/'tex/journal_20p'
dst=base/'KBS-Revision-20261112-20p'
dst.mkdir(exist_ok=True)
names=['main_20p.tex','supplementary.tex','supplementary-arm-tables.tex',
       *[p.name for p in sorted(src.glob('n*.tex'))], 'refs.bib','refs_new_verified.bib','highlights.tex']
for name in names:
    text=(src/name).read_text(encoding='utf-8')
    if name in ('main_20p.tex','supplementary.tex'):
        text=text.replace('\\graphicspath{{figs/}}','')
    (dst/name).write_text(text,encoding='utf-8')
alltext='\n'.join((dst/n).read_text(encoding='utf-8') for n in names if n.endswith('.tex'))
figures=list(dict.fromkeys(re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',alltext)))
for fig in figures:
    shutil.copy2(src/'figs'/f'{fig}.pdf',dst/f'{fig}.pdf')
for source,target in [('hmrs_kbs.pdf','revision-preview.pdf'),('supplementary.pdf','supplementary.pdf'),
                      ('supplementary-inventory.pdf','supplementary-inventory.pdf'),
                      ('revision-20261112.sha256','revision-20261112.sha256'),
                      ('hmrs_kbs.bbl','main_20p.bbl')]:
    shutil.copy2(src/source,dst/target)
for name in ['build_fig_miss_overlap.py','build_experiment_tables_20261112.py','fig_miss_overlap_data.csv','experiment_arm_summary_20261112.csv',
             'build_question_audit_20261112.py','experiment_question_audit_20261112.csv']:
    shutil.copy2(base/'figures'/name,dst/name)
shutil.copy2(base/'review/KBS-FIGURE-TABLE-CAPTIONS-20261112.md',dst/'FIGURE-TABLE-CAPTIONS.md')
print(f'{len(names)} source files, {len(figures)} figure PDFs in {dst}')
