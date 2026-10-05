# 三模式检索 × chat API 真机问答记录（3 题新设计）

- Run: `run-004648` · 生成: 2026-09-27 16:46 UTC
- 通道: 每模式真机检索(GPU Laya 判卷) → 各模式原生证据包(A 24k / B 40k / C 60k 设计预算) → 平台对外 chat API(`POST /api/claude/chat`, engine=claude, 无工具闭卷)
- 问题: 本场次新设计, 金标事实均已在语料原文核实

## Q1 [single] large-language-models

- 问题: 语言模型是如何逐步学会事实知识的？学习动力学呈现哪几个阶段、性能平台期对应什么内部机制、数据分布不均衡有何影响，以及为什么用微调向模型注入新知识会失败？(how language models learn facts dynamics curricula hallucinations)
- gold_docs: ['nlp__2503.21676__how-do-language-models-learn-facts-dynamics.md']
- gold_facts: 三个学习阶段, 平台期后才获得精确事实知识; 平台期伴随基于注意力的回忆回路形成(attention patching); 不均衡分布缩短平台期但导致过拟合; 数据课程可加速且缓解; 幻觉与知识同时出现; 微调注入新知识会快速破坏已有参数化记忆

### 模式 A

- 检索: ok=True real_engine=True engine=laya backend=laya_sdk 检索耗时 22.4s 保留文档 17 篇
- gold_hit: True {'2503.21676': True}
- chat API: 总延迟 33.4s (回答 9.6s) · tokens {'input': 6690, 'output': 310, 'cache_read': 37376, 'cache_creation': 0} · cost $0.059888

```
The retrieved evidence does not contain the answer. None of the retrieved chunks — including the Attention Is All You Need paper, the clinical-knowledge LLM paper (Singhal et al.), the Global RAG benchmark, machine-learning-for-molecular-simulation parts, or the vector-index-tuning guide — addresses how language models acquire factual knowledge, its learning dynamics/stages, performance plateaus and their internal mechanisms, data-distribution imbalance effects, or why fine-tuning fails to inject new knowledge.

Sources actually retrieved and checked: 工程与能源/mathematics__2211.12700 (part 1/5); 工程与能源/power-systems__2607.03098 (part 2/5); 自然科学与地球科学/chemistry__1911.02792 (parts 2 and 3); demo-qa-20260927/artificial-intelligence__1706.03762 (Attention Is All You Need); 生命科学与医学/genomics__2401.06823 (part 1/2); e2e-demo-0923-022632/global-rag-benchmark.md; soul-cs-library/, soul-e2e-tester-024115/, soul-demo-qa/thinking-style.md; 生命科学与医学/clinical-medicine__2212.13138 (part 1/8); AI 基础设施/vector-index-tuning-guide (part 1/2).

The evidence is insufficient to answer this question; I am not falling back on prior knowledge.
```

### 模式 B

- 检索: ok=True real_engine=True engine=laya backend=laya_sdk 检索耗时 28.9s 保留文档 35 篇
- gold_hit: True {'2503.21676': True}
- chat API: 总延迟 38.4s (回答 9.5s) · tokens {'input': 48878, 'output': 165, 'cache_read': 0, 'cache_creation': 0} · cost $0.24851499999999999

```
The evidence provided consists solely of the paper "Learning Reward Machines in Cooperative Multi-Agent Tasks" (arXiv 2303.14061), which concerns multi-agent reinforcement learning, reward machines, ILASP-based induction, and tasks such as THREEBUTTONS and RENDEZVOUS. It contains no material on language models, factual knowledge acquisition, learning dynamics or stages, performance plateaus, data distribution imbalance, knowledge injection via fine-tuning, or hallucinations. Therefore the evidence is insufficient to answer this question, and I stop here rather than draw on prior knowledge.

Sources used: none — the retrieved evidence (计算机与人工智能\artificial-intelligence__2303.14061__learning-reward-machines-in-cooperative-mult, parts 1–3) does not address the question.
```

### 模式 C

- 检索: ok=True real_engine=True engine=laya backend=laya_sdk 检索耗时 43.4s 保留文档 12 篇
- gold_hit: True {'2503.21676': True}
- chat API: 总延迟 53.6s (回答 10.0s) · tokens {'input': 16168, 'output': 363, 'cache_read': 37376, 'cache_creation': 0} · cost $0.10860299999999999

