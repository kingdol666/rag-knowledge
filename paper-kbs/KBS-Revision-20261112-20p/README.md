# KBS 论文 20 页内修订审阅包

`revision-preview.pdf` 是 18 页双栏预览，`main_20p.tex`、各节、图件和参考文献为同一版本，可在本文件夹平铺编译。`supplementary.pdf` 为 6 页配套补充材料，`supplementary-inventory.pdf` 为此前保留的详细实验清单。`FIGURE-TABLE-CAPTIONS.md` 提取正文图题、图注和表题；`REVISION-NOTES.md` 说明数据与修改。

从 `main_20p.tex` 依次执行 pdflatex、bibtex、pdflatex、pdflatex；补充材料对 `supplementary.tex` 运行两次 pdflatex。新增图和表的绘制脚本及汇总 CSV 位于本目录，脚本的原始数据路径以项目根目录为基准，原位置为 `paper-kbs/figures/`。实验原始资料位于项目根目录 `review/experiment-redesign-20261101/artifacts/`，部分受数据访问条件约束。哈希清单的路径相对原始目录 `paper-kbs/tex/journal_20p`，不是相对本平铺目录。

18 页为用户要求的双栏版面预算，不等同已确认的期刊篇幅规定。作者信息及投稿声明尚待作者填写或核实；稿件也不能由编译通过推断录用或符合全部期刊要求。此前 24 页包保留在 `paper-kbs/KBS-Revision-20261112/`。
