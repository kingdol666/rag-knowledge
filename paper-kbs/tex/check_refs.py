import io, re, os
tex = io.open('main.tex', encoding='utf-8').read()
bib = io.open('refs.bib', encoding='utf-8').read()
cited = set()
for grp in re.findall(r'\\cite\{([^}]+)\}', tex):
    for k in grp.split(','):
        cited.add(k.strip())
defined = set(re.findall(r'@\w+\{([^,]+),', bib))
print('cited keys:', len(cited))
missing = sorted(k for k in cited if k not in defined)
print('MISSING from refs.bib:', missing)
unused = sorted(k for k in defined if k not in cited)
print('defined-but-uncited (ok):', unused)
labels = set(re.findall(r'\\label\{([^}]+)\}', tex))
refs = set(re.findall(r'\\ref\{([^}]+)\}', tex))
print('refs missing label:', sorted(r for r in refs if r not in labels))
figs = set(re.findall(r'\\includegraphics\[[^\]]*\]\{([^}]+)\}', tex))
for f in sorted(figs):
    ok = os.path.exists(os.path.join('figs', f + '.pdf')) or \
         os.path.exists(os.path.join('figs', f))
    print('fig', f, 'exists:', ok)
for bad in ('TODO', 'XXX', 'PLACEHOLDER'):
    n = tex.count(bad)
    if n:
        print('leftover', bad, n)
