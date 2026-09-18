# paper_demo — CIKM Demo Track 论文工作区

目标：把 rag-knowledge 平台（系统名 **QDCVR**）写成 CIKM Demo 论文
（**正文 ≤4 页**，参考文献不计页；GenAI 披露不计页）。

**当前状态：可提交草稿完成。** `tex/main.pdf` = 5 页 = 正文 4 页 + 参考文献/披露 1 页。

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

| 产物 | 说明 |
|---|---|
| `fig1_architecture.png` | 图 1：全宽架构图，一条真实 query 走完全流程（HTML 渲染） |
| `fig2_ui_composite.png` | 图 2：**真实系统截图** 4 面板拼版（①②③④ 编号，图注逐一解释） |
| `shots/` | 原始截图（`*__viewport.png` 视口图、`*__full.png` 全页图） |
| `crops/` | 拼版用的局部裁切（统一 2.42:1，保证栅格无锯齿行） |

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
| 正文页数 | **4 页**（p1 引言 → p4 结论）✅；p5 = 致谢/数据可用性/GenAI 披露/参考文献 |
| 版面 | Fig 1 跨栏置于 p2 页首、Fig 2 跨栏置于 p3 页首，两页正文填满无空白 |
| Overfull hbox / vbox | **0 / 0** |
| LaTeX 错误 / 未定义引用 | **0 / 0** |
| 乱码 / 豆腐块 | **0** |
| 正文字数 | 4,070 words |
| 参考文献 | 15 条，arXiv/官方源逐条核验（`verify_refs.py`） |

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
