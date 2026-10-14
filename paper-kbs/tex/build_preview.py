import io, re, os, subprocess, tempfile

os.chdir(os.path.dirname(os.path.abspath(__file__)))
tex = io.open('main.tex', encoding='utf-8').read()

# 1) replace \cite{a,b} with [a, b] so pandoc keeps them as plain text
def cites(m):
    keys = [k.strip() for k in m.group(1).split(',')]
    return '[' + ', '.join(keys) + ']'
pre = re.sub(r'\\cite\{([^}]+)\}', cites, tex)
# 2) inline \input{tab_agentic} BEFORE macro replacement
tab = io.open('tab_agentic.tex', encoding='utf-8').read()
pre = pre.replace('\\input{tab_agentic}', tab)
# 3) checkmarks / dashes for table cells (drop the macros first)
pre = re.sub(r'\\newcommand\{\\yes\}\{[^}]*\}', '', pre)
pre = re.sub(r'\\newcommand\{\\no\}\{[^}]*\}', '', pre)
pre = pre.replace('\\yes', '✓').replace('\\no', '--')
pre = pre.replace('\\checkmark', '✓')
# math commands pandoc chokes on, replace in source
pre = pre.replace('$^\\circ$C', ' °C').replace('$^\\circ$C', ' °C')
pre = pre.replace('\\circ C', ' °C').replace('^\\circ', '')
pre = pre.replace('$\\|$', '‖')
pre = pre.replace('$\\geq$', '≥').replace('$\\leq$', '≤')
pre = pre.replace('\\geq', '≥').replace('\\leq', '≤')
pre = pre.replace('\\approx', '≈').replace('\\delta', 'δ')
pre = pre.replace('\\mathit{best}', 'best')
pre = pre.replace('$p$', 'p')
# 4) figure includes → markdown images pointing at ../figures PNGs
def figimg(m):
    return f'![{m.group(1)}](../figures/{m.group(1)}.png)'
pre = re.sub(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', figimg, pre)
# 5) drop commented lines (pandoc handles them, but keep clean)
with tempfile.NamedTemporaryFile('w', suffix='.tex', delete=False,
                                 encoding='utf-8') as f:
    f.write(pre)
    tmp = f.name

import pypandoc
out = pypandoc.convert_file(tmp, 'gfm', format='latex',
                            extra_args=['--wrap=none'])
os.unlink(tmp)

title = re.search(r'\\title\{(.+?)\}', tex, re.S).group(1)
title = re.sub(r'\s+', ' ', title)
banner = (f"---\ntitle: \"{title}\"\n"
          "subtitle: \"Knowledge-Based Systems submission — readable preview. "
          "The LaTeX source (tex/main.tex) is the manuscript of record; "
          "figures live in tex/figs/.\"\n"
          "---\n\n")
s = banner + out
s = s.replace('$`\\to`$', '→').replace('$`\\geq`$', '≥').replace('$`\\leq`$', '≤')
s = s.replace('$`\\pm`$', '±').replace('$`\\approx`$', '≈').replace('$`\\times`$', '×')
s = s.replace("$`-8^\\circ`$C", "-8 °C").replace("$`206\\to180^\\circ`$C", "206→180 °C")
s = re.sub(r'\$`([^`]+)`\$', r'`\1`', s)
s = s.replace('<span class="smallcaps">', '**').replace('</span>', '**')
s = s.replace('→**', '→').replace('≈**', '≈')  # pandoc math-boundary quirk
s = re.sub(r'</?div[^>]*>', '', s)
io.open('main.md', 'w', encoding='utf-8').write(s)
print('wrote main.md', len(s), 'chars')
