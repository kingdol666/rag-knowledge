# BQ01-BQ10 回答层对照实验报告（2026-11-15）

## 实验设计

- **增强臂（本轮新跑）**：当前修复后平台逐级路径 —— chat API（Claude Code 引擎，kbEnhanced，锁定五个学科库），题面原文为查询，无金标信息注入。
- **对照组（历史 run-20261013T094350Z-5f9faac，同 100 篇语料、同 10 题）**：
  - P 平台逐级（历史 a2）：同平台、同题；
  - F 文件工具对照（b）：不经过平台检索/判卷，直接文件工具；
  - C 分块复制对照（c）：同内容 800 字符分块副本、平台向量车道（同内容扁平底座控制）。
- **确定性评分口径（全臂一致）**：金标 arXiv id 是否出现（可溯源）、金标关键词覆盖（kw_list 与历史轮完全一致）、引用标记、假拒答、时延/成本。
- **检索层前置事实**（本轮 Stage6）：逐级宽网向量 gold rank1=10/10，Laya 真引擎判卷 10/10，判卷幸存者含金标 10/10。

## 汇总对比

| 臂 | gold id | 关键词全覆盖 | 有引用 | 平均时延 | 成本 |
|---|---|---|---|---|---|
| **逐级增强（新跑，修复后系统）** | **10/10** | **9/10** | **10/10** | 130.7 s | $3.10 |
| P 平台逐级（历史 a2） | 10/10 | 10/10 | 9/10 | 52.6 s | $7.11 |
| F 文件工具对照 | 10/10 | 9/10 | 7/10 | 22.2 s | $4.87 |
| C 分块复制对照 | 10/10 | —(9/10 口径) | 2/10 | 24.5 s | $5.27 |

> C 臂历史口径 kw_ok 未在 grades 顶层单列；引用标记 2/10 是论文中"组织产生可溯源标记"对比的核心数字（9/10 vs 2/10）。

## 逐题对比

| 题 | 增强臂 gold id / kw / 引用 | P | F | C | 增强臂时延/成本 |
|---|---|---|---|---|---|
| BQ01 | ✅ 3/3 / 5标记 | 3/3,✅ | 3/3,✗ | 3/3,✅ | 152s / $0.43 |
| BQ02 | ✅ 2/2 / 6标记 | 2/2,✅ | 2/2,✅ | 2/2,✗ | 90s / $0.23 |
| BQ03 | ✅ 2/2 / 13标记 | 2/2,✅ | 2/2,✅ | 2/2,✅ | 107s / $0.25 |
| BQ04 | ✅ 3/3 / 1标记 | 3/3,✅ | 3/3,✅ | 3/3,✗ | 56s / $0.18 |
| BQ05 | ✅ 1/1 / 2标记 | 1/1,✗ | 1/1,✅ | 1/1,✗ | 141s / $0.33 |
| BQ06 | ✅ 1/1 / 10标记 | 1/1,✅ | 1/1,✅ | 1/1,✗ | 262s / $0.51 |
| BQ07 | ✅ 2/2 / 6标记 | 2/2,✅ | 2/2,✅ | 2/2,✗ | 145s / $0.25 |
| BQ08 | ✅ 2/2 / 9标记 | 2/2,✅ | 2/2,✗ | 2/2,✗ | 140s / $0.35 |
| BQ09 | ✅ 1/2 / 7标记 | 2/2,✅ | 1/2,✗ | 2/2,✗ | 66s / $0.21 |
| BQ10 | ✅ 2/2 / 3标记 | 2/2,✅ | 2/2,✅ | 1/2,✗ | 131s / $0.38 |

## 全部真实增强回复（逐级臂，10 条原文）

---
### BQ01（gold 1706.03762；152s，$0.43，4 turns，关键词 3/3）

**问题**：How does the Transformer compute attention, and why does it replace recurrence and convolution?

**真实回答原文**：

**Conclusion:** A Transformer computes attention as a scaled dot-product over queries, keys and values — `Attention(Q,K,V) = softmax(QKᵀ/√d_k)·V` — run in parallel heads; it replaces recurrence and convolution because a self-attention layer connects every pair of positions with **O(1) sequentially executed operations and O(1) maximum path length**, eliminating the RNN's sequential bottleneck and the CNN's distance-growing path, at a per-layer cost of O(n²·d).

**1. How attention is computed** (source: *Attention Is All You Need*, arXiv 1706.03762 — KB「计算机与人工智能」, part 1/2; P0 direct evidence, verbatim):
- **Definition:** "An attention function can be described as mapping a query and a set of key-value pairs to an output… The output is computed as a weighted sum of the values, where the weight assigned to each value is computed by a compatibility function of the query with the corresponding key."
- **Scaled dot-product:** "We compute the dot products of the query with all keys, divide each by √d_k, and apply a softmax function to obtain the weights on the values." In matrix form (Eq. 1): `softmax(QKᵀ/√d_k)V`. Queries/keys have dimension d_k, values d_v.
- **Why scale:** "for large values of d_k, the dot products grow large in magnitude, pushing the softmax function into regions where it has extremely small gradients." Scaling by 1/√d_k counteracts this. Dot-product attention is preferred over additive attention because it is "much faster and more space-efficient in practice, since it can be implemented using highly optimized matrix multiplication code."
- **Multi-head (Sec. 3.2.2):** Q, K, V are linearly projected h times (h=8, d_k=d_v=d_model/h=64), attention runs in parallel per head, outputs are concatenated and projected by W^O. Purpose: "Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions." Cost stays similar to single-head full-dimension attention.
- **Three uses (Sec. 3.2.3):** encoder self-attention (all positions attend to all); decoder self-attention with masking (illegal future connections set to −∞, preserving auto-regression); encoder-decoder attention (queries from decoder, keys/values from encoder).
- **No recurrence/convolution ⇒** sinusoidal positional encodings are added to embeddings (Sec. 3.5) so order information is injected.

