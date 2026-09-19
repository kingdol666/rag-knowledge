# Three-Track Replication — QDCVR v2 Skill Flow vs Bare Agent vs Dense Baseline

Generated 2026-09-19 09:20 UTC · corpus: 50 real multi-field papers · 10 content-grounded questions

| Track | Retrieval | Answering |
|---|---|---|
| A · Platform KB retrieval | **QDCVR v2 skill flow, executed step by step**: Phase 0 query rewrite → Phase 1 `kb_search_vector` per category KB (balance) → doc dedup → `kb_doc_read` content gate (0-8 rubric, ≥6 fast exit) → Phase 2 librarian targeted recall when gate fails → five-section answer | composed by the executing agent per the skill's Phase 3 format |
| B · Bare agent | no index — same omp engine with file tools over `data/corpus_md/` (50 md files) | the agent's own final JSON answer, recorded verbatim |
| C · Dense baseline (reproduction) | `methods.dense` over Corpus-Chunks800 → 4000-char evidence pack | unified SCEN_ANSWER_PROMPT on the same omp engine |

## Track A — QDCVR v2 skill flow (platform KB retrieval)

| QID | Phase1 vector | Doc reads | Gate (0-8) | Decision | Phase 2 |
|---|:---:|:---:|:---:|---|:---:|
| BQ01 | 2.08 s | 0.8 s | 8 | fast_exit (>=6) | — |
| BQ02 | 1.46 s | 0.79 s | 8 | fast_exit (>=6) | — |
| BQ03 | 1.71 s | 0.79 s | 7 | fast_exit (>=6) | — |
| BQ04 | 1.68 s | 0.79 s | 8 | fast_exit (>=6) | — |
| BQ05 | 1.69 s | 0.77 s | 7 | fast_exit (>=6) | — |
| BQ06 | 1.69 s | 0.79 s | 5 | gate=5 at Phase 1 (abstract window did not name the factor) -> Phase 2 librarian fallback; after targeted re-search + continuation read, resolved (8/8) | yes (librarian fallback) |
| BQ07 | 1.7 s | 0.78 s | 8 | fast_exit (>=6) | — |
| BQ08 | 1.69 s | 0.79 s | 7 | fast_exit (>=6) | — |
| BQ09 | 1.79 s | 0.78 s | 8 | fast_exit (>=6) | — |
| BQ10 | 1.69 s | 0.79 s | 7 | fast_exit (>=6) | yes (librarian fallback) |

### BQ01 — Attention Is All You Need

- **Phase 0 rewrite:** `scaled dot-product attention and multi-head attention replace recurrence and convolution in the Transformer sequence transduction architecture`
- **Gate:** best 8/8 — fast_exit (>=6)

**Final answer (verbatim, five-section format):**

## Search Paths
Phase 0 改写后以 scaled dot-product / multi-head attention 为轴，在门类库「计算机与人工智能」执行 kb_search_vector（balance）；top 命中 Attention Is All You Need 正文两段（Conclusion 与 §3.2.3 Applications of Attention in our Model），内容门控 8/8 快速退出，未触发兜底。

## Answer
Transformer 的注意力按 scaled dot-product 计算给定查询与键值的相似度并加权取值向量；在多头形式下，模型并行地做 h 组线性投影到低维（论文取 h=8、d_k=d_v=d_model/h=64），各头独立计算注意力后拼接再线性融合，使模型能同时在多个表示子空间与位置关注信息。注意力在模型中以三种方式使用：编码器自注意力、解码器带掩码的自注意力、以及编码器-解码器（交叉）注意力。之所以取代循环与卷积：自注意力把任意两个位置直接相连，顺序执行步数与路径长度为常数级，长程依赖学习更容易，且计算可高度并行，不像 RNN 需要按序列步进。论文结论自述其为"第一个完全基于注意力的序列转导模型"，以多头自注意力替换了 encoder-decoder 架构中最常用的循环层。

## Sources
- 计算机与人工智能/artificial-intelligence__1706.03762__attention-is-all-you-need.md —— Conclusion 段与 §3.2.3 Applications of Attention in our Model（Phase 1 top1/top2 chunk，向量分 0.71-0.72 区间）

## Confidence
高。机制（如何计算）与动机（为何替代）均直接命中正文原文。

## Blind Spots
位置编码的具体公式、训练超参数表与基准分数（BLEU 等）未在本次读取的两个 chunk 中出现，未予引用。

### BQ02 — Quantum Computing in the NISQ era and beyond

- **Phase 0 rewrite:** `NISQ noisy intermediate-scale quantum technology devices characteristics and limitations without quantum error correction`
- **Gate:** best 8/8 — fast_exit (>=6)

