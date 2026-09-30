# 优化版逐级检索(opt_B) vs 旧 mode B — 同题真机对比

- Run: `run-014424` · 生成: 2026-09-27 17:44 UTC
- 变化: ①L4 并行读取(窗口8) ②内容驱动保留(retain_docs 相对截断 best-0.05+overlap 契合+top3 地板) ③分数降序打包(旧=路径字典序) ④全链路 trace.jsonl
- 判卷契约不变: Laya 逐段 fail-closed, yes 全收(段级)

## Q1

- 检索: 旧 28.9s → 新 21.78s (L4 读 1.47s, L5 判 15.59s, L5b peek 1.77+1.57s) · 旧题总 38.4s → 新题总 33.6s
- 层次: 列表 131 → 读 35 → 判 241 段 → yes 全收 241 段 → 保留 35 篇 → 包 16 块
- gold_in_pack: {'2503.21676': True} (旧 gold_hit: True)
- 包内文档 16 篇: 计算机与人工智能\artificial-intelligence__2303.14061__learni; 计算机与人工智能\artificial-intelligence__2510.13343__aoad-m; 计算机与人工智能\large-language-models__2402.11690__vision-f; 计算机与人工智能\large-language-models__2402.11690__vision-f; 计算机与人工智能\large-language-models__2402.11690__vision-f; 计算机与人工智能\large-language-models__2402.11690__vision-f; 计算机与人工智能\large-language-models__2402.12317__evor-evo; 计算机与人工智能\large-language-models__2402.12317__evor-evo; 计算机与人工智能\nlp__1810.04805__bert-pre-training-of-deep-; 计算机与人工智能\nlp__1810.04805__bert-pre-training-of-deep-; 计算机与人工智能\nlp__2503.21676__how-do-language-models-lea; 计算机与人工智能\nlp__2503.21676__how-do-language-models-lea; 计算机与人工智能\nlp__2608.05850__mameloshnlm-yiddish-langua; 计算机与人工智能\nlp__2608.05850__mameloshnlm-yiddish-langua; 计算机与人工智能\social-networks__1001.3181__weak-ties-subtl; 计算机与人工智能\speech__2509.05359__an-empirical-analysis-o

### 优化版回答(chat API 原样输出)

```
The evidence is insufficient to answer this question.

The retrieved chunks do not contain the relevant content. The paper that matches the question's topic — `nlp__2503.21676__how-do-language-models-learn-facts-dynamics.md` — is only present as parts 2 and 4 of 4, which contain the discussion/limitations section and figure captions, not the staged learning dynamics, plateau mechanism, or fine-tuning injection results. The other retrieved documents (EvoR code generation, BERT, VISION-FLAN, weak ties, MARL, Yiddish NLP, discrete speech units) are unrelated.

Sources actually used:
- `计算机与人工智能\nlp__2503.21676__how-do-language-models-learn-facts-dynamics.md` (part 2 of 4, part 4 of 4) — checked, does not contain the answer.
- Remaining evidence chunks — checked, topically unrelated.

No prior knowledge is used; I cannot answer from the evidence provided.
```

### 旧版回答(对照)

```
The evidence provided consists solely of the paper "Learning Reward Machines in Cooperative Multi-Agent Tasks" (arXiv 2303.14061), which concerns multi-agent reinforcement learning, reward machines, ILASP-based induction, and tasks such as THREEBUTTONS and RENDEZVOUS. It contains no material on language models, factual knowledge acquisition, learning dynamics or stages, performance plateaus, data distribution imbalance, knowledge injection via fine-tuning, or hallucinations. Therefore the evidence is insufficient to answer this question, and I stop here rather than draw on prior knowledge.

Sources used: none — the retrieved evidence (计算机与人工智能\artificial-intelligence__2303.14061__learning-reward-machines-in-cooperative-mult, parts 1–3) does not address the question.
```

## Q2

- 检索: 旧 7.8s → 新 11.07s (L4 读 0.6s, L5 判 4.16s, L5b peek 1.73+3.25s) · 旧题总 16.4s → 新题总 22.6s
- 层次: 列表 75 → 读 15 → 判 149 段 → yes 全收 149 段 → 保留 19 篇 → 包 15 块
- gold_in_pack: {'1105.1887': True} (旧 gold_hit: True)
- 包内文档 14 篇: 自然科学与地球科学\astronomy__1105.1887__the-corot-exoplanet-; 自然科学与地球科学\astronomy__1207.3189__the-dark-energy-surv; 自然科学与地球科学\astronomy__1207.3189__the-dark-energy-surv; 自然科学与地球科学\astronomy__2304.12442__enabling-exoplanet-; 自然科学与地球科学\chemistry__1911.02792__machine-learning-fo; 自然科学与地球科学\chemistry__1911.02792__machine-learning-fo; 自然科学与地球科学\climate-science__1503.07557__precipitation; 自然科学与地球科学\climate-science__2409.09639__gpc-m-global-; 自然科学与地球科学\oceanography__physics-0703220__scientific-; 自然科学与地球科学\quantum-physics__1801.00862__quantum-compu; 自然科学与地球科学\quantum-physics__1801.00862__quantum-compu; 自然科学与地球科学\quantum-physics__2303.00445__benchmarking-; 自然科学与地球科学\quantum-physics__2311.00487__echo-evolutio; 自然科学与地球科学\quantum-physics__2311.00487__echo-evolutio

### 优化版回答(chat API 原样输出)