**2. Why it replaces recurrence:** RNNs compute h_t as a function of h_{t−1}; "This inherently sequential nature precludes parallelization within training examples, which becomes critical at longer sequence lengths." Table 1: recurrent layers need **O(n) sequential operations** and have **O(n) maximum path length**, whereas self-attention needs **O(1)** for both.

**3. Why it replaces convolution:** ConvS2S/ByteNet compute representations in parallel, but "the number of operations required to relate signals from two arbitrary input or output positions grows in the distance between positions, linearly for ConvS2S and logarithmically for ByteNet… In the Transformer this is reduced to a constant number of operations, albeit at the cost of reduced effective resolution due to averaging attention-weighted positions, an effect we counteract with Multi-Head Attention." A single k<n convolution also cannot connect all pairs; it needs O(n/k) stacked or O(log_k n) dilated layers.

**4. The three stated desiderata (Sec. 4) and Table 1:** per-layer complexity, minimum sequential operations, maximum path length. Self-attention O(n²·d) / O(1) / O(1); recurrent O(n·d²) / O(n) / O(n); convolutional O(k·n·d²) / O(1) / O(log_k n). The paper notes self-attention is faster than recurrent layers "when the sequence length n is smaller than the representation dimensionality d," and that restricted (neighborhood-r) attention trades path length O(n/r) for lower complexity on very long sequences.

**5. Payoff:** 28.4 BLEU EN→DE ("improving over the existing best results, including ensembles, by over 2 BLEU") and 41.8 BLEU EN→FR single-model SOTA after 3.5 days on eight GPUs; base models trained in 12 hours on 8 P100s.

*Credibility: P0 — all quotes are verbatim from the paper text in the pinned KB (part 1 of 2; Secs. 2, 3.2, 3.5, 4, Table 1, Abstract).*

---
### BQ02（gold 1801.00862；90s，$0.23，4 turns，关键词 2/2）

**问题**：What defines NISQ technology and what is its central limitation?

**真实回答原文**：

**结论：NISQ（Noisy Intermediate-Scale Quantum，含噪中等规模量子）指量子比特数约 50 到几百个、且门操作有噪声、未被量子纠错保护的一代量子处理器；其核心限制是门噪声会随线路规模累积，使可靠执行的线路最多只有约 1000 个双比特门，从而给算力设下硬上限。**

**定义（P0 直接证据）**
- Preskill 原文：“‘intermediate scale’ refers to the size of quantum computers which will be available in the next few years, with a number of qubits ranging from **50 to a few hundred**”；50 比特是里程碑，因为它超出最强经典超级计算机的暴力模拟能力。
- “‘Noisy’ emphasizes that we'll have imperfect control over those qubits; **the noise will place serious limitations on what quantum devices can achieve in the near term**.”
- 明确定义边界：“When I speak of the NISQ era, I'm imagining quantum computers with noisy gates **unprotected by quantum error correction**.”
- 另一篇论文给出同构表述：NISQ 特征为 “restrictive qubit topologies, short coherence times and imperfect quantum gates”。

**核心限制（P0）**
- 门错误率目前“above the .1% level（常常更差）”，因此“we don't expect to be able to execute a circuit that contains many more than about **1000 gates** — 1000 fundamental two-qubit operations — because the noise will overwhelm the signal in a circuit much larger than that.”
- 原文点题：“That limitation on circuit size **imposes a ceiling on the computational power of NISQ technology**.” 近期的实验尺度是“of order 100 qubits, and with circuit depth less than 100, maybe much less.”
- 出路是量子纠错，但其在比特数与门数上有“heavy overhead cost”，所以容错机仍较远；100 比特机器“will not change the world right away”，只是通往更强量子技术的台阶。

**出处**
1. John Preskill, *Quantum Computing in the NISQ era and beyond*（arXiv:1801.00862），KB「自然科学与地球科学」，`quantum-physics__1801.00862__quantum-computing-in-the-nisq-era-and-beyond.md`（第 1/3 部分，§4.1–4.2、§6.2）— P0，定义与限制均由原文直引。
2. *Benchmarking noisy intermediate-scale quantum…*（arXiv:2303.00445），同 KB，`quantum-physics__2303.00445__benchmarking-noisy-intermediate-scale-quantu.md`（第 1/4 部分，§I Introduction）— P0，佐证 NISQ 的噪声/拓扑/相干时间刻画。

