# -*- coding: utf-8 -*-
"""Slim the manuscript: move redundant floats to supplementary.tex, rewire refs."""
import re, io, os
HERE=os.path.dirname(os.path.abspath(__file__))
def rd(f): return io.open(os.path.join(HERE,f),encoding='utf-8').read()
def wr(f,s): io.open(os.path.join(HERE,f),'w',encoding='utf-8').write(s)
bs=chr(92)
FIG={'fig:softdesign':'S1','fig:threearms':'S2','fig:ood':'S3','fig:marginvariants':'S4','fig:anatomy':'S5'}
TAB={'tab:kb-checks':'S1','tab:retrieval-design':'S2'}
files=['n3_overview.tex','n6_retrieval.tex','n7_implementation.tex','n8a_eval.tex','n8b_eval.tex','n8c_eval.tex']
supp=[]
envf=re.compile(bs+bs+r'begin\{figure\*?\}.*?'+bs+bs+r'end\{figure\*?\}',re.S)
envt=re.compile(bs+bs+r'begin\{table\*?\}.*?'+bs+bs+r'end\{table\*?\}',re.S)
for f in files:
    t=rd(f)
    for env,mapping,kind in ((envf,FIG,'figure'),(envt,TAB,'table')):
        for m in list(env.finditer(t)):
            body=m.group(0); lab=re.search(bs+bs+r'label\{([^}]+)\}',body)
            if lab and lab.group(1) in mapping:
                num=mapping[lab.group(1)]
                b2=body.replace(bs+bs+'label{'+lab.group(1)+'}',bs+bs+'label{'+kind[0]+':'+num+'}')
                # keep full-width in supp to avoid overfull
                b2=re.sub(bs+bs+r'cite[pt]?\{[^}]*\}','',b2)
                b2=re.sub(r'(Figure~|Fig\.~|Table~|Tables~|Section~)?'+bs+bs+r'ref\{[^}]*\}','',b2)
                supp.append((kind,num,b2)); t=t.replace(body,'')
    for L,num in FIG.items():
        t=re.sub(r'(Figure~|Figures~|Fig\.~)?'+bs+bs+r'ref\{'+re.escape(L)+r'\}','Fig.~'+num,t)
    for L,num in TAB.items():
        t=re.sub(r'(Table~|Tables~)?'+bs+bs+r'ref\{'+re.escape(L)+r'\}','Table~'+num,t)
    wr(f,t)
pre=[bs+bs+'documentclass[final,5p,times,twocolumn]{elsarticle}',
 bs+bs+'usepackage{graphicx}'+bs+bs+'usepackage{booktabs}'+bs+bs+'usepackage{array}'+bs+bs+'usepackage{amsmath}'+bs+bs+'usepackage{amssymb}'+bs+bs+'usepackage{caption}'+bs+bs+'usepackage{url}'+bs+bs+'usepackage{xurl}'+bs+bs+'urlstyle{same}',
 bs+bs+'newcommand{'+bs+bs+'yes}{'+bs+bs+'checkmark}'+bs+bs+'newcommand{'+bs+bs+'no}{--}',
 bs+bs+'graphicspath{{figs/}}'+bs+bs+'journal{Knowledge-Based Systems}',
 bs+bs+'begin{document}'+bs+bs+'section*{Supplementary Material}',
 bs+bs+'setcounter{figure}{0}'+bs+bs+'setcounter{table}{0}'+bs+bs+'renewcommand{'+bs+bs+'thefigure}{S'+bs+bs+'arabic{figure}}'+bs+bs+'renewcommand{'+bs+bs+'thetable}{S'+bs+bs+'arabic{table}}']
order=sorted(supp,key=lambda x:(x[0],x[1]))
wr('supplementary.tex','\n'.join(pre+[b for _,_,b in order]+[bs+bs+'end{document}']))
print("moved:",[(k,n) for k,n,_ in order])