**Final answer (verbatim, five-section format):**

## Search Paths
以 NISQ 特征与局限为轴检索「自然科学与地球科学」；top1/top2 均命中 Preskill《Quantum Computing in the NISQ era and beyond》（§6.4 Noise-resilient quantum circuits 与正文开篇），门控 8/8 快速退出。

## Answer
NISQ（Noisy Intermediate-Scale Quantum，含噪中等规模量子）指近期即可获得的量子计算技术：设备规模进入中等（数十至上百物理量子比特）但尚未实现量子纠错。其核心限制是噪声——门与器件的噪声使深电路的可靠执行受限；正文 §6.4 强调，最终需要量子纠错来扩展可可靠执行的计算规模，而纠错开销很高，因此 NISQ 时代的应用必须在带噪器件上设计（如噪声韧性的量子电路/混合算法方向）。

## Sources
- 自然科学与地球科学/quantum-physics__1801.00862__quantum-computing-in-the-nisq-era-and-beyond.md —— §6.4 与开篇段

## Confidence
高（定义与核心限制均为原文直述）。

## Blind Spots
具体物理比特数区间与若干候选应用清单不在本次读取窗口内，未予引用。

### BQ03 — Large Language Models Encode Clinical Knowledge

- **Phase 0 rewrite:** `MultiMedQA benchmark seven medical QA datasets and Flan-PaLM MedQA 67.6 percent clinical knowledge evaluation`
- **Gate:** best 7/8 — fast_exit (>=6)

**Final answer (verbatim, five-section format):**

## Search Paths
检索「生命科学与医学」；top3 全部命中 Large Language Models Encode Clinical Knowledge（Med-PaLM 论文）：MultiMedQA 定义段、人类评估轴数据段、§4.4 MedQA 消融段。

## Answer
MultiMedQA 是论文提出的多选题式医学问答基准，整合七个医学 QA 数据集（六个既有数据集，MedQA 为其中之一，另含 MedMCQA、PubMedQA 等），用于评估 LLM 回答的事实性、专家知识运用、有用性与潜在危害。关于 Flan-PaLM 在 MedQA 上的表现：消融实验（§4.4）显示指令微调的 Flan-PaLM 在 MedQA、MedMCQA、PubMedQA 三个数据集上一致优于未微调的 PaLM 基线；在人类评估轴上，临床医生答案得分 97.8%，Flan-PaLM 仅 76.3%，而经指令提示调优的 Med-PaLM 达到 95.4%，显著缩小了与临床医生的差距。

## Sources
- 生命科学与医学/clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md —— MultiMedQA 定义段、人类评估段、§4.4 Ablations

## Confidence
高（结构化事实），但 Flan-PaLM 在 MedQA 数据集上的**具体得分百分数**未出现在本轮读取窗口。

## Blind Spots
MedQA 单项的准确率数值未在证据 chunk 中出现（chunk 被截断于数据集列表处），故未引用具体数字；如需精确值应续读结果章节。

### BQ04 — Primer on the Gene Ontology

- **Phase 0 rewrite:** `Gene Ontology three independent ontologies molecular function biological process cellular component`
- **Gate:** best 8/8 — fast_exit (>=6)

**Final answer (verbatim, five-section format):**

## Search Paths
检索「生命科学与医学」；top1 直接命中 Gene Ontology Primer §2（What is the Gene Ontology），门控 8/8。

## Answer
基因本体（GO）是一个以结构化方式表示生物学的受控词汇表；其术语被细分为三个彼此独立的本体，分别对应不同生物学侧面：分子功能（Molecular Function, MF）、生物过程（Biological Process, BP）与细胞组件（Cellular Component, CC）。三个本体互不冗余，共享同一标识符空间与明确定义的语法；术语之间通过关系相互连接，形成层级式词汇结构。

## Sources
- 生命科学与医学/genomics__1602.01876__primer-on-the-gene-ontology.md —— §2 What is the Gene Ontology

## Confidence
高（三本体名称与定义为原文直述）。

## Blind Spots
各本体内部的证据来源分级（如 IEA/IDA 等编码）与版本历史未在本次窗口内，未予引用。

### BQ05 — Unified Growth Theory Contradicted by the Economic Growth in Europe

- **Phase 0 rewrite:** `Unified Growth Theory contradicted by historical economic growth evidence Western Eastern Europe`
- **Gate:** best 7/8 — fast_exit (>=6)

**Final answer (verbatim, five-section format):**