---
### BQ03（gold 2212.13138；107s，$0.25，6 turns，关键词 2/2）

**问题**：What is MultiMedQA and how did Flan-PaLM perform on the MedQA benchmark?

**真实回答原文**：

**结论：MultiMedQA 是 Singhal 等人（arXiv 2212.13138，Google Research/DeepMind）提出的医学问答基准，整合了 6 个既有数据集，并新增 HealthSearchQA；Flan-PaLM 540B 在其 MedQA（USMLE 四选一）子集上取得 67.6% 准确率，超越此前 SOTA 逾 17%。**

**1. MultiMedQA 是什么（P0 直接证据）**
- 定义（摘要原文）：「we present MultiMedQA, a benchmark combining six existing open question answering datasets spanning professional medical exams, research, and consumer queries; and HealthSearchQA, a new free-response dataset of medical questions searched online.」
- 七个组成部分（引言）：「MedQA [33], MedMCQA [64], PubMedQA [34], LiveQA [1], MedicationQA [2], and MMLU clinical topics [29]」＋新引入的第七个「HealthSearchQA, which consists of commonly searched health questions」，规模为「a dataset of 3375 commonly searched consumer medical questions」。
- 除准确率外，还配套人工评估框架：「a framework for human evaluation of model answers along multiple axes including factuality, precision, possible harm, and bias」（Table 2 共 12 个轴；Table 3 为外行用户 2 轴）。

**2. Flan-PaLM 在 MedQA 上的表现（P0 直接证据）**
- 摘要：「including 67.6% accuracy on MedQA (US Medical License Exam questions), surpassing prior state-of-the-art by over 17%」。
- 第 4.1 节原文：「On the MedQA dataset consisting of USMLE style questions with 4 options, our Flan-PaLM 540B model achieved a multiple-choice question (MCQ) accuracy of 67.6% surpassing the DRAGON model [94] by 20.1%」——即 67.6 vs. 前 SOTA 50.3 的差距被表述为 17.3 个百分点（另一处正文：「Flan-PaLM 540B exceeded this by 17.3%」）。
- 同批结果（贡献列表）：「67.6% accuracy on MedQA (more than 17% above prior SOTA), 57.6% on MedMCQA, and 79.0% on PubMedQA」。
- 方法：few-shot + chain-of-thought + self-consistency 组合提示；模型规模覆盖 8B / 62B / 540B。

**3. 重要限定（P1）**
高分≠可临床使用：作者明确指出人工评估暴露短板——clinician 判定 Flan-PaLM 长答仅 61.9% 符合科学共识（Med-PaLM 92.6%，临床医生 92.9%），29.7% 可能致害（Med-PaLM 5.8%）。原文：「human evaluation reveals key gaps in Flan-PaLM responses」，并据此提出 instruction prompt tuning 得到 Med-PaLM。

**出处**
- 《Large Language Models Encode Clinical Knowledge》（clinical-medicine__2212.13138），KB：生命科学与医学（`b28f0a25-…`），part 1（摘要/引言）与 part 2（§3.3、§4.1）。
- 同文另有 chunk 副本：`Corpus-Chunks800/…__k00–k33.md`（KB `ce642f28-…`），内容一致，可交叉核对。
- 检索：`kb_search_two_stage`（KB `b1199132-…` 无相关命中，返回 CoT/Flan-UL2 等邻近文档）＋跨库 `kb_search_vector`（top 命中 0.759）＋`kb_laya_judge`（35 段评分，20 段存活，3 篇文档均有 yes）。

---
### BQ04（gold 1602.01876；56s，$0.18，7 turns，关键词 3/3）

**问题**：Which three independent ontologies subdivide the Gene Ontology?

**真实回答原文**：

**结论：Gene Ontology（GO）由三个相互独立的本体（sub-ontology）划分——Molecular Function（MF，分子功能）、Biological Process（BP，生物过程）、Cellular Component（CC，细胞组分），三者非冗余，并共享同一套标识符空间与语法。**

**原始出处（P0 直接证据，逐字引用）**

文献：*Primer on the Gene Ontology*（Gaudet, Škunca, Hu, Dessimoz, 2016；文件名 `genomics__1602.01876__primer-on-the-gene-ontology.md`），KB：生命科学与医学（`b28f0a25-1e1d-40ad-96b8-61bd2b093a28`），第 2 节 "What is the Gene Ontology?"：

> "The Gene Ontology is a controlled vocabulary of terms to represent biology in a structured way. **The terms are subdivided in three distinct ontologies that represent different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC)** (1). These ontologies are non-redundant and share a common space of identifiers and a well-specified syntax."

**要点补充（同一段落）**
- GO 术语通过 `is_a`、`part_of`、`has_part`、`regulates`（含正/负调控）等关系构成有向无环图，节点为术语、边为关系；一个术语可有多个父节点。
- 规模（2015 年 10 月）：43,835 个术语、73,776 条显式 `is_a`、7,436 条 `part_of`、8,263 条 `regulates` 类关系。
- 三者之上常用的"精简版"是 GO-slim（如 Generic GO slim），是跨全部生物学层面的高通用术语人工子集，并非第四个本体。

