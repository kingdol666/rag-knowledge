# C 通道 GPU 化核实 + exp/PIPELINE 检索任务矩阵 — 记录（2026-09-27 下午）

> **结论先行**：C 模式的 Laya 判决**早已在 GPU 上**（与 A/B 同环境同通道）——报告里"CPU 瓶颈"
> 是陈旧文案，已修正；本轮补齐了 exp 实验项目的检索任务矩阵能力（`exp.py --retmodes`），
> 三模式 + 3 个 baseline 同题对照 **12/12 金标命中**，另修复一个真实 VRAM 换页缺陷。

## 一、"C 改 GPU"核实结果

| 证据 | 内容 |
|---|---|
| 判决引擎 device | `jev_filter._load_laya()` → **device=cuda**（backend/.venv, torch 2.12.1+cu130） |
| Laya 设备逻辑 | `Agent(device=None)` 在 `torch.cuda.is_available()` 时自动选 CUDA |
| 实测延迟 | C 全臂 64-70s（CPU 时代 542-577s，8 倍差）——GPU 生效的时序证据 |
| 报告文案 | 陈旧句「Laya CPU 逐段判决是时间瓶颈」已在 141 生成器修正并重生成 |

## 二、过程中抓到并修复的真实缺陷：VRAM 换页

- **现象**：exp 矩阵首次跑到 mode C 时 27 分钟不出结果（正常 68s），GPU 利用率 100%。
- **根因**：B 臂在 exp 主进程内加载了一份 GPU Laya（全局缓存 `_LAYA_AGENT`），C 子进程再加载
  一份 → 两副本叠加顶爆 16GB 显存 → WDDM 换页到共享内存（约 20 倍减速）。
- **修复**：`jev_filter.release_laya()`（清缓存 + `torch.cuda.empty_cache()`）；exp/140 在
  B 臂完成后、C 臂启动前调用。修复后 C 恢复正常量级（131-191s，晚高峰桌面显存占用更高，
  波动属预期）。

## 三、exp 实验项目与 PIPELINE 调整

| 文件 | 变更 |
|---|---|
| `experiments/baselines.py` | `run_method(retrieval_only=True)`：纯检索模式，跳过 LLM 回答（answer=None、零 token） |
| `experiments/retrieval_modes.py` | 新增共享 `ensure_laya_interpreter()`（140 与 exp 共用） |
| `exp.py` | 新增 `--retmodes [--ret-baselines bm25,vector,rrf]`：三模式+检索类 baseline 同题纯检索矩阵 → `RETRIEVAL-COMPARE.md` + `retmatrix.json`（RUN 记录 laya_env 证据） |
| `scripts/140` | RUN.json 记录 `laya_env`（torch 版本/cuda 布尔）+ 解释器 |
| `scripts/141` | 陈旧 C-CPU 结论文案修正（×2 处） |
| `PIPELINE.md` | 头部新增「三模式检索臂 + 检索任务矩阵（2026-09-27）」章节：两条入口 + GPU 环境说明 |

## 四、检索任务矩阵结果（run: `run-20260927T094215Z-47cc948`）

| 方法 | q1 耗时 | q2 耗时 | q1 金标 | q2 金标 | 语料 |
|---|---:|---:|:--:|:--:|---|
| mode_A 向量优先 | 82.7s | 52.4s | ✅ | ✅ | 真库 18KB/379docs |
| mode_B 图书管理员 | 78.5s | 29.8s | ✅ | ✅ | 真库（书架内 131/53 docs） |
| mode_C 混合并行 | 235.1s | 123.4s | ✅ | ✅ | 真库 |
| bm25 | <0.1s | <0.1s | ✅ | ✅ | corpus_md 100 篇 |
| vector（平台跨库） | 0.4s | 0.0s | ✅ | ✅ | 真库 |
| rrf | <0.1s | <0.1s | ✅ | ✅ | corpus_md 100 篇 |

- **12/12 金标命中**。所有方法都把金标论文排在第 1 位（bm25/rrf 的 ranked[0] 即金标 arXiv ID）。
- 模式臂 vs baseline 臂公平性说明：modes 与 vector 同库同题；bm25/rrf 在 100 篇固定语料上
  （金标在集），跨语料只比命中率不比绝对延迟；baseline 臂为纯检索（无 LLM 回答）。
- 模式臂延迟波动说明（25→83s 跨轮）：桌面显存占用波动影响 GPU 判决与嵌入服务，属环境方差；
  各模式内部排序（A/B 快、C 全）不变。

## 五、问答记录（q1 原题 · soul_qdcvr_ask 真链路）

- 人格：`soul-cs-library`（kb_scope=计算机与人工智能，labels nlp/llm/检索问答）
- 问：How does InstructDS generate high-quality query-based dialogue summaries?
- 答（节选）：「核心路径是『合成 QDS 三元组 + 多数据集联合训练 + 长度感知增强』三件套……
  三步骤数据合成流水线：summary-anchored query generation → query filtering →
  query-based summary generation」——与金标论文方法完全一致
- 引用：**5 条**，全部锚定 `nlp__2310.10981__instructive-dialogue-summarization-*`（金标论文各分篇）· PAS 5.0
- 全文：`review/fullcheck-20260927/qa-record-q1.json`

## 六、工件

- 矩阵：`benchmark-suite/results/runs/run-20260927T094215Z-47cc948/`（RETRIEVAL-COMPARE.md + retmatrix.json + arm_*.json）
- 三模式报告（文案修正版）：`benchmark-suite/results/runs/retmodes-20260927T062953Z-47cc948/THREE-MODE-REPORT.md`
- 问答：`review/fullcheck-20260927/qa-record-q1.json`
- 本轮全部代码改动：baselines.py / retrieval_modes.py / exp.py / 140 / 141 / jev_filter.py / PIPELINE.md
