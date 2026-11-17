"""Editable BQ04 qualitative prototype. Source: answers_historical_pfc.json.

Paths, process names and source locations here are model-answer reports, not
an independently reconstructed sequence of tool events. No paper files change.
"""
from pathlib import Path
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent
mpl.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none", "pdf.fonttype": 42})
fig = plt.figure(figsize=(7.2, 5.5), facecolor="white")
ax = fig.add_axes([0,0,1,1]); ax.set_xlim(0,100); ax.set_ylim(0,100); ax.axis("off")
ink, blue, mid = "#1b2c3c", "#1977b7", "#8cb6d4"

def box(x,y,w,h,fill="white",edge=mid,r=1.1,lw=.8):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0,rounding_size={r}",
                               fc=fill,ec=edge,lw=lw))
def txt(x,y,s,fs=8,c=ink,weight="normal",ha="left",va="center", **kwargs):
    ax.text(x,y,s,fontsize=fs,color=c,weight=weight,ha=ha,va=va,linespacing=1.25,**kwargs)
def connect(x1,y1,x2,y2):
    # This is an association between answer-reported details, not a verified event sequence.
    ax.plot([x1,x2],[y1,y2],lw=.9,color=ink)

box(1.3,85.5,97.4,12.7,fill="#f3f6f8",edge="#a5b2bc",r=.6)
ax.add_patch(Rectangle((3.5,89.4),3.4,5,fill=False,ec=blue,lw=1))
for y in [90.5,91.7,92.9]: ax.plot([4.1,6.3],[y,y],color=blue,lw=.7)
txt(8.7,95.4,"SHARED QUESTION  ·  BQ04",7.6,blue,"bold")
txt(8.7,90.9,"Which three independent ontologies subdivide the Gene Ontology?",8.7,ink,"bold")

txt(2,82.3,"RECORDED CONDITION",7.5,"#526474","bold")
txt(30.7,82.3,"REPORTED SOURCE",7.5,"#526474","bold")
txt(64.5,82.3,"ANSWER EXCERPT",7.5,"#526474","bold")
ax.plot([1.3,98.7],[79.9,79.9],lw=.6,color="#aab8c1",ls=(0,(3,3)))

def lane(y, name, method, source_head, source, ans):
    # reported evidence and answer excerpts are not presumed to be a full event trace
    box(2,y,25.4,18,fill="#ecf5fc")
    box(30.7,y,30.3,18,fill="#f7f9fb",edge="#bac9d3")
    box(64.5,y,33.5,18,fill="#f5fbf7",edge="#a9cab6")
    txt(3.5,y+14.5,name,8.1,blue,"bold")
    txt(3.5,y+8.5,method,7.4,c="#334b5e")
    txt(32.2,y+14.5,source_head,7.7,ink,"bold")
    txt(32.2,y+8.5,source,7.3,c="#334b5e")
    txt(66,y+14.5,"Three ontologies",7.7,"#27865d","bold")
    txt(66,y+8.0,ans,7.4,c=ink)
    connect(27.8,y+9,30.0,y+9); connect(61.4,y+9,63.8,y+9)

ans = "Molecular Function (MF)\nBiological Process (BP)\nCellular Component (CC)"
lane(59.3,"P  ·  Platform agent", "Laya evidence pack;\ntwo-stage / vector search",
     "Document + chunk-copy hits", "Part 1 of 2; chunk indices\n9 and 3",ans)
lane(38.3,"F  ·  File tools", "File-based source access",
     "Source paper (Markdown)", "Section 2, line 47;\nannotation discussion, line 104",ans)
lane(17.3,"C  ·  Chunk replica", "Vector search on\n800-character chunks",
     "Chunk records", "Chunk indices 9 and 3",ans)

ax.plot([1.3,98.7],[14.6,14.6],lw=.6,color="#aab8c1",ls=(0,(3,3)))
txt(2,11.8,"Source paper: Primer on the Gene Ontology (arXiv:1602.01876).",7.4,ink,"bold")
txt(2,8.5,"Paths and sources are answer-reported; P also reports chunk-replica hits.",7.1,c="#526474")
txt(2,5.3,"All three answers agree; different substrates prevent causal attribution.",7.1,c="#526474")

for ext in ("svg","pdf","png"):
    fig.savefig(OUT/f"bq04_three_arm_case_prototype.{ext}",dpi=300,facecolor="white")
plt.close(fig)