```
**Answer (from the provided evidence):**

According to the evidence, language models learn facts in three phases: first an initial language-understanding phase where the model learns generic attribute value statistics (reaching the "no knowledge baseline"), then a performance plateau, and finally a knowledge-emergence phase where it acquires individual-specific associations between subjects and attributes. The plateau length grows almost linearly with the number of individuals, supporting a statistical explanation that the model must observe multiple biographies of the same individual. Mechanistically, the plateau coincides with the formation of attention-based recall circuits; attention patching shows that replacing a model's attention patterns with post-plateau reference patterns removes the plateau, and attention to name tokens increases throughout the plateau. On data distribution, imbalanced distributions (inverse power law with exponent α) shorten the plateau — the optimal α minimizing plateau length is 0.6–0.8 — but excessive imbalance causes overfitting; knowledge acquisition speed depends on the least frequent individuals, so dynamic schedulers ("warm-up" on a subset then uniform) improve final knowledge. Fine-tuning to inject new knowledge fails for two reasons: models hallucinate (overconfident predictions on unseen individuals) as soon as they acquire individual-specific knowledge, and associative memories stored in feed-forward layers are rapidly corrupted when training on new individuals.

**Sources used:** `计算机与人工智能/nlp__2503.21676__how-do-language-models-learn-facts-dynamics.md (part 1 of 4).md` (abstract, Sections 1.1–1.4, 2.1, 2.2, 3.1, 3.2). The other two retrieved items (`vector-index-tuning-guide`, `pride_and_prejudice`) were irrelevant and not used.
```

## Q2 [single] astronomy

- 问题: CoRoT 卫星的系外行星计划有哪些科学目标？它何时开始科学观测、任务延长到什么时候？截至 2010 年夏共收集了多少条光变曲线？为什么 CoRoT-7b 这类超级地球只能在较亮恒星的光变曲线中发现？(CoRoT exoplanet program status results transit asteroseismology)
- gold_docs: ['astronomy__1105.1887__the-corot-exoplanet-program-status-results.md']
- gold_facts: 两大科学目标: 凌星法探测系外行星 + 星震学(恒星内部研究); 2007-02-02 开始科学观测; 初期 3 年, 延长 3 年至 2013-03; 截至 2010 年夏收集 129,326 条光变曲线; 超级地球(如 CoRoT-7b)只能在 R ≈ 14 以亮恒星的光变曲线中发现

### 模式 A

- 检索: ok=True real_engine=True engine=laya backend=laya_sdk 检索耗时 22.5s 保留文档 17 篇
- gold_hit: True {'1105.1887': True}
- chat API: 总延迟 30.8s (回答 6.8s) · tokens {'input': 5822, 'output': 218, 'cache_read': 37312, 'cache_creation': 0} · cost $0.053216

```
The retrieved evidence does not answer this question.

The strongest match, `自然科学与地球科学/astronomy__1105.1887__the-corot-exoplanet-program-status-results.md`, states CoRoT's two scientific objectives (transit detection of extrasolar planets and asteroseismology of stellar interiors), that scientific observations began on February 2nd 2007, and that the mission was extended by three additional years "till March 2013." However, this chunk contains no figure for the number of light curves collected by summer 2010, and it contains no discussion of CoRoT-7b or of why super-Earths are found only in light curves of brighter stars. The remaining evidence (stroke prediction, unified growth theory, Pride and Prejudice, bitvector query optimization, solar cells, global RAG benchmark, isotropic covariance estimation, spatial transcriptomics) is unrelated. The specific count and the CoRoT-7b observational-selection explanation are therefore insufficient in the provided evidence, and I cannot supply them from prior knowledge.
```

### 模式 B

- 检索: ok=True real_engine=True engine=laya backend=laya_sdk 检索耗时 7.8s 保留文档 4 篇
- gold_hit: True {'1105.1887': True}
- chat API: 总延迟 16.4s (回答 8.6s) · tokens {'input': 10497, 'output': 244, 'cache_read': 37312, 'cache_creation': 0} · cost $0.077241

```
The evidence answers all four parts.

**Answer**

CoRoT had two distinct scientific objectives, both requiring continuous observations and ultra-high-precision relative stellar photometry: detecting extrasolar planets by the transit method, and studying stellar interiors by asteroseismology. Scientific observations began on February 2nd, 2007; the mission was initially scheduled for three years but was extended for three more, i.e. until March 2013. By summer 2010, a total of 129,326 light curves had been collected. Super-Earth–size planets such as CoRoT-7b can only be discovered in the light curves of stars brighter than R ≈ 14, whereas Neptune-size planets are detectable at any stellar magnitude — the paper states this directly in the transit-signal-versus-magnitude analysis, without giving a deeper physical explanation.

**Sources used**
- `自然科学与地球科学\astronomy__1105.1887__the-corot-exoplanet-program-status-results.md` — §1 Introduction (objectives, start date, extension), §3 Detection capacity (129,326 light curves; magnitude limit for super-Earths), Figure 3 caption.
```

### 模式 C