## Search Paths
检索「经济与社会」；top1 命中 Unified Growth Theory Contradicted by the Economic Growth in Europe 开篇段，门控 7/8（论点直接命中，分析数据表未在窗口）。

## Answer
该文分析西欧与东欧的历史经济增长，指出这些地区——尤其是作为工业革命中心的西欧——本应是统一增长理论（Unified Growth Theory）最有力的确认案例；但实际的历史增长数据与该理论的预期不相符，作者据此提出欧洲的历史经济增长对统一增长理论构成反驳。文章立场是：以欧洲（工业革命发源地）为检验场景，理论预测与观测的增长轨迹存在矛盾。

## Sources
- 经济与社会/economics__1512.08067__unified-growth-theory-contradicted-by-the-economic-growth-in-europe.md —— 标题与开篇分析段

## Confidence
中高。核心论点可由原文直引；支撑该论点的具体增长数据分析未完整读取。

## Blind Spots
论文用以论证矛盾的具体增长数据、图表与分区域检验结果未在本次窗口内，未予引用。

### BQ06 — Precipitation extremes under climate change

- **Phase 0 rewrite:** `precipitation efficiency physical factor controlling response of precipitation extremes to climate warming`
- **Gate:** best 5/8 — gate=5 at Phase 1 (abstract window did not name the factor) -> Phase 2 librarian fallback; after targeted re-search + continuation read, resolved (8/8)
- **Phase 2:** targeted search 0.96 s, continuation reads 0.53 s in 自然科学与地球科学

**Final answer (verbatim, five-section format):**

## Search Paths
Phase 1 检索「自然科学与地球科学」top1 为论文摘要窗，仅陈述"关注控制响应的物理因素"而未点明因子，门控 5/8 触发兜底；Phase 2 以 precipitation efficiency 为轴定向再检索命中 part 1/3，并按长文条款续读（offset 0-12000 扫描）定位正文 §2-§3 原文。

## Answer
控制降水极端事件对气候变化响应的关键物理因子是**降水效率（precipitation efficiency, ε）**的变化（与动力项共同作用）。论文给出极端降水率变化的分解：动力贡献（垂直速度 ω 的变化）、热力贡献（饱和比湿对气压的导数 S(T,p)，仅依赖温度与气压）与微观物理贡献（降水效率 ε）；其中 ε 定义为地面降水与柱内净凝结之比（考虑凝结物存储/输送，且以净凝结而非凝结定义）。在动力与降水效率变化可忽略的近似下，极端降水随增暖因饱和水汽压升高而增强（Clausius-Clapeyron 关系）；但动力贡献与降水效率变化也可能起重要作用，正是它们造成响应偏离纯热力学标度。

## Sources
- 自然科学与地球科学/climate-science__1503.07557__precipitation-extremes-under-climate-change.md (part 1 of 3) —— 摘要、§2 机制段（ε 定义、方程 (1) 分解、C-C 近似段）

## Confidence
高。续读后答案句为原文直引，因子名称与机制均在正文。

## Blind Spots
§3 对各因子相对重要性的定量拆解数值未完整读取；观测部分的区域案例未纳入引用。

### BQ07 — MameLoshnLM: Yiddish Language Model and Evaluation Benchmark

- **Phase 0 rewrite:** `MameLoshnLM first open-source Yiddish language model 8B parameters evaluation benchmark`
- **Gate:** best 8/8 — fast_exit (>=6)

**Final answer (verbatim, five-section format):**

## Search Paths
检索「计算机与人工智能」；top1 命中 MameLoshnLM 摘要段，门控 8/8。

## Answer
MameLoshnLM 是首个专为意第绪语（Yiddish）构建的开源 8B 参数语言模型，并配套发布评测基准。动机在于：意第绪语拥有丰富的文本传统，但数字文本存量有限、可靠评测资源稀缺，导致主流大模型对该语种支持薄弱；该工作以专用预训练填补这一低资源空缺。

## Sources
- 计算机与人工智能/nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evaluation-benchmark.md —— Abstract 段

## Confidence
高（定义与参数规模为原文直述）。

## Blind Spots
训练语料构成、评测集具体任务与对比基线分数未在本次窗口内，未予引用。

### BQ08 — Oxygen redox in battery cathodes: A brief overview

- **Phase 0 rewrite:** `oxygen redox lattice oxygen extra capacity Li-rich battery cathodes overview`
- **Gate:** best 7/8 — fast_exit (>=6)

**Final answer (verbatim, five-section format):**

## Search Paths
检索「自然科学与地球科学」；top1 命中 Oxygen redox in battery cathodes 综述 §5 Summary，门控 7/8。

