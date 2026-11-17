#!/usr/bin/env python3
"""One-column answer-grid diagnostic based on archived graded 30-cell run."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'benchmark-suite/results/runs/run-20261013T094350Z-5f9faac'
GRADE = ROOT / 'benchmark-suite/results/exp_r2_grade_corrected.json'
OUT = ROOT / 'paper-kbs/tex/journal_20p/figs'
DATA = ROOT / 'paper-kbs/figures/experiment_20261115_data'
BLUE,ORANGE,DARK='#35689A','#C47727','#383838'
plt.rcParams.update({'font.family':'Arial','font.size':8.5,'axes.labelsize':8.5,
'xtick.labelsize':8.3,'ytick.labelsize':8.3,'legend.fontsize':8.3,'axes.linewidth':.75,
'pdf.fonttype':42,'ps.fonttype':42,'xtick.direction':'out','ytick.direction':'out',
'axes.edgecolor':DARK,'text.color':DARK,'axes.labelcolor':DARK,'savefig.facecolor':'white'})


def sha256(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    grade=json.loads(GRADE.read_text(encoding='utf-8'))
    assert grade['run_dir']==RUN.name
    records=[]
    for track,name in [('a2','Platform'),('b','File tools'),('c','Vector only')]:
        rows=[r for r in grade['rows'] if r['track']==track]
        assert len(rows)==10 and len({r['qid'] for r in rows})==10
        for r in rows:
            src=RUN/f'track_{track}_{r["qid"]}.json'
            raw=json.loads(src.read_text(encoding='utf-8'))
            assert raw['qid']==r['qid'] and raw['track']==track
            records.append({'arm':name,'qid':r['qid'],'strict_keyword':int(bool(r['kw_ok'])),
                            'citation_marker':int(bool(r['cited'])),'raw_sha256':sha256(src)})
    DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    with (DATA/'answer_grid_cells.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['arm','qid','strict_keyword','citation_marker','raw_sha256']);w.writeheader();w.writerows(records)
    names=['Platform','File tools','Vector only']; sums=[]
    fig,ax=plt.subplots(figsize=(3.5,2.4))
    fig.subplots_adjust(left=.27,right=.92,top=.74,bottom=.2)
    for y,name in enumerate(names):
        rows=[r for r in records if r['arm']==name]; assert len(rows)==10
        strict=sum(r['strict_keyword'] for r in rows); markers=sum(r['citation_marker'] for r in rows)
        assert strict==9 and markers=={'Platform':9,'File tools':7,'Vector only':2}[name]
        sums.append({'arm':name,'n':len(rows),'strict_keyword_count':strict,'citation_marker_count':markers})
        ax.scatter(strict,y-.15,marker='o',s=35,color=BLUE,zorder=3)
        ax.scatter(markers,y+.15,marker='s',s=34,color=ORANGE,zorder=3)
        ax.annotate(f'{strict}/10',(strict,y-.15),xytext=(4,0),textcoords='offset points',fontsize=8.3,va='center',color=BLUE)
        ax.annotate(f'{markers}/10',(markers,y+.15),xytext=(4,0),textcoords='offset points',fontsize=8.3,va='center',color=ORANGE)
    ax.set_yticks(range(3),names);ax.set_ylim(2.62,-.6);ax.set_xlim(0,11.8)
    ax.set_xticks([0,2,4,6,8,10]);ax.set_xlabel('Answers meeting check (out of 10)')
    ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',color='#D5D9DD',lw=.45);ax.set_axisbelow(True)
    ax.tick_params(length=3,pad=3)
    fig.legend(handles=[Line2D([0],[0],marker='o',color=BLUE,linestyle='none',label='Strict keywords',markersize=5),
                        Line2D([0],[0],marker='s',color=ORANGE,linestyle='none',label='Citation marker',markersize=5)],
               loc='upper left',bbox_to_anchor=(.24,.98),frameon=False,ncol=1,handletextpad=.4,labelspacing=.3)
    fig.savefig(OUT/'fig_exp_answer_grid.pdf',facecolor='white')
    fig.savefig(OUT/'fig_exp_answer_grid.png',dpi=300,facecolor='white')
    plt.close(fig)
    manifest={'run':str(RUN.relative_to(ROOT)).replace('\\','/'),
              'grade':str(GRADE.relative_to(ROOT)).replace('\\','/'),'grade_sha256':sha256(GRADE),
              'interpretation':'keyword and marker checks are lexical proxies, not semantic correctness or citation support',
              'summary':sums,'matplotlib_version':matplotlib.__version__}
    (DATA/'answer_grid_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(sums,indent=2))

if __name__=='__main__':main()