- 检索: ok=True real_engine=True engine=laya backend=laya_sdk 检索耗时 31.2s 保留文档 12 篇
- gold_hit: True {'1105.1887': True}
- chat API: 总延迟 39.2s (回答 7.7s) · tokens {'input': 21122, 'output': 264, 'cache_read': 37376, 'cache_creation': 0} · cost $0.130898

```
The evidence does not answer this question. The retrieved document is a Project Gutenberg license page from *Pride and Prejudice* (part 26/26), which contains no information on CoRoT, exoplanets, or transit photometry; the Voyager 1 article and the TraceLens/vector-index/HNSW documents also contain nothing about the CoRoT mission. No source among those retrieved addresses the CoRoT science objectives, its observation start date, mission extension, light-curve counts, or CoRoT-7b detectability limits. The relevant CoRoT paper (`astronomy__1105.1887__the-corot-exoplanet-program-status-results.md`) appears elsewhere in the corpus but was not present in the evidence I was given.

Sources used (all irrelevant to the question): `Novel-PridePrejudice/pride_and_prejudice (part 26 of 26).md`; `demo-qa-20260927/voyager-1.md`; `AI 基础设施/tracelens-deployment-notes.md`; `AI 基础设施/vector-index-tuning-guide (part 2 of 2).md`.

Per the contract, I am reporting the evidence as insufficient and stopping rather than drawing on prior knowledge.
```

## Q3 [multi] chemistry

- 问题: 在分子科学的机器学习中,Noé 等人的综述《Machine learning for molecular simulation》与“深度空间学习 + 分子振动”数据增强方法各自如何应对数据稀缺与建模挑战？后者在聚酰胺纳滤膜实验中把相对误差和决定系数分别改善到多少？(machine learning molecular simulation molecular vibration data augmentation nanofiltration)
- gold_docs: ['chemistry__1911.02792__machine-learning-for-molecular-simulation.md', 'chemistry__2011.07200__deep-spatial-learning-with-molecular-vibrati.md']
- gold_facts: 综述: ML 势函数/采样等视角(观点文章); 振动增强: 物理合理扰动扩充分子 3D 坐标数据; 相对误差 16.34% → 6.71%; 决定系数 R² 0.16 → 0.75

### 模式 A

- 检索: ok=True real_engine=True engine=laya backend=laya_sdk 检索耗时 24.5s 保留文档 20 篇
- gold_hit: False {'1911.02792': False, '2011.07200': True}
- chat API: 总延迟 35.1s (回答 9.2s) · tokens {'input': 7408, 'output': 279, 'cache_read': 37376, 'cache_creation': 0} · cost $0.062703

```
The evidence is insufficient to answer this question. The retrieved chunks include a paper on "Deep Spatial Learning with Molecular Vibration" (chemistry__2011.07200), which reports the polyamide nanofiltration membrane results — relative error dropping from 16.34% to 6.71% and R² rising from 0.16 to 0.75 — but it does not describe or cite Noé et al.'s review "Machine learning for molecular simulation," so I cannot report how that review addresses data scarcity. No chunk in the retrieved evidence contains the Noé review at all.

Sources used: `自然科学与地球科学/chemistry__2011.07200__deep-spatial-learning-with-molecular-vibrati.md` (for the nanofiltration error/R² figures only). The remaining retrieved chunks (vector-index-tuning-guide, 2211.12700, 1706.03762, 2110.08918, 1909.07748, 2402.07064, 2410.10669, soul memory-conventions files, aw-industrial smoke test) are unrelated to the question.

Bottom line: only half the question is answerable from the evidence (the 6.71% / 0.75 figures); the Noé review comparison is not covered, so I will not supply it from prior knowledge.
```

### 模式 B

- 检索: ok=True real_engine=True engine=laya backend=laya_sdk 检索耗时 7.9s 保留文档 9 篇
- gold_hit: False {'1911.02792': True, '2011.07200': False}
- chat API: 总延迟 19.5s (回答 11.5s) · tokens {'input': 9878, 'output': 282, 'cache_read': 37312, 'cache_creation': 0} · cost $0.075096

```
The evidence is insufficient to answer this question.

**What the evidence does cover:** The retrieved chunks are parts 1–2 of Noé et al., *Machine learning for molecular simulation* (arXiv 1911.02792), covering ML for potential energy surfaces, free energy surfaces, coarse-graining, sampling/thermodynamics, and incorporating physics (invariances, equivariances, energy/probability conservation) into ML models. The only mention of data augmentation is in §3.2, where it is described as statistically inefficient and inaccurate relative to hard-wiring invariances into the model — a general methodological point with no quantitative results.

**What is missing:** The evidence contains no reference to a "deep-space learning + molecular vibration" data-augmentation method, no polyamide nanofiltration membrane experiments, and no relative-error or R² (coefficient of determination) figures. Nothing in the retrieved text compares the two approaches as the question presupposes, and no numeric improvement values appear anywhere.

Sources used: `自然科学与地球科学\chemistry__1911.02792__machine-learning-for-molecular-simulation (part 1 of 4).md` and `(part 2 of 4).md`. Per the output contract, I am not falling back on prior knowledge to supply the missing comparison or numbers — the evidence does not answer the question.
```