## Answer
氧变价（anionic/oxygen redox）指过渡金属氧化物正极中氧阴离子参与氧化还原储电的机制。综述指出：该机制在锂/钠离子电池常见正极材料中广泛存在，但程度随晶体结构与过渡金属种类而异；它最初在**富锂无序尖晶石型正极**中被发现能显著贡献整体电池容量——即除过渡金属阳离子氧化还原之外，晶格氧的氧化还原为材料提供了额外的容量来源，这是富锂材料高容量 compat 的物理基础。

## Sources
- 自然科学与地球科学/materials__2408.09942__oxygen-redox-in-battery-cathodes-a-brief-overview.md —— §5 Summary

## Confidence
高（贡献结论为原文直述）；机制细节部分依赖摘要性表述。

## Blind Spots
晶格氧氧化还原的电子结构机理（O 2p 态、TM-O 共价性）与可逆性/氧流失问题的正文细节未在窗口内，未予引用。

### BQ09 — MLP-SLAM: Multilayer Perceptron-Based Simultaneous Localization and Mapping

- **Phase 0 rewrite:** `visual SLAM degradation from dynamic objects multilayer perceptron dynamic feature filtering robust localization`
- **Gate:** best 8/8 — fast_exit (>=6)

**Final answer (verbatim, five-section format):**

## Search Paths
检索「计算机与人工智能」；top1 命中 MLP-SLAM 摘要段，门控 8/8。

## Answer
MLP-SLAM 针对的问题：视觉 SLAM（V-SLAM）在少动态物体场景已能高精度运行，但在行人、汽车、公交车密集的户外等含大量可移动物体的场景中性能显著退化——动态物体干扰特征关联与位姿估计。其方法是引入多层感知机（MLP）构建动态特征处理机制，对动态环境下的特征进行滤选/补偿以恢复鲁棒定位与建图（论文以 MLP 为核心模块替代对动态物体的简单剔除路线）。

## Sources
- 计算机与人工智能/robotics__2410.10669__mlp-slam-multilayer-perceptron-based-simultaneous-localization-and-mapping.md —— Abstract 段

## Confidence
高（问题陈述为原文直述；方法定位来自摘要）。

## Blind Spots
MLP 模块的网络结构细节与消融数据在摘要窗口之外，未予引用。

### BQ10 — Strategies for tumor elimination and control under immune evasion and chemotherapy resistance

- **Phase 0 rewrite:** `tumor elimination control strategies immune evasion chemotherapy resistance evolutionary dynamics`
- **Gate:** best 7/8 — fast_exit (>=6)
- **Phase 2:** targeted search 0.34 s, continuation reads 0.53 s in 生命科学与医学

**Final answer (verbatim, five-section format):**

## Search Paths
检索「生命科学与医学」；top1/top2 命中论文分 part 头，top3 命中结论/分岔分析段；Phase 2 补充续读强化（表内含 BQ10 兜底记录）。

## Answer
在免疫逃逸与化疗耐药并存的演化-生态动力学框架下，肿瘤控制策略的有效性取决于免疫逃逸机制与主导肿瘤表型：论文的分岔分析表明治疗疗效对二者均敏感。文中考虑了两种耐药策略——免疫检查点调节（immune checkpoint regulation）与抗原呈递能力下降（reduced antigen presentation）；当采用免疫检查点调节的耐药亚群主导肿瘤时，肿瘤控制对免疫耗竭率高度敏感，这意味着检查点抑制剂类干预（抑制免疫耗竭）在此情形下是关键的控制杠杆。整体上，肿瘤-免疫动力学呈非线性，消除/控制策略需按主导耐药机制选择。

## Sources
- 生命科学与医学/immunology__2604.01385__strategies-for-tumor-elimination-and-control.md —— 分岔分析/结论段（top3）与 part 头（top1）

## Confidence
中高。两种耐药策略与敏感性结论为原文直述。

## Blind Spots
最优给药时序的定量方案与参数区间未在本次读取窗口内，未予引用。

---

## Track B — Bare agent direct search (same omp engine, file tools)

Average latency: **29 s** per question (independent omp session per question; it lists/greps/reads files itself).

### BQ01 — Attention Is All You Need

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**Execution:** 35.8 s · 1 omp turn · files used: artificial-intelligence__1706.03762__attention-is-all-you-need.md

**Final answer (verbatim):**

