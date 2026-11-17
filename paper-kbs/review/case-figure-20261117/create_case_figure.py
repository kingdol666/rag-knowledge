"""Reproducible, editable case-study figure; texts translated from the logs.

Source: review/experiment-redesign-20261101/artifacts/demo-20261112/
qa_omp_Q1.json and qa_claude_Q1.json. Workflow details are answer-reported.
"""
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

HERE = Path(__file__).resolve().parent
mpl.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none",
                     "pdf.fonttype": 42, "ps.fonttype": 42})
fig = plt.figure(figsize=(7.20, 5.55), facecolor="white")
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
ink, blue, border = "#182c42", "#297fc2", "#8eb5d5"
light, pale, green = "#eef6fc", "#f7f9fb", "#27865d"

def box(x, y, w, h, fill="white", edge=border, radius=1.1, lw=.8, ls="solid"):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                       fc=fill, ec=edge, lw=lw, linestyle=ls, mutation_aspect=1)
    ax.add_patch(p)
    return p

def text(x, y, s, size=8.1, color=ink, weight="normal", ha="left", va="center", **kw):
    return ax.text(x, y, s, fontsize=size, color=color, weight=weight,
                   ha=ha, va=va, linespacing=1.25, **kw)

def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1,y1), (x2,y2), arrowstyle="-|>",
                                mutation_scale=7.5, lw=.9, color=ink))

def icon_query(x,y):
    ax.add_patch(Rectangle((x, y), 3.1, 5.2, fill=False, ec=blue, lw=1))
    for j in range(3):
        ax.plot([x+.6,x+2.5],[y+1.2+j*1.2]*2, color=blue, lw=.7)

# A restrained input panel retains the reading order of the supplied reference.
box(1.2, 84, 97.6, 14, fill="#f4f6f8", edge="#9daab5", radius=.5)
icon_query(3.5, 88.6)
text(8.5, 95.0, "SHARED QUESTION", size=7.6, weight="bold", color=blue)
text(8.5, 91.0, "What are DeepSeek-R1's pass@1 scores on AIME 2024 and MATH-500?", size=8.6, weight="bold")
text(8.5, 87.1, "Prompt names the paper and library and prescribes the tool sequence.", size=7.4, color="#526274")

text(2, 80.9, "RECORDED CASE: TWO HARNESSES", size=8.0, weight="bold")
text(98, 80.9, "Workflow details reported in the answers", size=7.2, color="#56697a", ha="right")
ax.plot([1.2,98.8],[78.3,78.3], color="#aebbc6", lw=.6, ls=(0,(3,3)))

def lane(y, name, docs, judged, surviving):
    text(2.4, y+5.4, name, size=8.4, weight="bold", color=blue)
    positions = [15, 35.5, 56, 76.5]
    cells = [
        ("Rewrite query", "benchmark + metric"),
        ("Vector search", f"{docs} document parts"),
        ("Laya scoring", f"{judged} scored / {surviving} retained"),
        ("Read source", "Table 8 + Table 3"),
    ]
    for (x,(title,detail)) in zip(positions,cells):
        box(x,y,18,10.5, fill=light, edge=border)
        text(x+9,y+7.1,title,size=7.8,weight="bold",ha="center")
        text(x+9,y+3.2,detail,size=7.0,color="#526274",ha="center")
    for x in positions[:-1]: arrow(x+18.3,y+5.25,x+20.0,y+5.25)

lane(65.0,"OMP",4,52,40)
lane(51.0,"Claude",5,62,58)
ax.plot([1.2,98.8],[47.7,47.7],color="#aebbc6",lw=.6,ls=(0,(3,3)))

text(2,44.8,"SOURCE EVIDENCE",size=8.0,weight="bold")
text(98,44.8,"Two tables in the same paper",size=7.2,color="#56697a",ha="right")
box(2,32.4,46.7,9.3,fill=pale,edge="#c1ccd4")
box(51.3,32.4,46.7,9.3,fill=pale,edge="#c1ccd4")
text(4.1,39,"Table 8  ·  part 3",size=8.0,weight="bold")
text(4.1,35.3,"AIME 79.8  |  MATH-500 97.3",size=7.7,color=blue)
text(53.4,39,"Table 3  ·  part 1",size=8.0,weight="bold")
text(53.4,35.3,"R1 79.8 / 97.3  |  R1-Zero 77.9 / 95.9",size=7.3,color=blue)

text(2,28.7,"ANSWER EXCERPTS",size=8.0,weight="bold")
text(98,28.7,"English translations, condensed",size=7.2,color="#56697a",ha="right")
box(2,14.1,46.7,11.7,fill="#f8fcf9",edge="#a6c9b0")
box(51.3,14.1,46.7,11.7,fill="#f8fcf9",edge="#a6c9b0")
text(4.1,22.9,"OMP",size=8.1,weight="bold",color=green)
text(4.1,18.8,"R1: 79.8% on AIME; 97.3% on MATH-500.\nR1-Zero scores are not the final R1 scores.",size=7.3)
text(53.4,22.9,"Claude",size=8.1,weight="bold",color=green)
text(53.4,18.8,"R1: 79.8% on AIME; 97.3% on MATH-500.\nTables 8 and 3 agree; R1-Zero is distinct.",size=7.3)

ax.plot([1.2,98.8],[11.4,11.4],color="#aebbc6",lw=.6,ls=(0,(3,3)))
text(2,8.0,"Single directed case: both answers describe the prescribed retrieval workflow.",size=7.3,color="#536171")
text(2,4.6,"The logs retain final answers; the workflow above is self-reported, not an independently replayed trace.",size=7.2,color="#536171")

for ext in ("svg", "pdf", "png"):
    fig.savefig(HERE / f"q1_harness_case_prototype.{ext}", dpi=300, facecolor="white")
plt.close(fig)
