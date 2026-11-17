"""Export the exact main-manuscript figure captions and table titles."""
from pathlib import Path
import re

base = Path(__file__).resolve().parents[1]
src = base / 'tex' / 'journal_20p'
aux = (src / 'hmrs_kbs.aux').read_text(encoding='utf-8')
numbers = {m.group(1): (int(m.group(2)), int(m.group(3))) for m in re.finditer(
    r'\\newlabel\{((?:fig|tab):[^}]+)\}\{\{(\d+)\}\{(\d+)\}', aux)}
rows = []
for path in sorted(src.glob('n*.tex')):
    text = path.read_text(encoding='utf-8')
    for match in re.finditer(r'\\begin\{(figure\*?|table\*?)\}(.*?)\\end\{\1\}', text, re.S):
        body = match.group(2)
        label = re.search(r'\\label\{((?:fig|tab):[^}]+)\}', body)
        caption = re.search(r'\\caption\{', body)
        if not label or not caption or label.group(1) not in numbers:
            continue
        start = caption.end()
        depth = 1
        for i in range(start, len(body)):
            if body[i] == '{' and body[i - 1] != '\\': depth += 1
            if body[i] == '}' and body[i - 1] != '\\': depth -= 1
            if depth == 0: break
        name = label.group(1)
        number, page = numbers[name]
        rows.append((name.startswith('tab:'), number, page, path.name, body[start:i].strip()))
out = ['# 图题、图注和表题（论文原文）', '',
       '编号和页码来自本次双栏 PDF。以下保留原始 LaTeX 写法；插图、变量与引用以论文源文件为准。', '']
for is_table, number, page, source, caption in sorted(rows):
    out += [f"## {'表' if is_table else '图'} {number}（第 {page} 页）", '',
            f'源文件：`{source}`', '', '```latex', caption, '```', '']
target = base / 'review' / 'KBS-FIGURE-TABLE-CAPTIONS-20261112.md'
target.write_text('\n'.join(out), encoding='utf-8')
print(f'{target}: {len(rows)} captions')