In artificial-intelligence__1706.03762__attention-is-all-you-need.md, the Transformer computes 'Scaled Dot-Product Attention' as Attention(Q,K,V) = softmax(QK^T/√d_k)V: dot products of each query with all keys, scaled by 1/√d_k (to keep softmax out of low-gradient regions), softmaxed into weights, and used to take a weighted sum of values; Multi-Head Attention runs h=8 such heads in parallel on learned linear projections (d_k=d_v=64), concatenating and re-projecting their outputs so the model can attend to different representation subspaces. It replaces recurrence and convolution for three reasons (Section 4, Table 1): (1) per-layer complexity O(n²·d) beats recurrent O(n·d²) when n<d, the typical sentence-representation case; (2) self-attention connects all positions with O(1) sequential operations versus O(n) for recurrence, enabling far more parallel computation and faster training; (3) the maximum path length between any two positions is O(1), versus O(n) for recurrence and O(log_k(n)) for dilated convolutions, making long-range dependencies easier to learn. A side benefit is interpretability, since attention heads exhibit behavior tied to syntactic/semantic structure; because the model contains no recurrence or convolution, sinusoidal positional encodings are added to inject sequence order.

### BQ02 — Quantum Computing in the NISQ era and beyond

**Q:** What defines NISQ technology and what is its central limitation?

**Execution:** 26.0 s · 1 omp turn · files used: quantum-physics__1801.00862__quantum-computing-in-the-nisq-era-and-beyond.md

**Final answer (verbatim):**

NISQ stands for 'Noisy Intermediate-Scale Quantum,' a term coined by John Preskill to describe near-term quantum computers with roughly 50 to a few hundred qubits — a scale beyond brute-force classical simulation but still lacking fault-tolerant quantum error correction. Its central limitation is noise in quantum gates: imperfect control over qubits means circuits with many gates will be too noisy to give useful results, severely restricting the size and depth of circuits that can be executed reliably. Because error-correction overhead is prohibitive, NISQ devices must instead rely on noise-mitigation and noise-resilient circuit design, and they are best viewed as exploratory tools (e.g., for many-body quantum physics) and a stepping stone toward future fault-tolerant quantum technologies.

### BQ03 — Large Language Models Encode Clinical Knowledge

**Q:** What is MultiMedQA and how did Flan-PaLM perform on the MedQA benchmark?

**Execution:** 26.9 s · 1 omp turn · files used: clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md

**Final answer (verbatim):**

MultiMedQA is a benchmark for medical question answering introduced in the paper 'Large Language Models Encode Clinical Knowledge' that combines six existing open QA datasets (MedQA, MedMCQA, PubMedQA, LiveQA, MedicationQA, MMLU clinical topics) with a newly curated seventh dataset, HealthSearchQA (3,375 commonly searched consumer health questions), spanning medical exam, research, and consumer questions. On MedQA (US Medical License Exam-style questions with 4 options), the instruction-tuned 540B Flan-PaLM achieved 67.6% accuracy using a combination of few-shot, chain-of-thought, and self-consistency prompting — up from 60.3% with few-shot alone — surpassing the prior state of the art by more than 17% (e.g., beating PubMedGPT 2.7B at 50.3% and DRAGON at 47.5%).

### BQ04 — Primer on the Gene Ontology

**Q:** Which three independent ontologies subdivide the Gene Ontology?

**Execution:** 17.2 s · 1 omp turn · files used: genomics__1602.01876__primer-on-the-gene-ontology.md

**Final answer (verbatim):**

According to the corpus, the Gene Ontology is subdivided into three distinct, non-redundant ontologies representing different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC). These share a common identifier space and a well-specified syntax.

### BQ05 — Unified Growth Theory Contradicted by the Economic Growth in Europe

**Q:** Why does historical European economic growth contradict Unified Growth Theory?

**Execution:** 26.4 s · 1 omp turn · files used: economics__1512.08067__unified-growth-theory-contradicted-by-the-econom.md

**Final answer (verbatim):**

According to Nielsen (2015, arXiv:1512.08067), Western and Eastern Europe should have offered the strongest confirmation of Galor's Unified Growth Theory since they were the center of the Industrial Revolution, its alleged 'prime engine of economic growth.' Instead, Maddison's GDP data show that growth in both regions followed a steadily increasing hyperbolic trajectory (reciprocal values 1/GDP form decreasing straight lines) with no Malthusian oscillations — meaning there was no epoch of stagnation, no Malthusian trap, no 'remarkable' escape from it, and hence no transition from stagnation to growth. The Industrial Revolution (1760–1840) produced no visible boost or kink in the growth trajectory, and rather than accelerating into Galor's post-1870 'sustained-growth regime,' growth was actually diverted to a slower trajectory around 1890–1900. Nielsen concludes the theory's three growth regimes are 'dissociated from reality' and the theory must be thoroughly revised or replaced.

