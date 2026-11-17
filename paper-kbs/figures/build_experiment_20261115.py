#!/usr/bin/env python3
"""Build three HMRS evaluation figures from archived per-question records.

Produces journal-size vector PDFs, 300-dpi previews, data CSVs and provenance.
No model-generated/estimated result data. Run from any working directory.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'paper-kbs/tex/journal_20p/figs'
DATA = ROOT / 'paper-kbs/figures/experiment_20261115_data'
FROZEN = ROOT / 'review/experiment-redesign-20261101/artifacts/final_bench/s4_traces_final.json'
FOLLOW = ROOT / 'review/experiment-redesign-20261101/artifacts/replication_bench_20261112/s4_traces_r3.json'
SCORES = ROOT / 'paper-kbs/experiments/results/exp1_retrieval.json'
ORDER = ROOT / 'paper-kbs/experiments/results/exp5_judge_filter.json'
GOLD = ROOT / 'paper-kbs/experiments/kbcommon.py'
BLUE = '#35689A'
ORANGE = '#C47727'
DARK = '#383838'
GREY = '#D5D9DD'

plt.rcParams.update({
    'font.family':'Arial', 'font.size':9, 'axes.labelsize':9,
    'xtick.labelsize':8.5, 'ytick.labelsize':8.5, 'legend.fontsize':8.5,
    'axes.linewidth':0.75, 'axes.edgecolor':DARK, 'text.color':DARK,
    'axes.labelcolor':DARK, 'xtick.color':DARK, 'ytick.color':DARK,
    'xtick.direction':'out', 'ytick.direction':'out',
    'xtick.major.width':0.75, 'ytick.major.width':0.75,
    'pdf.fonttype':42, 'ps.fonttype':42, 'savefig.facecolor':'white',
    'figure.facecolor':'white', 'savefig.dpi':300,
})


def wilson(k:int,n:int)->tuple[float,float]:
    z=1.959963984540054
    p=k/n
    den=1+z*z/n
    c=(p+z*z/(2*n))/den
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return (100*max(0,c-h),100*min(1,c+h))


def read(path:Path):
    return json.loads(path.read_text(encoding='utf-8'))


def subset(raw:dict,arm:str):
    rows=[r for r in raw[arm] if not r.get('is_refusal',False)]
    if len(rows)!=72 or len({r['qid'] for r in rows})!=72:
        raise ValueError(f'{arm} requires 72 unique non-refusal rows, got {len(rows)}')
    return rows


def decorate(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(length=3, pad=3)
    ax.set_axisbelow(True)
    ax.grid(axis='x', color=GREY, linewidth=0.45)


def save(fig,name):
    OUT.mkdir(parents=True,exist_ok=True)
    fig.savefig(OUT/f'{name}.pdf', facecolor='white')
    fig.savefig(OUT/f'{name}.png',dpi=300,facecolor='white')
    plt.close(fig)


def write_csv(name, rows, fields):
    DATA.mkdir(parents=True,exist_ok=True)
    with (DATA/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def point_ci(ax, x, y, lo, hi, color, marker):
    ax.errorbar(x,y,xerr=[[max(0,x-lo)],[max(0,hi-x)]], fmt=marker,
                mfc=color,mec=color,ms=5.5,ecolor=color,elinewidth=1,
                capsize=2.5,capthick=1,linestyle='none',zorder=3)


def route(frozen):
    arms=('A0','A3')
    datasets={a:subset(frozen,a) for a in arms}
    assert {r['qid'] for r in datasets['A0']}=={r['qid'] for r in datasets['A3']}
    records=[]
    fig,axes=plt.subplots(1,2,figsize=(7.0,1.95))
    fig.subplots_adjust(left=.08,right=.965,top=.81,bottom=.30,wspace=.29)
    for ax,field,label,panel in zip(axes,['route_correct','gold_hit'],
              ['Gold-domain selection (%)','Gold-string containment (%)'],['(a)','(b)']):
        for i,a in enumerate(arms):
            rows=datasets[a];k=sum(bool(r[field]) for r in rows);lo,hi=wilson(k,72);x=k/72*100
            records.append({'arm':a,'metric':field,'n':72,'hits':k,'percent':x,'wilson_low':lo,'wilson_high':hi})
            point_ci(ax,x,i,lo,hi,BLUE if a=='A0' else ORANGE,'o' if a=='A0' else 's')
            ax.text(lo-2 if x>90 else min(98,hi+2),i,f'{k}/72',fontsize=8.5,ha='right' if x>90 else 'left',va='center')
        ax.set_xlim(0,103);ax.set_xticks([0,25,50,75,100]);ax.set_ylim(1.6,-.6)
        ax.set_yticks([0,1],arms);ax.set_xlabel(label);decorate(ax)
        ax.text(0,1.13,panel,transform=ax.transAxes,fontweight='bold',fontsize=9.5)
    write_csv('route_summary.csv',records,['arm','metric','n','hits','percent','wilson_low','wilson_high'])
    save(fig,'fig_exp_route')


def content(frozen,follow):
    arms=['A0','A0f','A0h','PD','A1b','A2','A3','A1-readall']
    labels=['A0','A0f','A0h','PD','A1b','A2','A3','Read-all']
    records=[]
    fig=plt.figure(figsize=(7,3.25))
    gs=fig.add_gridspec(1,2,width_ratios=[4.9,1.5],left=.10,right=.98,top=.84,bottom=.16,wspace=.03)
    ax=fig.add_subplot(gs[0]); tab=fig.add_subplot(gs[1],sharey=ax);tab.axis('off')
    for i,a in enumerate(arms):
        f=subset(frozen,a); k=sum(bool(r['gold_hit']) for r in f);lo,hi=wilson(k,72)
        point_ci(ax,k/72*100,i-.13,lo,hi,BLUE,'o')
        records.append({'arm':a,'run':'frozen','n':72,'hits':k,'percent':k/72*100,'wilson_low':lo,'wilson_high':hi})
        tab.text(.16,i-.13,f'{k}/72',ha='center',va='center',fontsize=8.5,color=BLUE)
        if a=='A1-readall':
            # Only 3 completed gold cases in follow-up: not a 72-question estimate.
            incomplete=[r for r in follow[a] if not r.get('is_refusal',False)]
            assert len(incomplete)==3
            tab.text(.74,i+.13,'incomplete',ha='center',va='center',fontsize=8.0,color=DARK)
        else:
            r=subset(follow,a)
            assert {x['qid'] for x in f}=={x['qid'] for x in r}
            k=sum(bool(x['gold_hit']) for x in r);lo,hi=wilson(k,72)
            point_ci(ax,k/72*100,i+.13,lo,hi,ORANGE,'^')
            records.append({'arm':a,'run':'same-question follow-up','n':72,'hits':k,'percent':k/72*100,'wilson_low':lo,'wilson_high':hi})
            tab.text(.74,i+.13,f'{k}/72',ha='center',va='center',fontsize=8.5,color=ORANGE)
    ax.set_xlim(0,104);ax.set_xticks([0,20,40,60,80,100]);ax.set_ylim(len(arms)-.45,-.55)
    ax.set_yticks(range(len(arms)),labels);ax.set_xlabel('Gold-string containment (%)');decorate(ax)
    tab.text(.16,-.78,'Frozen',ha='center',va='center',fontsize=8.5,fontweight='bold')
    tab.text(.74,-.78,'Follow-up',ha='center',va='center',fontsize=8.5,fontweight='bold')
    fig.legend(handles=[Line2D([0],[0],color=BLUE,marker='o',linestyle='none',markersize=5,label='Frozen'),
                        Line2D([0],[0],color=ORANGE,marker='^',linestyle='none',markersize=5,label='Same-question follow-up')],
               loc='upper left',bbox_to_anchor=(.12,.99),frameon=False,ncol=2,handletextpad=.35,columnspacing=1.5)
    write_csv('content_summary.csv',records,['arm','run','n','hits','percent','wilson_low','wilson_high'])
    save(fig,'fig_exp_content')


def verifier():
    # Archive predates project rename: qdcvr_hybrid is the logged method name.
    sys.path.insert(0,str(GOLD.parent))
    from kbcommon import QUESTIONS
    gold_doc={q['qid']:q['gold_doc_substrings'] for q in QUESTIONS}
    records=[]
    for row in read(SCORES)['rows']:
        if row.get('method') not in ('qdcvr_hybrid','hmrs_hybrid') or 'judge_scores' not in row:continue
        for path, score in row['judge_scores']['all'].items():
            gold=any(s.lower() in path.lower() for s in gold_doc[row['qid']])
            records.append({'qid':row['qid'],'candidate':path,'group':'Gold' if gold else 'Non-gold','score':score})
    groups=[[r['score'] for r in records if r['group']==group] for group in ('Gold','Non-gold')]
    assert [len(x) for x in groups]==[17,174]
    assert round(float(np.median(groups[0])),2)==.88 and round(float(np.median(groups[1])),2)==.86
    assert all(v>.5 for g in groups for v in g)
    run=read(ORDER)['rows']
    assert len(run)==16 and sum(r['filter_only']['hit'] for r in run)==15 and sum(r['judged']['hit'] for r in run)==7
    run=sorted(run,key=lambda r:int(r['qid'][1:]))
    fig,(ax,bx)=plt.subplots(1,2,figsize=(7,2.65),gridspec_kw={'width_ratios':[1,1.45]})
    fig.subplots_adjust(left=.105,right=.965,bottom=.31,top=.84,wspace=.42)
    rng=np.random.default_rng(523)
    for i,(vals,c,m) in enumerate(zip(groups,[BLUE,ORANGE],['o','s'])):
        x=rng.uniform(-.16,.16,len(vals))+i
        ax.scatter(x,vals,s=14,alpha=.55,marker=m,c=c,linewidths=0,zorder=2)
        ax.hlines(np.median(vals),i-.24,i+.24,colors=DARK,lw=1.5,zorder=3)
    ax.axhline(.5,ls='--',lw=.8,color=DARK)
    ax.text(.03,.515,'0.5 threshold',transform=ax.get_yaxis_transform(),fontsize=8,va='bottom')
    ax.set_ylim(.45,1.015);ax.set_xlim(-.55,1.55)
    ax.set_xticks([0,1],['Gold\n(n=17)','Non-gold\n(n=174)']);ax.set_ylabel('Verifier score')
    ax.spines[['top','right']].set_visible(False);ax.tick_params(length=3,pad=3)
    ax.text(0,1.09,'(a) Score archive',transform=ax.transAxes,fontweight='bold',fontsize=9)
    for y,(key,c) in enumerate([('filter_only',BLUE),('judged',ORANGE)]):
        for j,r in enumerate(run):
            hit=r[key]['hit']
            bx.scatter(j+1,y,s=36,marker='s' if key=='filter_only' else 'o',
                       facecolor=c if hit else 'white',edgecolor=c,lw=1,zorder=3)
        bx.text(17,y,f'{sum(r[key]["hit"] for r in run)}/16',va='center',ha='left',fontsize=9,fontweight='bold',color=c)
    bx.set_xlim(.3,19);bx.set_ylim(1.55,-.55)
    bx.set_yticks([0,1],['Fusion order','Judge order']);bx.set_xticks([1,4,8,12,16])
    bx.set_xlabel('Question number');bx.tick_params(length=3,pad=3)
    bx.spines[['top','right','left']].set_visible(False)
    bx.text(0,1.09,'(b) Ordering archive',transform=bx.transAxes,fontweight='bold',fontsize=9)
    write_csv('verifier_scores.csv',records,['qid','candidate','group','score'])
    pairrows=[{'qid':r['qid'],'fusion_order_hit':bool(r['filter_only']['hit']),'judge_order_hit':bool(r['judged']['hit'])} for r in run]
    write_csv('verifier_order_pairs.csv',pairrows,['qid','fusion_order_hit','judge_order_hit'])
    save(fig,'fig_exp_verifier')


def main():
    frozen,follow=read(FROZEN),read(FOLLOW)
    route(frozen);content(frozen,follow);verifier()
    sources={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in [FROZEN,FOLLOW,SCORES,ORDER,GOLD]}
    manifest={'sources_sha256':sources,'artifacts':'fig_exp_route/content/verifier.{pdf,png}',
        'route':'frozen 72 non-refusal cases, Wilson 95%','content':'frozen and follow-up 72 non-refusal cases, Wilson 95%; follow-up read-all only 3 complete and not plotted',
        'verifier':'exp1 recorded scores and exp5 same-pool ordering are separate archives; absent score excluded',
        'note':'Figure generation uses Matplotlib, with Origin-style presentation; the Origin application was not used.',
        'matplotlib_version':matplotlib.__version__}
    (DATA/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Figures and data:',OUT,DATA)

if __name__=='__main__': main()