**可信度**：P0——检索命中即目标文档，且已 `kb_doc_read` 打开正文核对逐字原句，非片段推断。

**检索说明**：对 5 个指定库各做一次向量检索（`kb_search_vector`, slim=true, top_k=10）；命中仅来自 `b28f0a25`（score 0.764，远超其他库 0.44–0.58 的噪声），其余四库（计算机与人工智能、自然科学与地球科学、工程与能源、经济与社会）无相关证据。

---
### BQ05（gold 1512.08067；141s，$0.33，7 turns，关键词 1/1）

**问题**：Why does historical European economic growth contradict Unified Growth Theory?

**真实回答原文**：

**结论：** 按照该库收录文献的论证，欧洲（西方 12 个领先国家、西方 30 国合计、东欧）的 Maddison 长期 GDP 数据显示的是 **AD 1500–1900 年间不间断的双曲增长**，Galor 统一增长理论（UGT）所主张的“马尔萨斯停滞→后马尔萨斯→持续增长”三阶段，以及“惊人的马尔萨斯陷阱逃离”，在数据中都不存在；工业革命也未改变增长轨迹，因此在欧洲这一本应最支持 UGT 的地区，该理论反而被数据推翻。（来源：Nielsen, *Unified Growth Theory Contradicted by the Economic Growth in Europe*, Griffith University, Dec 2015, arXiv:1512.08067；库「经济与社会」）

**核心论据**

1. **方法：倒数变换检验。** 若增长是双曲型 S(t)=(a−kt)⁻¹，其倒数 1/GDP = a−kt 应为一条下降直线；直线即“机制未变”，不应被人为切成两三个“制度阶段”。该文用 Maddison (2010) 数据分别作半对数与倒数图。
2. **无停滞、无跳变。** “There was never a transition from stagnation to growth because there was no stagnation.” 马尔萨斯振荡（随机波动）在原始与倒数图中均缺失；所谓起飞特征在倒数图上“missing”。
3. **拟合参数（可复核的关键数字）：**
   - 西欧 12 国：a = 1.147×10⁻¹，k = 5.961×10⁻⁵，奇点 1923 年；但增长约在 1900 年转向更慢轨迹（绕过奇点约 23 年）；AD 1500–1900 拟合“remarkably good”。
   - 西欧 30 国合计：a = 9.859×10⁻²，k = 5.112×10⁻⁵，奇点 1929 年，约 1900 年转向（约 29 年）。
   - 东欧：a = 7.749×10⁻¹，k = 4.048×10⁻⁴，奇点 1915 年，约 1890 年转向（约 25 年）。
4. **逐条对撞（Conclusions 原文）：** “The theory claims a prolonged epoch of stagnation; the data show a steadily-increasing hyperbolic growth. The theory claims the existence of Malthusian trap; the data show that there was no trap… The theory claims that the Industrial Revolution was the primary engine of economic growth; the data show that this engine had absolutely no effect on the economic growth trajectories.”
5. **对 UGT 数据用法的批评：** Galor 等人反复只取 4 个点用直线相连（Ashraf 2009；Galor 2005a 等多处），该文称这种处理“unscientific”，导致理论“dissociated from reality”，需“thoroughly revised… most likely replaced”。
6. **附加论点：** 该文还称 UGT 宣称的“持续增长时代”具有误导性——数据反而显示增长虽已减速但仍过快，指向不安全的未来（Nielsen 2015f）。

**可信度标注：** P1（直接相关，但为单一作者 arXiv 预印本的批评性论证，非中性综述；本次检索未见 Galor 原著或 UGT 教科书条目入库，故仅呈现该批评文献的立场与证据）。库内另有同文分块副本（KB `Corpus-Chunks800`，`economics__1512.08067…__k*.md`），不构成独立第二来源。

---
### BQ06（gold 1503.07557；262s，$0.51，12 turns，关键词 1/1）

**问题**：Which physical factor primarily controls the response of precipitation extremes to climate change?

**真实回答原文**：

**Conclusion: the primary control is thermodynamic — the warming-driven increase in the saturation vapor pressure of water (atmospheric water-vapor content), which drives precipitation extremes up at roughly Clausius–Clapeyron scaling (6–7 % K⁻¹); changes in dynamics (vertical velocity) and precipitation efficiency are secondary and much less certain.**