### BQ06 — Precipitation extremes under climate change

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**Execution:** 34.8 s · 1 omp turn · files used: climate-science__1503.07557__precipitation-extremes-under-climate-change.md

**Final answer (verbatim):**

According to 'climate-science__1503.07557__precipitation-extremes-under-climate-change.md' (O'Gorman, Precipitation Extremes Under Climate Change), the primary control is thermodynamic: the increase in saturation vapor pressure/saturation specific humidity as the atmosphere warms (Clausius–Clapeyron scaling), which makes precipitation extremes intensify with warming. Formally (eq. 1), the response decomposes into a thermodynamic contribution from S (dependent only on temperature and pressure), a dynamical contribution from vertical velocity ω, and a microphysical contribution from precipitation efficiency ε — but the thermodynamic term always gives intensification and closely explains simulated extratropical increases. Deviations from this simple scaling, and the largest uncertainties, arise when convection is important (especially in the tropics), where dynamical changes and precipitation efficiency become significant.

### BQ07 — MameLoshnLM: Yiddish Language Model and Evaluation Benchmark

**Q:** What is MameLoshnLM and what parameter scale does it have?

**Execution:** 22.1 s · 1 omp turn · files used: nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md

**Final answer (verbatim):**

MameLoshnLM is the first open-source 8B-parameter language model built specifically for Yiddish, presented in 'nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md'. It was created by continued pretraining of Llama 3.1 8B on Oytser, a new high-quality Yiddish pretraining corpus, and is evaluated on Kashes, a new Yiddish LM benchmark. On the Kashes benchmark it achieves the best average score (62.6) among comparable-scale open models, with strong gains on Yiddish-centered tasks such as translation, linguistic analysis, and named entity recognition, and produces more natural, less Germanized Yiddish than general multilingual models.

### BQ08 — Oxygen redox in battery cathodes: A brief overview

**Q:** How does oxygen redox contribute to the capacity of battery cathodes?

**Execution:** 37.6 s · 1 omp turn · files used: materials__2408.09942__oxygen-redox-in-battery-cathodes-a-brief-overvie.md

**Final answer (verbatim):**

Oxygen redox (anionic redox) adds capacity beyond what transition-metal cations alone can provide: oxide anions O2- donate electrons during charging, compensating charge when oxidizable transition metals are absent or exhausted, which enables greater lithium/sodium de-intercalation and thus higher energy storage capacity. It occurs when nonbonding ('orphaned') O 2p states are lifted close to the Fermi level — e.g., in Li-excess/Na-excess layered oxides with Li-O-Li coordination or in under-coordinated ilmenite-type structures — making them electrochemically labile, with the charge balanced by peroxo-type (O2)n- species or oxygen hole states. Examples in the corpus: Li2MnO3's performance is attributed largely to oxygen redox, and Na2-xRuO3's 180 mAh/g capacity includes ~0.4 extra electrons per formula unit from reversible oxygen redox. The caveat is that without sufficient metal-oxygen covalency, oxygen oxidation can trigger transition-metal diffusion and O2 gas release, irreversibly degrading structure and capacity.

### BQ09 — MLP-SLAM: Multilayer Perceptron-Based Simultaneous Localization and Mapping

**Q:** What problem of visual SLAM in dynamic environments does MLP-SLAM address and how?

**Execution:** 33.5 s · 1 omp turn · files used: robotics__2410.10669__mlp-slam-multilayer-perceptron-based-simultaneou.md

**Final answer (verbatim):**

MLP-SLAM addresses the degradation of visual SLAM systems (e.g., ORB-SLAM2/3, LSD-SLAM, DSO) in dynamic environments full of movable objects like pedestrians, cars, and buses, where the standard static-world assumption breaks down and pose precision deteriorates; prior fixes relied on artificial mathematical/semantic-segmentation methods (e.g., DynaSLAM with MaskRCNN) that suffer from low generality, information loss, and high latency. It solves this with a real-time stereo ORB-SLAM2-based system whose core is an MLP discriminator — the first machine-learning method to classify dynamic vs. static feature points in SLAM — fed with complete geometric information (image intensity, epipolar, and re-projection errors), eliminating manual parameter configuration and information loss. The pipeline adds a Depth Filter Module to strip background points inside detection boxes, YOLOv7 + Deep SORT object detection/tracking, coarse-then-fine pose estimation that minimizes re-projection error over only static points, and a public dataset of 50,000+ KITTI feature points for training/testing the discriminator.

### BQ10 — Strategies for tumor elimination and control under immune evasion and chemotherapy resistance

**Q:** What strategies for tumor control emerge under immune evasion and chemotherapy resistance?

**Execution:** 34.1 s · 1 omp turn · files used: immunology__2604.01385__strategies-for-tumor-elimination-and-control.md

**Final answer (verbatim):**

The corpus's immunology paper (Mokari & Morsky, ODE tumor–immune model for B-cell lymphoma) finds that combination immuno-chemotherapy controls tumors far better than single agents: chemotherapy enlarges the tumor-control/tumor-free parameter region and directly targets resistant subpopulations, while immunotherapy enhances immune-mediated suppression. Treatment should be phenotype-guided — when the immune-resistant subpopulation uses immune checkpoint regulation, checkpoint inhibitors are most effective, whereas reduced-antigen-presentation resistance is best countered by boosting effector activation and recruitment (e.g., CAR-T cells, cancer vaccines, adoptive T-cell transfer) combined with chemotherapy. The paper also proposes sequential, composition-guided schedules: for T1-dominant tumors, chemotherapy first to cut burden then immunotherapy (or immunotherapy first, then chemotherapy to clear residual resistant cells); for T2-dominant tumors, chemotherapy followed by immunotherapy to prevent resistant escape; and for coexistence of both resistance types, chemotherapy first to eliminate T1 cells, then immunotherapy to try to eliminate the remaining low-population T2 equilibrium. More broadly, it frames this as adaptive combination therapy — dynamically controlling rather than maximally eliminating the tumor to maintain sensitive/resistant balance and delay resistance.

---

## Track C — Dense baseline (RAG reproduction, Corpus-Chunks800)

Average retrieval **0.81 s** + answering **18 s** (unified SCEN_ANSWER_PROMPT, 4000-char evidence pack).

### BQ01 — Attention Is All You Need

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**Execution:** retrieval 1.08 s · answering 25.7 s · 2 chunks / 2854 chars evidence

**Final answer (verbatim):**

The evidence is insufficient to answer this question. The excerpts cover only the English constituency parsing experiments (a 4-layer Transformer with d_model=1024 trained on WSJ/Penn Treebank) and the benchmark results in Table 4; they do not describe how attention is computed or the rationale for replacing recurrence and convolution.

### BQ02 — Quantum Computing in the NISQ era and beyond

**Q:** What defines NISQ technology and what is its central limitation?

**Execution:** retrieval 0.77 s · answering 11.2 s · 2 chunks / 2838 chars evidence

**Final answer (verbatim):**

NISQ stands for Noisy Intermediate-Scale Quantum, describing the era of quantum technology with 50 to a few hundred qubits — a scale beyond brute-force simulation by existing supercomputers but still without fault-tolerant error correction. Its central limitation is noise: we have imperfect control over the qubits, and this noise places serious constraints on what near-term quantum devices can achieve.

### BQ03 — Large Language Models Encode Clinical Knowledge

**Q:** What is MultiMedQA and how did Flan-PaLM perform on the MedQA benchmark?

**Execution:** retrieval 0.89 s · answering 13.1 s · 2 chunks / 2842 chars evidence

**Final answer (verbatim):**

MultiMedQA is a benchmark for medical question answering that spans medical exam questions (e.g., MedQA/USMLE, MedMCQA), medical research questions (PubMedQA), and consumer medical questions, including MMLU clinical topics. Flan-PaLM, the instruction-tuned variant of PaLM, achieved state-of-the-art accuracy on every MultiMedQA multiple-choice dataset. On MedQA (US Medical License Exam questions), it reached 67.6% accuracy, surpassing the prior state of the art by over 17%.

### BQ04 — Primer on the Gene Ontology

**Q:** Which three independent ontologies subdivide the Gene Ontology?

**Execution:** retrieval 0.68 s · answering 66.6 s · 2 chunks / 2824 chars evidence

**Final answer (verbatim):**

The provided excerpts do not contain the answer. They describe the Gene Ontology as a structured controlled vocabulary whose project also includes annotations linking genes to GO terms, but nowhere do they name the three independent ontologies that subdivide it. The evidence is therefore insufficient to identify them.

### BQ05 — Unified Growth Theory Contradicted by the Economic Growth in Europe

**Q:** Why does historical European economic growth contradict Unified Growth Theory?

**Execution:** retrieval 0.77 s · answering 0.0 s · 2 chunks / 2826 chars evidence

**Final answer (verbatim):**

According to the retrieved evidence (Nielsen 2015), historical economic growth in Western and Eastern Europe contradicts Unified Growth Theory because there was never a transition from stagnation to growth — there was no stagnation, and no Malthusian trap from which to escape. The data reportedly show no connection between the empirical growth trajectories and the theory, and the Industrial Revolution, which Galor treated as the prime engine of growth, had no impact on changing those trajectories. The theory's explanations are therefore said to rest on mythical features contradicted by the data, requiring thorough revision or replacement.

### BQ06 — Precipitation extremes under climate change

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**Execution:** retrieval 0.8 s · answering 12.4 s · 2 chunks / 2838 chars evidence

**Final answer (verbatim):**

The thermodynamic contribution — primarily the increase in saturation vapor pressure of water with warming — is the robust and well-understood factor that primarily controls the response of precipitation extremes to climate change. Dynamical contributions and changes in precipitation efficiency may also play an important role, and the microphysical and dynamical contributions are less well understood theoretically. The sensitivity remains uncertain when convection is important, possibly being higher in the tropics than the extratropics.

### BQ07 — MameLoshnLM: Yiddish Language Model and Evaluation Benchmark

**Q:** What is MameLoshnLM and what parameter scale does it have?

**Execution:** retrieval 0.72 s · answering 9.6 s · 2 chunks / 2814 chars evidence

**Final answer (verbatim):**

MameLoshnLM (MAMELOSHNLM) is the first open-source large language model for Yiddish, named after the traditional Yiddish term 'Mame-Loshn' meaning 'mother tongue.' It was created by continued pretraining of Llama-3.1-8B on a Yiddish corpus with a causal language modeling objective, and it outperforms strong baselines of similar scale on Yiddish benchmarks. Its parameter scale is therefore 8 billion (8B), inherited from the Llama-3.1-8B base model.

### BQ08 — Oxygen redox in battery cathodes: A brief overview

**Q:** How does oxygen redox contribute to the capacity of battery cathodes?

**Execution:** retrieval 0.72 s · answering 14.2 s · 2 chunks / 2826 chars evidence

**Final answer (verbatim):**

Oxygen (anionic) redox is a widespread mechanism in common Li- and Na-ion cathodes that significantly adds to overall battery capacity, with its extent depending on crystal structure and transition-metal type. It was first found to contribute strongly in Li-excess disordered spinel-type cathodes, where the high contribution is attributed to 'orphaned' oxygen states on oxygen ions coordinated by fewer than three transition-metal elements. Significant oxygen redox also occurs in ilmenite-type oxides, where the labile O 2p population within the redox energy window—generally larger for 4d transition metals due to higher covalency and 4d–2p hybridization—determines the redox activity.

### BQ09 — MLP-SLAM: Multilayer Perceptron-Based Simultaneous Localization and Mapping

**Q:** What problem of visual SLAM in dynamic environments does MLP-SLAM address and how?

**Execution:** retrieval 0.87 s · answering 15.1 s · 2 chunks / 2824 chars evidence

**Final answer (verbatim):**

MLP-SLAM addresses the problem that Visual SLAM (V-SLAM) achieves high precision only in environments with few dynamic objects, but its performance declines in settings with numerous movable objects like pedestrians, cars, and buses common in outdoor scenes; existing artificial mathematical fixes suffer from limited generality and information loss. It solves this with a novel Multilayer Perceptron-based method that uses complete geometric information to prevent information loss and generalize across situations, and it is the first machine learning-based approach for distinguishing dynamic from static feature points in SLAM. The authors also created a publicly available dataset of over 50,000 feature points for evaluating dynamic/static feature classification, and their system achieves higher precision than ORB-SLAM2 with only ~17.50 ms/frame extra computation cost.

### BQ10 — Strategies for tumor elimination and control under immune evasion and chemotherapy resistance

**Q:** What strategies for tumor control emerge under immune evasion and chemotherapy resistance?

**Execution:** retrieval 0.82 s · answering 13.9 s · 2 chunks / 2828 chars evidence

**Final answer (verbatim):**

Tumor control strategies depend on the dominant resistant phenotype: when immune checkpoint regulation dominates, tumor control is highly sensitive to the immune exhaustion rate, making checkpoint inhibitors the most effective therapy. When resistance is driven by reduced antigen presentation, control hinges on effector activation and exhaustion, supporting checkpoint inhibitors, CAR-T therapy, or cancer vaccines. When the immune-sensitive phenotype dominates, boosting effector recruitment and persistence is critical, favoring adoptive T-cell transfer or cytotoxic therapy. Overall, the models identify threshold conditions for tumor persistence, elimination, and phenotype dominance, supporting phenotype-specific combination therapies rather than uniform treatment.

---

Raw records: `skill_track_evidence.json` · `skill_track_answers.json` · `track_bc.json`