### 模式 C

- 检索: ok=True real_engine=True engine=laya backend=laya_sdk 检索耗时 35.0s 保留文档 12 篇
- gold_hit: False {'1911.02792': False, '2011.07200': False}
- chat API: 总延迟 41.4s (回答 6.1s) · tokens {'input': 19772, 'output': 238, 'cache_read': 37376, 'cache_creation': 0} · cost $0.123498

```
The retrieved evidence does not contain the answer. None of the four documents address Noé et al.'s review *Machine learning for molecular simulation*, deep-space learning with molecular vibration data augmentation, or polyamide nanofiltration membrane experiments. The available sources are an HNSW vector-index tuning guide, two portions of *Pride and Prejudice*, an industrial temperature-diagnostics smoke-test report, and the Transformer paper (*Attention Is All You Need*). Accordingly, the evidence is insufficient and I cannot supply the relative error or R² figures requested.

Sources consulted: `AI 基础设施/vector-index-tuning-guide (part 1 of 2).md`; `Novel-PridePrejudice/pride_and_prejudice (part 26 of 26).md`; `Novel-PridePrejudice/pride_and_prejudice (part 4 of 26).md`; `aw-industrial/【冒烟测试】工业诊断报告-522c33de-team_smoke-5秒窗口诊断.md`; `demo-qa-20260927/artificial-intelligence__1706.03762__attention-is-all-you-need.md`.
```

## 补充诊断 · C×Q2（同一 pack 复答 + 干净包对照）

C×Q2 主轮: 金标 CoRoT 论文位于证据包第 1 位(23,303 字符全文)，但模型声称包中无此文，只引用了包尾噪音文档(傲慢与偏见/冒烟报告/voyager/tracelens) → 弃答。

### 复答(cell_C_Q2_retry.json, 同一 60k pack 再问一次)
The evidence is insufficient to answer most of this question. The retrieved chunks include the CoRoT paper, but the file content is truncated mid-sentence ("Its closest approach to Jupiter was on") and none of the four retrieved chunks addresses the CoRoT question — they are respectively a Voyager 1 article, a RAG benchmark paper, an HNSW tuning guide, and unrelated industrial/文学 documents. The CoRoT material present covers photometry, observation strategy, and planets, but not the requested facts as a coherent answer set: the two scientific objectives are stated (exoplanet transit detection and asteroseismology, with observations starting 2 February 2007), yet the question's specific asks — the exoplanet program's science goals in detail, the mission extension, the light-curve count "as o

### 对照诊断(cell_C_Q2_diagnostic.json, 仅取该包前 24k 字符=金标单文档, 无噪音)
**CoRoT 系外行星计划的科学目标、时间线与关键事实（仅基于所给证据）**

The CoRoT satellite was designed with two distinct scientific objectives, both requiring continuous observations and ultra-high-precision relative stellar photometry: (1) the detection of extrasolar planets by the transit method, and (2) the study of stellar interiors by asteroseismology. Scientific observations began on **February 2nd, 2007**. The mission was initially scheduled for 3 years but was extended for 3 additional years, i.e. **until March 2013**. By summer 2010, a total of **129,326 light curves** had been collected. Super-Earth sized planets such as CoRoT-7b can be discovered only in the light curves of stars brighter than R ≈ 14; Neptune-size planets, by contrast, can be detected whatever the magnitude of the star.

**Sources used:**
- `自然科学与地球科学/astronomy__1105.1887__the-corot-exoplanet-program-status-results.md` — §1 Introduction (

**归因**: 干净包下同一 chat API 完全答对(目标/2007-02-02/延至2013-03/129,326/R≈14 全对) → C×Q2 失败非生成能力问题, 而是**模式 C 合并噪音拖垮回答阶段**(A 车道全局向量搜索混入无关库文档, 60k 包内 37k 为噪音; 长嘈杂包下模型 lost-in-the-middle)。

**另发现的平台缺陷(真实记录)**: 124_mode_c_parallel 合并规则 consensus+only_a+only_b[:max(0,12-0-20)] 在 A 独占 20 篇时将 only_b 整体清空 → C×Q3 中 B 车道找到的 4 部分金标(1911.02792)被整体丢弃, 合并 12 篇=A 列表前 12 篇(全噪音)。
