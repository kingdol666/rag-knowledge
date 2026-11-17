"""Create a flat, review-only Elsevier LaTeX package."""
from pathlib import Path
import re
import shutil
from docx import Document

base = Path(__file__).resolve().parents[1]
src = base / 'tex' / 'journal_20p'
dst = base / 'KBS-Revision-20261112'
dst.mkdir(exist_ok=True)
names = ['main_20p.tex', *[p.name for p in sorted(src.glob('n*.tex'))],
         'refs.bib', 'refs_new_verified.bib', 'highlights.tex']
for name in names:
    shutil.copy2(src / name, dst / name)
main = dst / 'main_20p.tex'
main.write_text(main.read_text(encoding='utf-8').replace('\\graphicspath{{figs/}}', ''), encoding='utf-8')
shutil.copy2(src / 'hmrs_kbs.bbl', dst / 'main_20p.bbl')
shutil.copy2(src / 'hmrs_kbs.pdf', dst / 'revision-preview.pdf')
shutil.copy2(src / 'supplementary.pdf', dst / 'supplementary.pdf')
shutil.copy2(src / 'supplementary-inventory.pdf', dst / 'supplementary-inventory.pdf')
shutil.copy2(src / 'revision-20261112.sha256', dst / 'revision-20261112.sha256')
for name in ('KBS-REVISION-20261112.md','KBS-FIGURE-TABLE-CAPTIONS-20261112.md'):
    shutil.copy2(base / 'review' / name, dst / name)
all_tex='\n'.join((src / n).read_text(encoding='utf-8') for n in names if n.endswith('.tex'))
figures = list(dict.fromkeys(re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', all_tex)))
for fig in figures:
    shutil.copy2(src / 'figs' / (fig + '.pdf'), dst / (fig + '.pdf'))
highlights=(src / 'highlights.tex').read_text(encoding='utf-8')
items=re.findall(r'\\item\s+(.+)', highlights)
doc=Document()
doc.add_heading('Highlights', 0)
for item in items:
    doc.add_paragraph(item.replace('\\%', '%'), style='List Bullet')
doc.save(dst / 'highlights.docx')
(dst / 'README.md').write_text('''# KBS 双栏修订审阅包

`revision-preview.pdf` 是由同一源稿生成的双栏预览；`main_20p.tex` 与各节、参考文献、图件均在同一文件夹，可供 Elsevier LaTeX 流程使用。`supplementary.pdf` 包含图 S1–S5 和表 S9–S10；`supplementary-inventory.pdf` 包含详细记录和表 S1–S8。图题、替换清单、证据限制和出版商要求核查见两份 KBS 说明文件。

这不是已核实符合 KBS 专属投稿要求的最终投稿包。作者姓名、机构、贡献、经费、利益冲突、AI 声明和期刊专属要求仍须确认；实验尚有金标回退及对照设计问题。旧的历史 freeze 不代表本版；`revision-20261112.sha256` 的相对路径以原 `paper-kbs/tex/journal_20p` 为基准，供原工作区核验。

图形源和绘图数据位于原工作区的 `paper-kbs/figures/`；原始实验记录仍受相应语料访问条件约束。PDF 与 LaTeX 源稿中所列图件逐项对应。
''', encoding='utf-8')
print(f'{dst}: {len(names)} text/bib files, {len(figures)} main figures')
