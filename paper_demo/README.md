# paper_demo — CIKM Demo Track 论文工作区

目标：把 rag-knowledge 平台（系统名 **QDCVR**）写成 CIKM Demo 论文
（**正文 ≤4 页**，参考文献不计页；GenAI 披露不计页）。

**当前状态：可提交草稿完成。** `tex/main.pdf` = 5 页 = 正文 4 页（含结论与致谢，
符合 CIKM 2026 demo CFP「4 页含附录与致谢」）+ 第 5 页仅 GenAI 披露与参考文献
（CFP 允许溢出；Data Availability 作为披露段并入 GenAI 披露块）。

## 目录

| 路径 | 内容 |
|---|---|
| `WRITING-PLAN.md` | 写作计划：合规清单、范文研读、系统素材与证据链、逐节方案、评审循环记录 |
| `FIGURE-STYLE-GUIDE.md` | 6 篇 CIKM Demo 范文的图表风格提炼（18 条可执行规则 + 禁止项） |
| `reference/` | 6 篇 CIKM Demo 范文（PDF + 提取文本 + `papers_index.json`） |
| `figures/` | 论文配图源码与产物（见下） |
| `tex/` | `main.tex` + 分节 tex + `refs.bib` + 编译产物 `main.pdf` 与逐页 PNG |

## 配图流水线（全部可复跑）

```bash
cd figures
python capture_ui.py               # 登录真实系统 → 逐页截图（2x，含全页图）
python capture_search.py --tag nisq # 真实跑一次检索会话并截图
python build_fig2.py               # 裁切 4 个面板 → HTML 拼版 → 渲染 PNG
```

### 一页一图（2026-09-19 定稿布局）

三张全宽图按「一页一张」分布：**图 1（对比图）置 p2 页首、图 2（架构）置 p3 页首、
图 3（三轨对照）置 p4 页首**。`figure*` 浮动体只会落在"遇到它的那一页的下一页"，
所以图 2 的源码块有意放在 `sec2_system.tex` §2.2 中间（§2.2 在 p2 排版），图 3 紧跟
`\input{sec3_demo}` 之后——移动源码块位置即可微调落页，勿改回页首集中放置。

| 产物 | 说明 |
|---|---|
| `fig1_rag_vs_kb.png` | 图 1（p2）：常规 dense RAG vs. QDCVR 协议同库同题对照 + 底部口径分栏的基准条 |
| `fig2_architecture.png` | 图 2（p3）：四层架构 + 一条真实 query 全流程 + gate-fail 路径 |
| `fig3_benchmark.png` | 图 3（p4）：Track A/B/C 逐字真实回答 + 时延条（口径已标注） |
| `fig1_architecture.png` / `fig2_ui_composite.png` / `fig2_demo_traces.png` / `fig3_threeway.png` | 历史版本与视频素材，未收入论文 |
| `shots/` | 原始截图（`*__viewport.png` 视口图、`*__full.png` 全页图） |
| `crops/` | 拼版用的局部裁切 |

## 编译与终检

```bash
cd tex
pdflatex main && bibtex main && pdflatex main && pdflatex main
python ../render_pages.py          # 逐页渲染 PNG 供人工核对
python ../verify_refs.py           # 参考文献 arXiv 核验
```

终检结果（2026-09-18）：

| 项 | 结果 |
|---|---|
| 正文页数 | **4 页**（p1 引言 → p4 结论 + 致谢 + 数据可用性）✅；p5 = GenAI 披露 + 参考文献（均不计页） |
| 版面 | 图 1 跨栏置 p2 页首，图 2 跨栏置 p4（§3 论证处），无空白浮动页 |
| Overfull hbox / vbox | **0 / 0** |
| LaTeX 错误 / 未定义引用 | **0 / 0** |
| 乱码 / 豆腐块 | **0** |
| 参考文献 | 15 条，arXiv/官方源逐条核验（`verify_refs.py`） |
| 仓库 URL | `github.com/kingdol666/rag-knowledge`（**已修正**：旧稿写的 `kingdol/...` 是 404） |
| 演示视频 URL | GitHub 公开仓库 blob 链接（推送后生效） |

合规与排版审计见 [`CIKM-COMPLIANCE-AUDIT.md`](CIKM-COMPLIANCE-AUDIT.md)。

## 数据来源铁律

正文每个数字都可回溯到 `benchmark-suite/results/` 的工件，且**全部对应当前
30000 字符分块那一轮**（2026-09-18）：

| 论文数字 | 工件 |
|---|---|
| 50 篇解析 50/50、8.3–50.3 s | `ingest_survey.json` |
| 5 门类库 18/15/10/5/2 篇、165 入库文档（9 整篇 + 156 part） | `ingest_report.json` |
| 3 处文件名被内容推翻 | `data/papers/classification.json`（逐条 note） |
| 10 题回归 9/10 | `bench10_qa.json` |
| Track A 门控 6–8/8、top-1 金标 10/10、向量 1.57 s + 读 0.81 s | `skill_track_evidence.json` |
| Track A 关键词 10/10（全中 9/10） | `track_a_kw_hit.json` |
| Track B 78.8 s（35.5–165.3）、Track C 12.2 s（5.8–28.6） | `track_bc.json` |
| Track C 证据链缺失（`evidence_docs` 全空） | `track_bc.json` |
| 3 个语料外探针 1/8、1/8、0/8 | `honest_failure_probe.json`（79 产证 → 80 判定） |
| 复现基线 Chunks800 2367 / Struct 1385 / Paras 10219 | `repro_ingest.json` |

### 本轮修正的过期数字

旧稿写的是上一轮（2000 字符分块）的口径，已全部改到当前口径：

| 旧稿 | 现稿 | 依据 |
|---|---|---|
| 1,321 parts | **165 indexed documents**（9 整篇 + 156 part） | `ingest_report.json` |
| >12k 切 ≤10k | **30k 上限分块** | `config.yml` `large_doc.max_chars` |
| 门控 7–8/8（5×7 + 5×8） | **6–8/8（2×8 + 6×7 + 2×6）** | 最新报告 |
| Track B 55.5 s | **78.8 s** | `track_bc.json` |
| Track A 兜底初检 5/8 与 4/8 | **两题初检均 5/8**（BQ06→7、BQ10→6） | 最新报告 |
| 探针报告内 "1,321 parts" | **按 shelf 普查重算为 165 文档** | 79→80 重跑 |

## 提交前必做（人工）

1. **作者信息**：Demo 是**单盲**，`main.tex` 中 `Author Name` / `Affiliation` 为占位符，须替换为真实姓名与单位。
2. **演示视频**：`https://example.org/qdcvr-demo` 为占位 URL（摘要、§3、结论各一处），须替换为真实 3 分钟视频链接。
3. **致谢/资助**：`Acknowledgments` 仍是占位文本。
4. **会议信息**：`\acmConference` 中的 2027 城市/日期为占位，camera-ready 时补齐。
