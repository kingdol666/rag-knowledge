"""Recompute descriptive counts, Wilson intervals and paired records."""
from pathlib import Path
import csv
import json
import math

root = Path(__file__).resolve().parents[2]
frozen = json.loads((root / 'review/experiment-redesign-20261101/artifacts/final_bench/s4_traces_final.json').read_text(encoding='utf-8'))
follow = json.loads((root / 'paper-kbs/figures/fig_ladder_20261112_snapshot.json').read_text(encoding='utf-8'))
arms = ['A0', 'A0f', 'A0h', 'PD', 'A1b', 'A2', 'A3', 'A1-readall']
def collect(raw):
    return {a: {r['qid']: bool(r['gold_hit']) for r in rs if not r['is_refusal']} for a,rs in raw.items()}
base, later = collect(frozen), collect(follow)
def wilson(k, n):
    z=1.959963984540054; p=k/n; d=1+z*z/n
    center=(p+z*z/(2*n))/d; half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return center-half, center+half
def paired(a,b):
    assert a.keys() == b.keys()
    wins=sum(a[q] and not b[q] for q in a); losses=sum(b[q] and not a[q] for q in a)
    n=wins+losses
    p=min(1., 2*sum(math.comb(n,k) for k in range(min(wins,losses)+1))/2**n)
    return wins,losses,p
out=[]
for a in arms:
    assert len(base[a]) == 72
    k=sum(base[a].values()); lo,hi=wilson(k,72)
    if a in later:
        assert base[a].keys() == later[a].keys()
        m=sum(later[a].values()); agreement=sum(base[a][q]==later[a][q] for q in base[a])
        followtext=f'{m}/72'; agree=f'{agreement}/72'
    else: followtext=agree='--'
    out.append([a,k,f'{100*lo:.1f}',f'{100*hi:.1f}',followtext,agree])
expected=[37,45,52,46,39,25,33,72]
assert [r[1] for r in out] == expected
with (root/'paper-kbs/figures/experiment_arm_summary_20261112.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['arm','frozen_hits','wilson_low_pct','wilson_high_pct','followup_hits','agreement']); w.writerows(out)
lines=[r'\begin{table*}[t]',r'\centering\small',r'\caption{Gold-string containment on 72 in-domain questions: frozen aggregate and same-question follow-up. Wilson intervals describe the frozen counts; follow-up agreement is the number of questions whose hit status agrees with the frozen record. Read-all follow-up was incomplete. Arms differ in more than one component and some reference lookups may use the gold domain.}',r'\label{tab:s-arm-data}',r'\begin{tabular}{lrrrrr}',r'\toprule',r'Configuration & Frozen & Frozen rate & Wilson 95\% CI & Follow-up & Agreement \\',r'\midrule']
for a,k,lo,hi,fol,agree in out:
    a = a.replace('A1-readall','Read-all')
    lines.append(f'{a} & {k}/72 & {k/72*100:.1f}\\% & [{lo}, {hi}]\\% & {fol} & {agree} '+r'\\')
lines.extend([r'\bottomrule',r'\end{tabular}',r'\end{table*}'])
lines.extend([r'\begin{table*}[t]',r'\centering\small',r'\caption{Exploratory paired gold-string containment records (two-sided exact binomial/McNemar values, unadjusted). The follow-up repeats the same questions and is not an independent sample. The lookup and configuration limitations of Table S12 apply.}',r'\label{tab:s-paired-data}',r'\begin{tabular}{llrrr}',r'\toprule',r'Run & Contrast & First only & Second only & $p$ \\',r'\midrule'])
for name,data in [('Frozen',base),('Follow-up',later)]:
    for a,b in [('A0h','A1b'),('A0h','PD')]:
        x,y,p=paired(data[a],data[b])
        lines.append(f'{name} & {a} vs. {b} & {x} & {y} & {p:.5f} '+r'\\')
lines.extend([r'\bottomrule',r'\end{tabular}',r'\end{table*}'])
target=root/'paper-kbs/tex/journal_20p/supplementary-arm-tables.tex'
target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(', '.join(map(str,row)) for row in out))
