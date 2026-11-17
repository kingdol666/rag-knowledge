#!/usr/bin/env python3
"""Frozen A0 misses: intersection of containment by three configurations."""
from pathlib import Path
import csv
import json
from collections import Counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[2]
source = root / 'review/experiment-redesign-20261101/artifacts/final_bench/s4_traces_final.json'
out = root / 'paper-kbs/tex/journal_20p/figs'
traces = json.loads(source.read_text(encoding='utf-8'))
arms = ('A0', 'A0f', 'A0h', 'PD')
rows = {arm: {r['qid']: r for r in traces[arm] if not r['is_refusal']} for arm in arms}
assert all(len(v) == 72 for v in rows.values())
assert all(rows[a].keys() == rows['A0'].keys() for a in arms)
miss = [qid for qid, r in rows['A0'].items() if not r['gold_hit']]
patterns = Counter(tuple(bool(rows[a][qid]['gold_hit']) for a in arms[1:]) for qid in miss)
assert len(miss) == 35 and patterns == {(1, 1, 1): 8, (0, 1, 0): 7, (0, 0, 1): 1, (0, 0, 0): 19}
order = [(1, 1, 1), (0, 1, 0), (0, 0, 1), (0, 0, 0)]
csv_path = Path(__file__).with_name('fig_miss_overlap_data.csv')
with csv_path.open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['A0f_contains', 'A0h_contains', 'PD_contains', 'questions'])
    for pattern in order:
        writer.writerow([*map(int, pattern), patterns[pattern]])

plt.rcParams.update({'font.family':'sans-serif', 'font.sans-serif':['Arial','DejaVu Sans'],
    'font.size':8.5, 'axes.labelsize':8.5, 'xtick.labelsize':8.5, 'ytick.labelsize':8.5,
    'axes.linewidth':0.8, 'pdf.fonttype':42, 'ps.fonttype':42})
fig = plt.figure(figsize=(3.54, 2.38))
gs = fig.add_gridspec(2, 1, height_ratios=[2.1, 1], left=.19, right=.97, bottom=.14, top=.94, hspace=.08)
ax = fig.add_subplot(gs[0]); matrix = fig.add_subplot(gs[1], sharex=ax)
colors = ['#0072B2','#0072B2','#0072B2','#8D98A4']
bars = ax.bar(range(4), [patterns[p] for p in order], color=colors, width=.55)
ax.set_ylim(0,22); ax.set_yticks([0,5,10,15,20]); ax.set_ylabel('Questions')
ax.tick_params(axis='x', bottom=False, labelbottom=False)
ax.spines[['top','right']].set_visible(False)
for bar in bars:
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+.35, str(int(bar.get_height())), ha='center', va='bottom')
for x,p in enumerate(order):
    yy=[2-i for i,v in enumerate(p) if v]
    if len(yy)>1: matrix.plot([x,x],[min(yy),max(yy)], color='#0072B2', lw=1.1, zorder=1)
    for i,v in enumerate(p):
        matrix.scatter(x,2-i,s=26,color='#0072B2' if v else '#DCE2E8',zorder=2)
matrix.set_yticks([2,1,0],['A0f','A0h','PD']); matrix.set_ylim(-.5,2.5)
matrix.set_xticks(range(4),['All three','A0h only','PD only','None'])
matrix.tick_params(axis='both', length=0, pad=4)
for spine in matrix.spines.values(): spine.set_visible(False)
out.mkdir(exist_ok=True)
for ext in ('pdf','png'):
    fig.savefig(out / f'fig_miss_overlap.{ext}', dpi=400, facecolor='white')
print(f'{len(miss)} misses; intersections {patterns}; output {out}')
