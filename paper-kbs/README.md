# paper-kbs — KBS期刊论文《QDCVR》实验与手稿

本目录是为 **Knowledge-Based Systems** (Elsevier) 撰写的完整论文及其全部实验产物。
论文系统 = `D:\codes\ragproject\rag-knowledge`(QDCVR 平台 v2.3.0)。

## 目录结构

```
paper-kbs/
├── tex/                    # 论文手稿 (elsarticle, KBS 模板)
│   ├── main.tex            # 主文件 (pdflatex → bibtex → pdflatex ×2)
│   ├── main.md             # 可读预览版 (build_preview.py 生成, 引用为[键名])
│   ├── main_preview.pdf    # 浏览器打印的预览PDF(18页,非elsarticle排版)
│   ├── refs.bib            # 27 条参考文献(全部经 arXiv/DOI 核验,含 refs_verified.json)
│   ├── highlights.tex      # KBS 要求的 Highlights(5 条,均 ≤85 字符)
│   ├── tab_agentic.tex     # Exp2 结果表(由 experiments/gen_agentic_table.py 生成)
│   ├── check_refs.py       # 引用/标签/图文件一致性检查
│   └── figs/               # 论文用图 (PDF 矢量)
├── figures/
│   ├── figures.py          # 全部论文图的绘图脚本 (Okabe-Ito 色盲安全, 300dpi)
│   └── fig1..fig5 .pdf/.png
├── experiments/
│   ├── kbcommon.py         # 公共库: MCP SSE 客户端 / chat API / 16 金标题集
│   ├── exp1_retrieval.py   # Exp1: 机器级 7 方法 × 16 题检索对照
│   ├── exp2_lanes.py       # Exp2: agentic 3 lane + bare × 4 题端到端 × 两轮 (真实 omp)
│   ├── exp3_abstention.py  # Exp3: OOD弃答探针(机器层) + 切割线重放 + 金标秩次
│   ├── exp4_agent_abstention.py # Exp4: agent层OOD弃答探针 6跑(全答案存档)
│   ├── analyze_round2.py   # 双轮一致性 + 去污染fact-check + refusal重算
│   ├── gen_agentic_table.py# Exp2 → LaTeX 表格 + 汇总
│   └── results/
│       ├── exp1_retrieval.json / exp1_summary.json   # Exp1 原始数据(16题)
│       ├── exp2_lanes/ exp2_lanes_rep2/              # Exp2 两轮逐跑日志(32跑)
│       ├── exp3_abstention.json                      # 探针/重放/秩次
│       └── exp4_abstention/run_*.json                # OOD探针全答案(6跑)
└── notes/review-2026-10-08.md  # 五维评审意见与全部修复记录
```

## 复现步骤

```bash
# 0) 前置: ragctl up (backend:8770 + web:6789 + neo4j), kb-mcp SSE :8000, laya worker :8791
cd paper-kbs/experiments
PY=../rag-knowledge/backend/.venv/Scripts/python.exe   # 从仓库根相对
$PY exp1_retrieval.py        # ~3 min, 产出 results/exp1_*.json
$PY exp2_lanes.py            # ~40 min, 16 次真实 agent 运行
uv run --python 3.12 --with matplotlib --with numpy ../figures/figures.py all
$PY gen_agentic_table.py     # 生成 tex/tab_agentic.tex
cd ../tex && pdflatex main && bibtex main && pdflatex main && pdflatex main
```

## 实验设计一页纸

- **Exp1 (工具层)**: 同一 42 文档/5 库生产语料,16 个金标题,7 方法
  (BM25 / Dense / RRF / Graph / Two-stage / Fusion-only / QDCVR-Hybrid+judge),
  指标 Hit@5 / Recall@5 / MRR / 时延。平台方法全部经真实 MCP 工具接口调用。
- **Exp2 (Agent 层)**: 4 题 (Q2 EL脱层 / Q4 POE阻隔 / Q6 克重条款 / Q7 TC0根因) × 4 臂
  (search 钉库 / librarian 全库 / hybrid 钉库 / bare 无KB) × 2 轮,经公开 chat API
  (engine=omp→GLM-5.3-Flash) 真实执行,记录墙钟 / 轮次 / 金标引用 / 事实标记 / 拒答。
- **Exp3 (判卷分析)**: 4条库外探针(机器层,阈值零弃答) + 切割线margin离线重放
  (0.15→16/17金标,0.20→17/17) + 金标judged秩次分布。
- **Exp4 (agent层弃答)**: 3臂×2条OOD题,6/6诚实not-found,零编造引用。
- **判卷膨胀分析**: 191个judged候选分数,金标(n=17)与非金标(n=174)分布
  Mann-Whitney p=0.26 无可检出分离 (图4)。

## 主要发现(详见论文 §7)

1. 健康语料上 BM25/RRF/Two-stage 均 Hit@5=1.00(毫秒级),dense 0.94(Q16近重复族);
   **judged hybrid 0.44**——判卷同域膨胀是唯一主导失败(8题判卷重转序+Q16融合丢)。
2. 191个judged候选全部过阈(≥0.589),零过滤力;金标与非金标分数分布不可分
   (MW p=0.26);**切割线margin重放**: 0.15→丢1金标(Q11),≥0.20→17/17保留。
3. 阈值层对库外查询也不弃答(kept 9-11/12);**诚实弃答的enforcement在阅读/作答层**:
   agent层6/6 OOD诚实not-found、零编造引用、自愿盲区披露。
4. Agent双轮32跑: 金标引用一致16/16、去污染事实标记12/12两轮全保持;bare 0/4引用。
   时延≈轮数×12-15s且两轮波动大→"结果可复现,时延不可复现"。
5. 语料完整性是前提: 实验设置期发现并修复两起索引静默丢失(§6.1/§8 L5)。

## KBS 合规对照

| 要求 | 状态 |
|---|---|
| elsarticle 模板 + 编号引用 (unsrtnat) | ✅ main.tex |
| Highlights (3–5×≤85 字符) | ✅ highlights.tex |
| 结构: 摘要(≈250词)/关键词/背景/相关工作/方法/实现/实验/讨论/结论 | ✅ |
| 声明: CRediT / 利益冲突 / 数据可用性 / AI 使用声明 | ✅ |
| 图: 架构图(1)/三lane流程(2)/工具层结果(3)/agentic结果(4)/判卷膨胀(5) | ✅ 全矢量+视觉验收18页全pass |
| 作者信息/ORCID/基金/demo论文作者名单 | ⚠️ AUTHOR ACTION 占位(main.tex 内有标记) |

> 编译: `tex/main.pdf` 由 tectonic 0.15 (elsarticle) 编译,29页,BibTeX干净;
> `tex/main_preview.pdf` 是 HTML 打印的可读预览(非期刊排版)。
> 注意文件名顺序: 文内 Figure 4 = fig5_e2e(§7.2),Figure 5 = fig4_inflation(§7.3)。
> exp2 run JSON 的 success:false 是已知omp信封误标bug,答案完整,评测以内容为准。
