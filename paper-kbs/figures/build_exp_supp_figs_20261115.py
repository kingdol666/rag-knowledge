#!/usr/bin/env python3
"""Redraw supplemental experiment figures S3--S5 using archived results."""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT=Path(__file__).resolve().parents[2]
RES=ROOT/'paper-kbs/experiments/results'
OUT=ROOT/'paper-kbs/tex/journal_20p/figs'
DATA=ROOT/'paper-kbs/figures/experiment_20261115_data'
BLUE,ORANGE,DARK,GREY='#35689A','#C47727','#383838','#B9BEC4'
plt.rcParams.update({'font.family':'Arial','font.size':8.5,'axes.labelsize':8.5,'xtick.labelsize':8.3,
'ytick.labelsize':8.3,'legend.fontsize':8.3,'axes.linewidth':.75,'pdf.fonttype':42,'ps.fonttype':42,
'axes.edgecolor':DARK,'text.color':DARK,'axes.labelcolor':DARK,'xtick.color':DARK,'ytick.color':DARK,
'figure.facecolor':'white','savefig.facecolor':'white'})

def get(name):return json.loads((RES/name).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(fig,name):
    fig.savefig(OUT/(name+'.pdf'),facecolor='white')
    fig.savefig(OUT/(name+'.png'),dpi=300,facecolor='white')
    plt.close(fig)
def csv_out(name,rows):
    with (DATA/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def clean(ax):
    ax.spines[['top','right']].set_visible(False);ax.tick_params(length=3,pad=2)

def fig_s3(raw):
    labels=['Li thermal runaway','Vaccination schedule','Python concurrency','Mold vent design']
    rows=raw['probes'];assert len(rows)==4
    fig,ax=plt.subplots(figsize=(3.5,2.7))
    fig.subplots_adjust(left=.35,right=.94,bottom=.16,top=.75)
    out=[]
    for i,(r,label) in enumerate(zip(rows,labels)):
        k,above=r['kept_n'],r['vector_above_0.35']
        ax.scatter(k,i-.16,s=30,marker='o',c=BLUE,zorder=3)
        ax.scatter(above,i+.16,s=30,marker='s',c=ORANGE,zorder=3)
        ax.annotate(str(k),(k,i-.16),xytext=(4,0),textcoords='offset points',va='center',fontsize=8.3,color=BLUE)
        ax.annotate(str(above),(above,i+.16),xytext=(4,0),textcoords='offset points',va='center',fontsize=8.3,color=ORANGE)
        out.append({'qid':r['qid'],'topic':r['topic'],'merged_candidates':r['merge_n'],'judge_survivors':k,'vector_chunks_above_0_35':above})
    ax.set_yticks(range(4),labels);ax.set_ylim(3.55,-.55);ax.set_xlim(0,14)
    ax.set_xticks([0,3,6,9,12]);ax.set_xlabel('Count per probe')
    ax.grid(axis='x',color='#D7DADD',linewidth=.45);ax.set_axisbelow(True);clean(ax)
    fig.legend(handles=[Line2D([0],[0],marker='o',color=BLUE,linestyle='none',markersize=5,label='Judge survivors (documents)'),
                        Line2D([0],[0],marker='s',color=ORANGE,linestyle='none',markersize=5,label='Dense score ≥ 0.35 (chunks)')],
               loc='upper left',bbox_to_anchor=(.31,.98),frameon=False,ncol=1,handletextpad=.4)
    csv_out('supp_s3_probes.csv',out);save(fig,'fig_exp_s3')

def fig_s4(raw,order):
    replay=raw['cut_replay'];m=sorted(float(x) for x in replay)
    assert m==[.05,.1,.15,.2,.25,.3,.35]
    def find(v):return replay[next(k for k in replay if float(k)==v)]
    gold=[find(v)['gold_kept'] for v in m];kept=[find(v)['mean_kept'] for v in m]
    assert gold==[8,14,16,17,17,17,17]
    records=[{'margin':x,'gold_kept':g,'gold_pool':17,'mean_kept':k} for x,g,k in zip(m,gold,kept)]
    rows=order['rows']; assert len(rows)==16
    # Filtering preserves fusion order. A retained hit is also an original top-five
    # hit only when even placing every removed item before it keeps its rank <= 5.
    fusion=[]
    for r in rows:
        filtered=bool(r['filter_only']['hit'])
        removed=r['n_fusion']-r['n_survivors']
        best=r['filter_only']['best_rank']
        if removed == 0:
            fusion.append(filtered)
        elif filtered and best is not None and best + removed <= 5:
            fusion.append(True)
        else:
            raise ValueError('Fusion hit cannot be inferred from archived summary')
    sums=[sum(fusion),sum(r['judged']['hit'] for r in rows),sum(r['filter_only']['hit'] for r in rows),sum(r['rrf_fuse']['hit'] for r in rows)]
    assert sums==[15,7,15,14]
    fig=plt.figure(figsize=(5.46,3.15))
    gs=fig.add_gridspec(2,2,left=.12,right=.98,bottom=.17,top=.84,wspace=.58,hspace=.35,width_ratios=[1.15,1.0])
    a=fig.add_subplot(gs[0,0]);c=fig.add_subplot(gs[1,0],sharex=a);b=fig.add_subplot(gs[:,1])
    a.plot(m,gold,'o-',color=BLUE,lw=.9,ms=4);a.set_ylim(6,18.4);a.set_yticks([8,12,16]);a.set_ylabel('Gold kept\n(of 17)');clean(a)
    c.plot(m,kept,'s-',color=ORANGE,lw=.9,ms=4);c.set_ylim(6,12.5);c.set_yticks([6,9,12]);c.set_ylabel('Mean kept');c.set_xlabel('Margin m');clean(c)
    plt.setp(a.get_xticklabels(),visible=False)
    c.set_xticks([.05,.15,.25,.35],['0.05','0.15','0.25','0.35'])
    for ax in (a,c):
        ax.axvline(.15,color=GREY,ls='--',lw=.65);ax.axvline(.20,color=GREY,ls=':',lw=.75)
        ax.grid(axis='y',color='#D7DADD',linewidth=.4);ax.set_axisbelow(True)
    names=['Fusion','Judge rank','Judge filter','Rank fusion']
    for i,(label,n) in enumerate(zip(names,sums)):
        color=ORANGE if i==1 else BLUE
        b.scatter(n,i,marker='s' if i==1 else 'o',s=29,color=color,zorder=3)
        b.annotate(f'{n}/16',(n,i),xytext=(4,0),textcoords='offset points',fontsize=8.3,va='center',color=color)
    b.set_yticks(range(4),names);b.set_ylim(3.65,-.65);b.set_xlim(0,20)
    b.set_xticks([0,4,8,12,16]);b.set_xlabel('Questions with Hit@5');clean(b)
    b.grid(axis='x',color='#D7DADD',linewidth=.4);b.set_axisbelow(True)
    a.text(0,1.16,'(a) Score archive',transform=a.transAxes,fontsize=8.5,fontweight='bold')
    b.text(0,1.07,'(b) Ordering archive',transform=b.transAxes,fontsize=8.5,fontweight='bold')
    csv_out('supp_s4_margin.csv',records)
    csv_out('supp_s4_ordering.csv',[{'role':label,'hit_at_5':n,'n_questions':16} for label,n in zip(names,sums)])
    save(fig,'fig_exp_s4')

def fig_s5(raw):
    r=raw['response'];f=[p.replace('\\','/') for p in r['merge']['judged_candidates']]
    scores={k['doc_path'].replace('\\','/'):float(k['score']) for k in r['cut']['kept']}
    assert len(f)==len(scores)==12 and set(f)==set(scores)
    judged=sorted(scores,key=lambda p:-scores[p]);
    def cls(p):return 'Gold' if 'EL-2025-0317' in p else ('PLC' if 'aw-industrial/【演示线1' in p else 'Other')
    assert [cls(x) for x in f].count('Gold')==1 and [cls(x) for x in f].count('PLC')==5
    out=[]
    for i,p in enumerate(f):out.append({'fusion_rank':i+1,'judge_rank':judged.index(p)+1,'score':scores[p],'class':cls(p),'candidate':p})
    assert out[0]['class']=='Gold' and out[0]['judge_rank']==8 and round(out[0]['score'],3)==.846
    fig,axes=plt.subplots(1,2,figsize=(5.46,3.3),sharey=True)
    fig.subplots_adjust(left=.115,right=.98,bottom=.23,top=.80,wspace=.30)
    colors={'Gold':BLUE,'PLC':ORANGE,'Other':GREY}
    for ax,order,label in zip(axes,[judged,f],['(a) Judge rank','(b) Fusion-order filter']):
        ax.axhspan(.5,5.5,color='#EDF1F4',zorder=0)
        for i,p in enumerate(f):
            kind=cls(p); y=order.index(p)+1
            ax.plot([0,1],[i+1,y],color=colors[kind],linewidth=1.5 if kind=='Gold' else .9 if kind=='PLC' else .6,
                    marker='o',ms=3.5 if kind=='Gold' else 2.8,zorder=4 if kind=='Gold' else 3)
        ax.set_ylim(12.8,.2);ax.set_xlim(-.12,1.12);ax.set_xticks([0,1],['Fusion','Output'])
        ax.set_yticks([1,3,5,7,9,11,12]);clean(ax)
        ax.text(0,1.06,label,transform=ax.transAxes,fontsize=8.5,fontweight='bold')
    axes[0].set_ylabel('Rank (1 = highest)')
    # Both raw rankings and scores are retained in the csv; shaded band is top 5.
    fig.legend(handles=[Line2D([0],[0],color=BLUE,lw=1.5,label='Gold (score 0.846)'),
                        Line2D([0],[0],color=ORANGE,lw=1,label='PLC telemetry (5)'),
                        Line2D([0],[0],color=GREY,lw=1,label='Other candidates (6)')],
               loc='lower center',bbox_to_anchor=(.53,.01),frameon=False,ncol=2,handlelength=1.2,columnspacing=1.2)
    csv_out('supp_s5_rankings.csv',out);save(fig,'fig_exp_s5')

def main():
    OUT.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True)
    a=get('exp3_abstention.json'); b=get('exp5_judge_filter.json');c=get('exp5_q2_anatomy.json')
    fig_s3(a);fig_s4(a,b);fig_s5(c)
    manifest={'sources_sha256':{name:sha(RES/name) for name in ['exp3_abstention.json','exp5_judge_filter.json','exp5_q2_anatomy.json']},
    's4_note':'Margin sweep 0.05 through 0.35 comes from exp3; paired ordering roles come from a separate exp5 archive. Fusion hit derives from filter hit when filtering hits or when no candidates removed.',
    's3_note':'Judge survivors and dense hits are different unit populations: documents and vector chunks.',
    'style':'Matplotlib vector output, Origin-style presentation; Origin software not used.'}
    (DATA/'supp_figures_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Created S3--S5 PDF, PNG and source-linked CSVs.')

if __name__=='__main__':main()
