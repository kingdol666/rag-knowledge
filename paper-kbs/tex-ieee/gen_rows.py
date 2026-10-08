import io, re
s = io.open('../tex/tab_agentic.tex', encoding='utf-8').read()
lines = []
for ln in s.splitlines():
    t = ln.strip()
    if t.startswith('\\begin{tabular}') or t.startswith('\\end{tabular}'):
        continue
    if t in ('\\toprule', '\\bottomrule', '\\midrule'):
        continue
    if t.startswith('Arm & Q & Wall'):
        continue
    lines.append(ln)
body = '\n'.join(lines).strip()
io.open('tab_agentic_rows.tex', 'w', encoding='utf-8').write(body)
print('rows written')
