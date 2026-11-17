# -*- coding: utf-8 -*-
"""Rebuild supplementary.tex from pre-slim backups (single-backslash, clean)."""
import re, io, os
HERE=os.path.dirname(os.path.abspath(__file__))
B=os.path.join(HERE,'.bak_slim')
bs=chr(92)
def rd(p): return io.open(p,encoding='utf-8').read()
WANT=[('n7_implementation.tex','fig:softdesign','figure'),
      ('n8c_eval.tex','fig:threearms','figure'),
      ('n8c_eval.tex','fig:ood','figure'),
      ('n8b_eval.tex','fig:marginvariants','figure'),
      ('n8c_eval.tex','fig:anatomy','figure'),
      ('n8a_eval.tex','tab:kb-checks','table'),
      ('n8a_eval.tex','tab:retrieval-design','table')]
out=[]
for f,lab,kind in WANT:
    t=rd(os.path.join(B,f))
    env=re.compile(bs+bs+r'begin\{'+kind+r'\*?\}.*?'+bs+bs+r'end\{'+kind+r'\*?\}',re.S)
    for m in env.finditer(t):
        if (bs+bs+'label{'+lab+'}') in m.group(0) or (bs+'label{'+lab+'}') in m.group(0):
            b=m.group(0)
            b=b.replace(bs+'begin{'+kind+'}',bs+'begin{'+kind+'*}').replace(bs+'end{'+kind+'}',bs+'end{'+kind+'*}')
            b=re.sub(bs+bs+r'cite[pt]?\{[^}]*\}','',b)
            b=re.sub(r'(Figure~|Fig\.~|Table~|Tables~|Section~)?'+bs+bs+r'ref\{[^}]*\}','',b)
            out.append(b)
pre=[bs+'documentclass[final,5p,times,twocolumn]{elsarticle}',
 bs+'usepackage{graphicx}'+bs+'usepackage{booktabs}'+bs+'usepackage{array}'+bs+'usepackage{amsmath}'+bs+'usepackage{amssymb}'+bs+'usepackage{caption}'+bs+'usepackage{url}'+bs+'usepackage{xurl}'+bs+'urlstyle{same}',
 bs+'newcommand{'+bs+'yes}{'+bs+'checkmark}'+bs+'newcommand{'+bs+'no}{--}',
 bs+'graphicspath{{figs/}}'+bs+'journal{Knowledge-Based Systems}',
 bs+'begin{document}'+bs+'section*{Supplementary Material}',
 bs+'setcounter{figure}{0}'+bs+'setcounter{table}{0}'+bs+'renewcommand{'+bs+'thefigure}{S'+bs+'arabic{figure}}'+bs+'renewcommand{'+bs+'thetable}{S'+bs+'arabic{table}}']
io.open(os.path.join(HERE,'supplementary.tex'),'w',encoding='utf-8').write('\n'.join(pre+out+[bs+'end{document}']))
print("supplementary rebuilt with", len(out), "floats")