```
The evidence does not answer the question. The CoRoT document provided (`astronomy__1105.1887__the-corot-exoplanet-program-status-results.md`) states only that in summer 2010 a total of 129,326 light curves were collected, and that super-Earths such as CoRoT-7b can be discovered only in light curves of stars brighter than R ≈ 14. It does not state the program's scientific goals, when science observations began, how far the mission was extended, or an explanation of why super-Earths are limited to brighter stars.

Source used: `自然科学与地球科学\astronomy__1105.1887__the-corot-exoplanet-program-status-results.md` (only partially relevant).

The remaining retrieved evidence (DES data processing, NISQ quantum computing, quantum error mitigation, molecular simulation ML, precipitation extremes, GPC/m, exoplanet demographics) addresses unrelated topics and is insufficient for this question.
```

### 旧版回答(对照)

```
The evidence answers all four parts.

**Answer**

CoRoT had two distinct scientific objectives, both requiring continuous observations and ultra-high-precision relative stellar photometry: detecting extrasolar planets by the transit method, and studying stellar interiors by asteroseismology. Scientific observations began on February 2nd, 2007; the mission was initially scheduled for three years but was extended for three more, i.e. until March 2013. By summer 2010, a total of 129,326 light curves had been collected. Super-Earth–size planets such as CoRoT-7b can only be discovered in the light curves of stars brighter than R ≈ 14, whereas Neptune-size planets are detectable at any stellar magnitude — the paper states this directly in the transit-signal-versus-magnitude analysis, without giving a deeper physical explanation.

**Sources used**
- `自然科学与地球科学\astronomy__1105.1887__the-corot-exoplanet-program-status-results.md` — §1 Introduction (objectives, start date, extension), §3 Detection capacity (129,326 light curves; magnitude limit for super-Earths), Figure 3 caption.
```

## Q3

- 检索: 旧 7.9s → 新 15.73s (L4 读 1.5s, L5 判 8.77s, L5b peek 1.48+2.66s) · 旧题总 19.5s → 新题总 30.4s
- 层次: 列表 75 → 读 35 → 判 297 段 → yes 全收 297 段 → 保留 30 篇 → 包 15 块
- gold_in_pack: {'1911.02792': True, '2011.07200': True} (旧 gold_hit: False)
- 包内文档 15 篇: 自然科学与地球科学\astronomy__1207.3189__the-dark-energy-surv; 自然科学与地球科学\chemistry__1911.02792__machine-learning-fo; 自然科学与地球科学\chemistry__1911.02792__machine-learning-fo; 自然科学与地球科学\chemistry__2011.07200__deep-spatial-learni; 自然科学与地球科学\mathematics__1810.09292__optimal-distribut; 自然科学与地球科学\mathematics__1810.09292__optimal-distribut; 自然科学与地球科学\mathematics__1810.09292__optimal-distribut; 自然科学与地球科学\mathematics__1810.09292__optimal-distribut; 自然科学与地球科学\mathematics__1810.09292__optimal-distribut; 自然科学与地球科学\quantum-physics__2201.00752__quantum-error; 自然科学与地球科学\quantum-physics__2303.00445__benchmarking-; 自然科学与地球科学\quantum-physics__2303.00445__benchmarking-; 自然科学与地球科学\quantum-physics__2311.00487__echo-evolutio; 自然科学与地球科学\quantum-physics__2311.00487__echo-evolutio; 自然科学与地球科学\quantum-physics__2311.00487__echo-evolutio

### 优化版回答(chat API 原样输出)

```
The retrieved evidence is insufficient to answer this question.

**What the evidence does contain:** Two chunks from `chemistry__1911.02792__machine-learning-for-molecular-simulation` (parts 2 and 3 of 4) cover unrelated sections — energy-matching/density-estimation losses (Eqs. 17–18), incorporating physics into ML, and Boltzmann Generators/VAMPnet (Figure 6). One chunk from `chemistry__2011.07200__deep-spatial-learning-with-molecular-vibrati` states that the proposed deep spatial learning with molecular augmentation outperforms RF, SVR, and GBR, and that "molecular vibration as a physically interpretable method provides a significant performance boost," but it gives **no numeric values** for relative error or coefficient of determination.

**What is missing:** No evidence describes how the Noé et al. review addresses data scarcity, and no evidence reports the 聚酰胺纳滤膜 (polyamide nanofiltration membrane) relative-error / R² improvements as specific numbers. The remaining chunks (Cahn-Hilliard control, quantum error mitigation, DES survey) are topically unrelated.

Per the output contract, I am reporting insufficient evidence rather than answering from prior knowledge.

**Sources consulted:**
- `自然科学与地球科学\chemistry__1911.02792__machine-learning-for-molecular-simulation (part 2 of 4).md`
- `自然科学与地球科学\chemistry__1911.02792__machine-learning-for-molecular-simulation (part 3 of 4).md`
- `自然科学与地球科学\chemistry__2011.07200__deep-spatial-learning-with-molecular-vibrati.md`
```

### 旧版回答(对照)

```
The evidence is insufficient to answer this question.

**What the evidence does cover:** The retrieved chunks are parts 1–2 of Noé et al., *Machine learning for molecular simulation* (arXiv 1911.02792), covering ML for potential energy surfaces, free energy surfaces, coarse-graining, sampling/thermodynamics, and incorporating physics (invariances, equivariances, energy/probability conservation) into ML models. The only mention of data augmentation is in §3.2, where it is described as statistically inefficient and inaccurate relative to hard-wiring invariances into the model — a general methodological point with no quantitative results.

**What is missing:** The evidence contains no reference to a "deep-space learning + molecular vibration" data-augmentation method, no polyamide nanofiltration membrane experiments, and no relative-error or R² (coefficient of determination) figures. Nothing in the retrieved text compares the two approaches as the question presupposes, and no numeric improvement values appear anywhere.

Sources used: `自然科学与地球科学\chemistry__1911.02792__machine-learning-for-molecular-simulation (part 1 of 4).md` and `(part 2 of 4).md`. Per the output contract, I am not f
```
