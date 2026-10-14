# -*- coding: utf-8 -*-
"""Structural audit: env balance + label census per file."""
import re
from pathlib import Path

for f in sorted(Path('.').glob('n*.tex')):
    s = f.read_text(encoding='utf-8')
    ops = re.findall(r'\\(begin|end)\{(figure|table)\*?\}', s)
    bal = {}
    for kind, env in ops:
        key = env
        bal[key] = bal.get(key, 0) + (1 if kind == 'begin' else -1)
    labels = re.findall(r'\\label\{((?:tab|fig|sec):[^}]*)\}', s)
    tabs = [l for l in labels if l.startswith('tab:')]
    figs = [l for l in labels if l.startswith('fig:')]
    status = 'OK ' if all(v == 0 for v in bal.values()) else 'UNBALANCED ' + str(bal)
    print(f'{f.name:22} {status:22} tab_labels={tabs}')
    if figs:
        print(f'{"":22} fig_labels={figs}')