Evidence from the review *Precipitation extremes under climate change* (P. A. O'Gorman, climate-science__1503.07557, KB 自然科学与地球科学; P0 direct evidence):

1. **The decomposition (Eq. 1):** P ≃ −ε{ω·S(T,p)}, i.e. the precipitation rate in an extreme event splits into a dynamical contribution (ω, vertical velocity), a thermodynamic contribution (S, saturation specific humidity along a moist adiabat), and a microphysical contribution (ε, precipitation efficiency). "This scaling is often referred to as Clausius-Clapeyron scaling and gives a sensitivity of 6–7 % K⁻¹ for typical surface temperatures." (part 1 of 3, §3 Theory)

2. **Why thermodynamics dominates in the extratropics:** "If changes in dynamics and precipitation efficiency are negligible, precipitation extremes increase with warming because of increases in the saturation vapor pressure of water." (part 1, §1) And from the omega equation: "the vertical velocities associated with large-scale extratropical precipitation extremes might not change greatly under climate change" — hence the response is essentially the thermodynamic/Clausius–Clapeyron response (multimodel-median extratropical sensitivity ≈6 % K⁻¹). (part 1, §4.1)

3. **RCE/tropical conditions:** "For surface temperatures near those of the present-day tropics, the precipitation extremes increase at close to the thermodynamic rate, and this is close to Clausius-Clapeyron scaling with the surface specific humidity, with relatively small contributions from changes in vertical velocities and precipitation efficiency." (part 1, §3)

4. **Conclusion:** "Contributions from changes in thermodynamics, dynamics, and precipitation efficiency have all been found to be important… The thermodynamic contribution is the easiest to understand and always gives an intensification with warming." The abstract adds that it "is robust and well understood, but theoretical understanding of the microphysical and dynamical contributions is still being developed." (part 2, §8; part 1 abstract)

**Caveats (P1):** Where convection matters the sensitivity is higher and less certain — observed tropical sensitivity 9 % K⁻¹ (90% CI 6–14 % K⁻¹) and observationally constrained model estimate 11 % K⁻¹ (7–15 % K⁻¹) vs ~6 % K⁻¹ extratropically; possibly a more positive dynamical contribution in the tropics. Below ~295 K, changes in precipitation efficiency (e.g. hydrometeor fall speed) can push subdaily extremes above CC scaling. (part 1 §2/§4.2; part 2 §7)

---
### BQ07（gold 2608.05850；145s，$0.25，5 turns，关键词 2/2）

**问题**：What is MameLoshnLM and what parameter scale does it have?

**真实回答原文**：

**MameLoshnLM is the first open-source large language model built specifically for Yiddish, and it has 8B parameters.** It was produced by continued pretraining of Llama‑3.1‑8B on a Yiddish corpus.

**What it is**
- The abstract states: *"the first open-source 8B-parameter language model built specifically for Yiddish."*
- The paper introduces *"MAMELOSHNLM, an open-source 8B-parameter LM for Yiddish, together with two supporting resources: Oytser, a new Yiddish pretraining corpus, and Kashes, a benchmark for evaluating Yiddish LMs."*
- Name: *"We name the model Mame-Loshn … 'mother tongue'"* (Section 5, first open-source LLM for Yiddish).

**Parameter scale / training**
- 8B parameters — *"MAMELOSHNLM was produced by continued pretraining of Llama-3.1-8B on a Yiddish corpus using a causal language modeling objective"*, trained in bfloat16 with the 8-bit AdamW optimizer.
- Compared against open models of similar scale (Llama 3.1 8B, Qwen3 8B, BLOOMZ 7B, Gemma‑2 9B, EuroLLM 9B), it *"outperforms open models of similar scale, with strong gains on Yiddish-centered tasks such as translation, linguistic analysis, and named entity recognition"* — notably **>11 COMET points** over its closest competitor on English→Yiddish translation, and it better captures Yiddish lexical/morphological patterns than general multilingual models.

**Sources (P0 — direct verbatim evidence, Laya-verified survivors)**
- KB **计算机与人工智能** → `计算机与人工智能/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md (part 1 of 4).md` (Abstract, §1, §5) and `(part 4 of 4).md` (§7.2, Appendix F); mirrored chunks in KB **Corpus-Chunks800** (`..._k00/_k12/_k17.md`).

---
### BQ08（gold 2408.09942；140s，$0.35，6 turns，关键词 2/2）

**问题**：How does oxygen redox contribute to the capacity of battery cathodes?

**真实回答原文**：

**Conclusion: Oxygen (anionic) redox adds capacity that transition-metal redox alone cannot deliver — lattice O²⁻ donates electrons during charging, compensating for the absence of oxidizable transition metals and pushing cathodes past the transition-metal oxidation limit ("overcapacity").** The participating oxygen states are reversible O²⁻ ↔ (O₂)ⁿ⁻ peroxo-type species (or oxygen electron holes), which raises achievable capacity above what cationic redox would predict (Assadi & Hanaor, *Oxygen redox in battery cathodes: A brief overview*, arXiv:2408.09942, 工程与能源 KB; P0 direct evidence — this review is devoted to exactly this question).

**What enables it**
- Oxygen redox occurs when **orphaned/non-bonding O 2p states are lifted close to the Fermi level**, i.e. when O is coordinated by fewer than three transition metals: Li-/Na-excess layered oxides (e.g. Li₂MnO₃, where Mn stays +4), and ilmenite-type NaTMO₃ where O is under-coordinated by both alkali and TM (2 TM + 2 Na). In conventional LiTMO₂, O 2p sits ~10 eV below the Fermi level and is electrochemically inert (Part 1, §2; Part 2, §4).
- Extra delithiation capacity is carried by oxygen oxidation, e.g. Li₄Mn₂O₅: Li₄⁺Mn₂³⁺O₅²⁻ → 4Li⁺ + 4e⁻ + Mnₓ⁴⁺Mn₂₋ₓ⁵⁺O₅₋ₓ²⁻Oₓ¹⁻, where **x quantifies the extent of oxygen participation** (Part 1, §3).

**Quantified contribution**
- Na₂₋ₓRuO₃ (0 < x < 1.5) shows **180 mAh g⁻¹, ≈1.4 electrons per formula unit; the additional ≈0.4 electron capacity is attributed to a reversible oxygen redox mechanism**, and once O redox initiates the voltage spikes from **2.2 V to 3.4 V** (Part 2, §4).
- O redox is more dominant in **4d transition-metal oxides** (higher TM–O covalency); DFT labile O 2p populations: NaNbO₃ 2.58 e⁻, NaAgO₃ 2.51 e⁻ vs NaVO₃ only 0.17 e⁻ (Part 2, Tables 1–2).

**The price of that extra capacity**
- Reduced O ions bond to each other and leave the lattice as **O₂ gas** → fire/ignition hazard plus **rapid, permanent capacity fade**, large first-cycle loss, voltage fade, and layered→spinel transformation. Mitigation (e.g. surface fluorination strengthening TM–O bonds) is required if the extra capacity is to be used, with a trade-off between initial capacity and long-term retention (Part 1, §3.1; Part 2, §5).
- Predicting it computationally requires DFT that correctly places O 2p vs TM d states: integrate O 2p weight within ~2.0–2.5 eV below E_F; plain GGA fails for these strongly correlated oxides — use HF hybrid or GGA+U (Part 1, §3.2).

*Source: KB 8fa4db59 (工程与能源), doc `materials__2408.09942__oxygen-redox-in-battery-cathodes-a-brief-overvie.md` (parts 1 & 2). An identical copy exists in KB ce642f28 (Corpus-Chunks800).*

---
### BQ09（gold 2410.10669；66s，$0.21，4 turns，关键词 1/2）

**问题**：What problem of visual SLAM in dynamic environments does MLP-SLAM address and how?

**真实回答原文**：

## MLP-SLAM: the problem and the method

**Conclusion (first line):** MLP-SLAM (Li & Sun, arXiv 2410.10669) tackles V-SLAM's **accuracy degradation in highly dynamic scenes** — the static-world assumption breaks down around pedestrians, cars and buses — and solves it by replacing hand-tuned geometric rules and coarse semantic masks with a **multilayer-perceptron dynamic/static feature-point classifier fed with complete geometric information** (image intensity error, epipolar error, reprojection error), embedded in an ORB-SLAM2-based real-time stereo pipeline.

### The problem it addresses
- V-SLAM assumes a static world: "most existing SLAM systems are heavily reliant on the assumption of a static world, including SOTA systems such as ORB-SLAM2, ORB-SLAM3, LSD-SLAM and Direct Sparse Odometry… their precision tends to deteriorate when deployed in dynamic environments."
- Prior solutions fail in three ways: **Type I** geometric-only (epipolar/reprojection error, optical flow); **Type II** semantic-mask filtering (DynaSLAM) which "may erroneously remove" static parked cars on the roadside → information loss, plus MaskRCNN latency; **Type III** hybrids (CFP-SLAM, PointSLOT, VDO-SLAM, DynaSLAM II) that "rely on only partial geometric information" and "often require manual parameter tuning, lack generality, and are excessively laborious to finetune."
- Evaluation gap: no public dataset existed to score dynamic/static discriminators directly.

### How MLP-SLAM solves it
1. **MLP discriminator** — input feature per point is a 3-vector vᵢ = {e_I, e_D, e_Re} (image intensity error, epipolar error, reprojection error, Eqs. 3–5). "The input layer's number of nodes corresponds to the dimension of the input feature, which is three… Previous work like [10] and [11] has often overlooked some of these features, leading to incomplete information." Output is binary: 0 = static, 1 = dynamic, cᵢ = argmax(M(vᵢ)). Claimed as "the first time that machine learning-based method introduced for distinguishing dynamic and static feature points in the SLAM field."
2. **System structure** — built on ORB-SLAM2 "with an extra dynamic and static object discriminator module to filter dynamic feature points." Flow: stereo ORB extraction → YOLOv7 + Deep Sort detection/tracking on the left image → **Depth Filter Module (DFM)** treats features outside the depth band [μ_d − ηδ_d, μ_d + ηδ_d] (η = 1.2) inside a box as background/static, compensating for loose detection boxes → **coarse pose** from out-of-box + DFM-filtered static points → **MLP labels** remaining in-box points → **fine pose** by minimizing reprojection error over all static points.
3. **Benchmark contribution** — a public dataset of "over 50,000 feature points" from KITTI Odometry sequences 00/01, manually labeled 1:1 dynamic:static, split 70/20/10.

### Evidence of effectiveness
| Method | Accuracy | F1 |
|---|---|---|
| **MLP (proposed)** | **87.71** | **87.64** |
| SVM | 84.19 | 84.58 |
| ~PointSLOT | 81.36 | 81.43 |
| ~CFP-SLAM | 73.61 | 71.10 |
| e_D only | 60.10 | 61.32 |

Full-system claim: "our proposed MLP-based realtime stereo SLAM system achieves the highest average precision and fastest speed on the outdoor KITTI Odometry and KITTI360 datasets compared to other dynamic SLAM systems" (baselines: ORB-SLAM2, DynaSLAM, modified VDO-SLAM). Qualitative check vs DynaSLAM (Fig. 1): DynaSLAM mislabels highway-guardrail and parked-car features as dynamic; MLP-SLAM "correctly predicts them as static."

**Sources (KB 计算机与人工智能):** `robotics__2410.10669__mlp-slam-multilayer-perceptron-based-simultaneou.md (part 1 of 2).md` — Abstract, §I Introduction, §III-C/D, §IV-A–E, §V-A/B; `(part 2 of 2).md` — §VI Conclusions, Table III. Credibility: **P0** direct paper content (15/17 judge segments survived, scores 0.70–0.94).

---
### BQ10（gold 2604.01385；131s，$0.38，6 turns，关键词 2/2）

**问题**：What strategies for tumor control emerge under immune evasion and chemotherapy resistance?

**真实回答原文**：

**Bottom line: in the retrieved corpus, tumor control under immune evasion + chemoresistance is not achieved by any single modality — the paper's central result is that control emerges from *phenotype-guided combination immuno-chemotherapy*, delivered in a sequence matched to which resistant subpopulation dominates, with "control rather than elimination" (adaptive therapy) as the fallback when elimination is not reachable.**

The only relevant match across the pinned KBs is one modeling study — Mokari & Morsky, *Strategies for tumor elimination and control under immune evasion and chemotherapy resistance* (immunology__2604.01385, 3 parts, KB 生命科学与医学 / `b28f0a25…`). Evidence grade: **P0 as direct evidence of what the paper argues**, but note it is an ODE/mathematical-oncology model (B-cell lymphoma, two tumor subpopulations T1 immune-resistant, T2 immune-sensitive/possibly chemo-resistant), not clinical trial data.

**1. Combination is the enabling condition.** "Immune dynamics alone are generally insufficient to fully eliminate the tumor"; adding chemotherapy "significantly enlarges the parameter region corresponding to tumor control or tumor-free equilibria," and "combination immuno-chemotherapy provides greater flexibility and improved tumor control compared to single-therapy approaches" (part 3, §3.3, Discussion).

**2. Adaptive therapy — control over eradication.** From part 1: adaptive therapy "seeks to control rather than eliminate the tumor by maintaining a balance between drug-sensitive and drug-resistant cells," unlike maximum-tolerated-dose (MTD) strategies; combination therapy "can reduce the likelihood that any single clone can survive," but "success… depends heavily on timing, dosing, and sequence."

**3. Phenotype-guided selection (which evasion mechanism dominates).**
- *Immune checkpoint regulation dominant:* "tumor control is primarily achieved by decreasing immune exhaustion (μ) or increasing immune activation (ρ and σ). In this case, checkpoint inhibitors combined with moderate chemotherapy provide the most effective control strategy." Control is "highly sensitive to the immune exhaustion rate."
- *Reduced antigen presentation dominant:* stability "depends more strongly on effector activation and exhaustion," supporting "checkpoint inhibitors, CAR-T therapy, or cancer vaccines"; this phenotype is "more robust against relatively weak chemotherapy."
- *Immune-sensitive (T2) phenotype dominant:* "boosting effector recruitment and persistence becomes critical. Adoptive T-cell transfer or cytotoxic therapy are then the preferred therapies."

**4. Sequential protocols by tumor composition (part 3, Discussion).**
- T1-dominant: chemotherapy first to reduce burden → immunotherapy to maintain control; or immunotherapy first → chemotherapy to "eliminate residual resistant cells."
- T2-dominant: chemotherapy reduces burden but "can also lead to resistant escape; therefore, immunotherapy is typically applied afterward to stabilize the system."
- Predicted coexistence: "first… apply a chemotherapy thereby eliminating T1 cells," leaving a low T2-only equilibrium, then immunotherapy may eliminate the tumor — with the caveat that "if the tumor is only controlled, the emergence of T1 mutants could result in resurgence."

**5. The elimination threshold.** Proposition 1 (part 2, §3.1): the tumor-free equilibrium is stable iff effective immune strength exceeds maximal effective tumor growth, σ/(δ+ωχ) > max{α₂−θ₂χ, (α₁−χ)/θ₁}. Practically: raise effector recruitment σ, lower effector death δ, or raise activation ρ.

**6. Why uniform treatment fails.** Efficacy "depends on both the immune evasion mechanism and dominant tumor phenotype," and "modest parameter changes can induce qualitative transitions between immune control and tumor escape" — hence bistability and the paper's call for marker/composition-guided therapy.

Not found: no clinical-trial or drug-level protocols in the pinned KBs (AI, quantum, power-systems, economics KBs returned no relevant hits); the remaining hits were duplicate chunks of this same document.

## 对照组关键事实（详见 answers_historical_pfc.json 全文）

- **BQ01 / F(文件工具对照)**：grounded=True, kw 3/3, cited=False；开头摘录：**Answer (from evidence retrieved this session):**  The Transformer computes attention as a query–key–value mapping: it takes the dot products of the query with all keys, divides e…
- **BQ01 / C(分块复制对照)**：grounded=True, kw 3/3, cited=True；开头摘录：**Answer (from retrieved chunks only — all from "Attention Is All You Need", arXiv 1706.03762):**  An attention function maps a query and a set of key–value pairs, all vectors, to …
- **BQ02 / F(文件工具对照)**：grounded=True, kw 2/2, cited=True；开头摘录：**Answer**  NISQ stands for "Noisy Intermediate-Scale Quantum," a term coined by John Preskill for the era of quantum computers with roughly 50 to a few hundred qubits — "intermedi…
- **BQ02 / C(分块复制对照)**：grounded=True, kw 2/2, cited=False；开头摘录：**Answer.** The retrieved sources define NISQ technology as "Noisy Intermediate-Scale Quantum" — a term coined by John Preskill for the era of quantum computers with roughly 50 to …
- **BQ03 / F(文件工具对照)**：grounded=True, kw 2/2, cited=True；开头摘录：**Answer.** MultiMedQA is a benchmark curated in the paper "Large Language Models Encode Clinical Knowledge": it comprises seven medical question-answering datasets — six existing …
- **BQ03 / C(分块复制对照)**：grounded=True, kw 2/2, cited=True；开头摘录：**Answer:** MultiMedQA is a benchmark for medical question answering, curated in the Med-PaLM paper, that spans medical exam questions, medical research questions, and consumer med…
- **BQ04 / F(文件工具对照)**：grounded=True, kw 3/3, cited=True；开头摘录：The three ontologies that subdivide the Gene Ontology are **Molecular Function (MF)**, **Biological Process (BP)**, and **Cellular Component (CC)**.  The retrieved source states th…
- **BQ04 / C(分块复制对照)**：grounded=True, kw 3/3, cited=False；开头摘录：The three distinct ontologies that subdivide the Gene Ontology are **Molecular Function (MF), Biological Process (BP), and Cellular Component (CC)**, which represent different biol…
- **BQ05 / F(文件工具对照)**：grounded=True, kw 1/1, cited=True；开头摘录：Evidence retrieved and verified (only one corpus file discusses this topic). Answer:  **Why historical European economic growth contradicts Unified Growth Theory, per the source:**…
- **BQ05 / C(分块复制对照)**：grounded=True, kw 1/1, cited=False；开头摘录：**Answer (all evidence from a single retrieved paper, Nielsen 2015, arXiv:1512.08067, retrieved via `kb_search_vector` on Corpus-Chunks800):**  Historical European economic growth …
- **BQ06 / F(文件工具对照)**：grounded=True, kw 1/1, cited=True；开头摘录：**Answer.** According to the retrieved review, the response of precipitation extremes to climate change is primarily controlled by the **thermodynamic factor: the warming-driven in…
- **BQ06 / C(分块复制对照)**：grounded=True, kw 1/1, cited=False；开头摘录：**Answer:** The retrieved evidence identifies the **thermodynamic factor — the warming-driven increase in the atmosphere's saturation vapor pressure (moisture content), i.e., Claus…
- **BQ07 / F(文件工具对照)**：grounded=True, kw 2/2, cited=True；开头摘录：**MameLoshnLM is the first open-source large language model built specifically for Yiddish**, created by continued pretraining of Llama 3.1 8B on *Oytser*, a purpose-built high-qua…
- **BQ07 / C(分块复制对照)**：grounded=True, kw 2/2, cited=False；开头摘录：MAMELOSHNLM is the first open-source large language model built specifically for Yiddish, named after "Mame-Loshn" ("mother tongue"), and it is an 8B-parameter model produced by co…
- **BQ08 / F(文件工具对照)**：grounded=True, kw 2/2, cited=False；开头摘录：**Answer:** Oxygen (anionic) redox contributes to cathode capacity because oxide anions donate electrons during charging — acting as reducing agents — compensating for the absence …
- **BQ08 / C(分块复制对照)**：grounded=True, kw 2/2, cited=False；开头摘录：Answer: Oxygen redox contributes to cathode capacity by having oxide anions (O²⁻) donate electrons during charging — effectively acting as reducing agents that compensate for the a…
- **BQ09 / F(文件工具对照)**：grounded=True, kw 1/2, cited=False；开头摘录：**Answer (evidence retrieved this session):**  MLP-SLAM addresses the degradation of visual SLAM in dynamic environments: standard systems (e.g., ORB-SLAM2/3, LSD-SLAM, DSO) rely o…
- **BQ09 / C(分块复制对照)**：grounded=True, kw 2/2, cited=False；开头摘录：**Answer (from retrieved chunks only):**  The retrieved paper "MLP-SLAM: Multilayer Perceptron-Based Simultaneous Localization and Mapping" addresses the degradation of visual SLAM…
- **BQ10 / F(文件工具对照)**：grounded=True, kw 2/2, cited=True；开头摘录：**Answer**  The only corpus evidence on this question is the paper "Strategies for tumor elimination and control under immune evasion and chemotherapy resistance" (Mokari & Morsky)…
- **BQ10 / C(分块复制对照)**：grounded=True, kw 1/2, cited=False；开头摘录：**Answer (from retrieved chunks only):** The retrieved evidence—all from one paper, `immunology__2604.01385__strategies-for-tumor-elimination-and-control`—identifies several tumor-…