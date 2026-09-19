# Three-Way Retrieval QA — 10 Content-Grounded Questions

Generated 2026-09-17 15:42 UTC · corpus: 50 real multi-field papers · answering harness: **same omp engine for all tracks** (A/C share the identical unified answer prompt with a 4000-char evidence budget; B answers from the same engine with file tools and no budget)

| Track | Method | Avg latency | Gold-keyword answers |
|---|---|:---:|:---:|
| Track A — Platform KB retrieval | track_a_kb_system | 36 s | 9/10 |
| Track B — Bare agent direct search | track_b_bare_agent | 92 s | 10/10 |
| Track C — RAG reproduction (dense baseline) | track_c_dense_rag | 39 s | 9/10 |

## Track A — Platform KB retrieval

_MCP two_stage over the 5 category KBs → doc-level dedup → top-3 chunk excerpts (4000-char budget) → unified answer prompt_

| QID | Field | Latency | Gold keywords in answer |
|---|---|:---:|---|
| BQ01 | artificial-intelligence | 69.4 s | recurrence |
| BQ02 | quantum-physics | 10.8 s | noisy intermediate-scale |
| BQ03 | clinical-medicine | 10.3 s | multimedqa, 67.6 |
| BQ04 | genomics | 4.6 s | molecular function, biological process, cellular component |
| BQ05 | economics | 30.1 s | unified growth theory |
| BQ06 | climate-science | 52.5 s | — |
| BQ07 | nlp | 14.1 s | yiddish, 8b |
| BQ08 | materials | 46.0 s | cathode |
| BQ09 | robotics | 37.1 s | dynamic, multilayer perceptron |
| BQ10 | immunology | 84.3 s | immune evasion, chemotherapy |

### BQ01 — Attention Is All You Need

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**Sources:** artificial-intelligence__1706.03762__attention-is-

**Answer:** The excerpts do not describe the actual attention computation (e.g., query/key/value operations or softmax weighting), so the evidence is insufficient on that point. What they do support is that the Transformer is the first transduction model relying entirely on self-attention to compute representations of its input and output, dispensing with sequence-aligned RNNs and convolutions. Recurrence and convolution are replaced because this design attains superior quality on two machine translation tasks, and its complexity is comparable to a separable convolution — a self-attention layer plus a point-wise feed-forward layer — while also yielding more interpretable models as a side benefit.

### BQ02 — Quantum Computing in the NISQ era and beyond

**Q:** What defines NISQ technology and what is its central limitation?

**Sources:** quantum-physics__1801.00862__quantum-computing-in-

**Answer:** NISQ（Noisy Intermediate-Scale Quantum，含噪中等规模量子）指即将到来的量子技术新阶段，其中“中等规模”指未来几年可获得的量子计算机的量子比特数约为 50 到几百个（50 个量子比特是一个重要里程碑）。其核心局限在于这一阶段的设备不具容错能力——文中指出容错量子计算仍是相当遥远的梦想，而我们正是在此背景下进入 NISQ 时代，因此 NISQ 技术是“含噪”的、尚无纠错保障。

### BQ03 — Large Language Models Encode Clinical Knowledge

**Q:** What is MultiMedQA and how did Flan-PaLM perform on the MedQA benchmark?

**Sources:** clinical-medicine__2212.13138__large-language-mode

**Answer:** MultiMedQA is a benchmark for medical question answering spanning medical exam, medical research, and consumer medical questions. Evaluated on it, Flan-PaLM (the instruction-tuned variant of the 540B PaLM) achieved state-of-the-art accuracy on every MultiMedQA multiple-choice dataset (MedQA, MedMCQA, PubMedQA, MMLU clinical topics), including 67.6% on MedQA (USMLE), surpassing the prior state of the art by over 17%. Without self-consistency prompting it scored 60.3 on MedQA 4 options, rising to 67.6 with SC.

### BQ04 — Primer on the Gene Ontology

**Q:** Which three independent ontologies subdivide the Gene Ontology?

**Sources:** genomics__1602.01876__primer-on-the-gene-ontology.

**Answer:** The Gene Ontology is subdivided into three distinct, non-redundant ontologies representing different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC). These ontologies share a common space of identifiers and a well-specified syntax, and their terms are linked by relations to form a hierarchical vocabulary.

### BQ05 — Unified Growth Theory Contradicted by the Economic Growth in Europe

**Q:** Why does historical European economic growth contradict Unified Growth Theory?

**Sources:** economics__1512.08067__unified-growth-theory-contr

**Answer:** The excerpts only state the claim that Unified Growth Theory (Galor, 2005a, 2011) is contradicted by economic growth in Africa, Asia, the former USSR, the world, and Western Europe; they do not contain the actual reasons or data analysis explaining why European historical growth contradicts the theory. The only substantive text is an introductory assertion and a section heading ('Analysis of data for Western Europe'), with the analytical explanation cut off. Therefore, the evidence is insufficient to explain the contradiction.

### BQ06 — Precipitation extremes under climate change

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**Sources:** climate-science__1503.07557__precipitation-extreme

**Answer:** The evidence points to atmospheric water vapor — specifically near-surface humidity increasing with warming at roughly Clausius-Clapeyron scaling — as the physical factor governing the response, since precipitation extremes intensify under a warming climate and papers are cited relating changes in surface/column water vapor to Clausius-Clapeyron scaling and providing the physical basis for increases in precipitation extremes. The sensitivity of extremes to warming remains uncertain, however, and the excerpts do not name a single dominant controlling factor explicitly.

### BQ07 — MameLoshnLM: Yiddish Language Model and Evaluation Benchmark

**Q:** What is MameLoshnLM and what parameter scale does it have?

**Sources:** nlp__2608.05850__mameloshnlm-yiddish-language-mode

**Answer:** MAMELOSHNLM is an open-source language model for Yiddish, released together with two supporting resources: Oytser, a new Yiddish pretraining corpus, and Kashes, a benchmark for evaluating Yiddish LMs. It has 8B parameters. The evidence further notes that it outperforms strong baselines of similar scale and better captures language-defining lexical and morphological patterns than general-purpose multilingual models.

### BQ08 — Oxygen redox in battery cathodes: A brief overview

**Q:** How does oxygen redox contribute to the capacity of battery cathodes?

**Sources:** materials__2408.09942__oxygen-redox-in-battery-cat

**Answer:** {"answer": "Oxygen (anionic) redox participates in the redox activity of cathode materials for Li- and Na-ion batteries and thereby governs part of their useful capacity; the extent of this contribution depends on the crystal structure and the type of transition metal. It was first found to contribute significantly to overall battery capacity in Li-excess disordered spinel-type cathodes. Because anionic redox mechanisms cannot be probed directly, density functional

### BQ09 — MLP-SLAM: Multilayer Perceptron-Based Simultaneous Localization and Mapping

**Q:** What problem of visual SLAM in dynamic environments does MLP-SLAM address and how?

**Sources:** robotics__2410.10669__mlp-slam-multilayer-perceptr

**Answer:** MLP-SLAM addresses the degradation of visual SLAM systems in dynamic environments—scenes with numerous movable objects such as pedestrians, cars, and buses, common in outdoor settings—where most existing systems (e.g., ORB-SLAM2/3, LSD-SLAM) rely on a static-world assumption and lose accuracy. Its approach is an MLP (multilayer perceptron)-based real-time stereo SLAM system that performs dynamic-versus-static feature classification to mitigate that degradation. The excerpts confirm the problem and the MLP-based mechanism but do not detail the full classification pipeline.

### BQ10 — Strategies for tumor elimination and control under immune evasion and chemotherapy resistance

**Q:** What strategies for tumor control emerge under immune evasion and chemotherapy resistance?

**Sources:** immunology__2604.01385__strategies-for-tumor-elimi

**Answer:** The retrieved excerpts contain only the document and section titles (e.g., "Strategies for tumor elimination and control under immune evasion and chemotherapy resistance" with its Results and Methods subsections) and no substantive text. Therefore the evidence is insufficient to state any specific tumor-control strategies arising under immune evasion and chemotherapy resistance.

---

## Track B — Bare agent direct search

_Same omp engine WITH file tools, cwd=data/corpus_md/ (50 markdown papers, no index); it locates and reads passages itself_

| QID | Field | Latency | Gold keywords in answer |
|---|---|:---:|---|
| BQ01 | artificial-intelligence | 13.6 s | scaled dot-product, multi-head, recurrence |
| BQ02 | quantum-physics | 125.5 s | noisy intermediate-scale, error correction |
| BQ03 | clinical-medicine | 15.1 s | multimedqa, 67.6 |
| BQ04 | genomics | 27.4 s | molecular function, biological process, cellular component |
| BQ05 | economics | 67.2 s | unified growth theory |
| BQ06 | climate-science | 196.4 s | precipitation efficiency |
| BQ07 | nlp | 17.3 s | yiddish, 8b |
| BQ08 | materials | 180.5 s | oxygen redox |
| BQ09 | robotics | 105.4 s | dynamic, multilayer perceptron |
| BQ10 | immunology | 176.5 s | chemotherapy |

### BQ01 — Attention Is All You Need

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**Sources:** artificial-intelligence__1706.03762__attention-is-all-you-need.md

**Answer:** The Transformer computes attention with Scaled Dot-Product Attention: it maps a query and a set of key-value pairs to an output by taking dot products of the query with all keys, dividing each by sqrt(d_k), applying a softmax to obtain weights, and returning a weighted sum of the values, i.e. Attention(Q,K,V) = softmax(QK^T/sqrt(d_k))V; multi-head attention runs h such functions in parallel on learned linear projections. It replaces recurrence and convolution because a self-attention layer connects all positions with a constant O(1) number of sequentially executed operations (vs O(n) for recurrent layers) and has a maximum path length of O(1) rather than O(n) or O(log_k(n)), giving far more parallelization and making it easier to learn long-range dependencies. Since the model contains no recurrence or convolution, positional encodings (sine and cosine functions of different frequencies) are added to the input embeddings to inject sequence order.

### BQ02 — Quantum Computing in the NISQ era and beyond

**Q:** What defines NISQ technology and what is its central limitation?

**Sources:** quantum-physics__1801.00862__quantum-computing-in-the-nisq-era-and-beyond.md

**Answer:** NISQ stands for 'Noisy Intermediate-Scale Quantum,' a term coined by John Preskill for the near-term era of quantum technology: 'intermediate-scale' refers to devices of roughly 50 to a few hundred qubits (beyond what brute-force classical supercomputers can simulate), while 'noisy' emphasizes imperfect control over those qubits. Its central limitation is noise: imperfect gates limit the size (depth) of quantum circuits that can be executed reliably, so circuits with many gates are too noisy to yield useful results. Because quantum error correction carries too much overhead for this era, NISQ devices must rely on noise-resilient algorithm design, and near-term experiments are confined to of order 100 qubits with circuit depth under 100 (perhaps much less).

### BQ03 — Large Language Models Encode Clinical Knowledge

**Q:** What is MultiMedQA and how did Flan-PaLM perform on the MedQA benchmark?

**Sources:** clinical-medicine__2212.13138__large-language-models-encode-clinical-knowledge.md

**Answer:** MultiMedQA is a benchmark for medical question answering assembled by the Med-PaLM authors, combining six existing open datasets — MedQA, MedMCQA, PubMedQA, LiveQA, MedicationQA, and MMLU clinical topics — plus a newly introduced seventh dataset, HealthSearchQA, spanning medical exam, medical research, and consumer medical questions. On the MedQA (USMLE, 4-option) multiple-choice benchmark, the Flan-PaLM 540B model reached 67.6% accuracy using a combination of few-shot, chain-of-thought, and self-consistency prompting, surpassing the prior state of the art (PubMedGPT at 50.3%, DRAGON at 47.5%) by over 17 percentage points — a 20.1% improvement over DRAGON. The paper notes that despite this SOTA multiple-choice performance, human evaluation revealed key gaps in Flan-PaLM's long-form answers, motivating the instruction-prompt-tuned Med-PaLM.

### BQ04 — Primer on the Gene Ontology

**Q:** Which three independent ontologies subdivide the Gene Ontology?

**Sources:** genomics__1602.01876__primer-on-the-gene-ontology.md

**Answer:** The Gene Ontology is subdivided into three distinct, non-redundant ontologies representing different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC). They share a common space of identifiers and a well-specified syntax.

### BQ05 — Unified Growth Theory Contradicted by the Economic Growth in Europe

**Q:** Why does historical European economic growth contradict Unified Growth Theory?

**Sources:** economics__1512.08067__unified-growth-theory-contradicted-by-the-econom.md

**Answer:** Nielsen's analysis of Maddison's (2001, 2010) GDP data for Western and Eastern Europe finds that economic growth followed a steadily-increasing hyperbolic trajectory rather than the three regimes Galor's Unified Growth Theory posits. The data show no prolonged Malthusian stagnation and therefore no Malthusian trap, no dramatic transition from stagnation to growth, and no spectacular escape from a trap. Europe is the decisive test case because it was the center of the Industrial Revolution — which Galor calls the 'prime engine of economic growth' — yet the Industrial Revolution produced no visible boost or change in the growth trajectories; growth was simply hyperbolic from AD 1500 to about 1900, then diverted to a slower trajectory around 1900. Hence the theory is contradicted even in the region where it should fit best, and Nielsen concludes it must be revised or replaced.

### BQ06 — Precipitation extremes under climate change

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**Sources:** climate-science__1503.07557__precipitation-extremes-under-climate-change.md

**Answer:** The precipitation-extremes literature in this directory identifies the temperature-dependent moisture content of the atmosphere as the primary control: the thermodynamic contribution, in which the net condensation rate in an extreme event scales with saturation specific humidity along a moist adiabat, giving Clausius-Clapeyron scaling of roughly 6-7% K^-1 for typical surface temperatures. This contribution 'is the easiest to understand and always gives an intensification with warming,' and extratropical precipitation extremes in CMIP simulations increase at close to this thermodynamic rate. Dynamical (vertical velocity) and microphysical (precipitation efficiency) contributions matter in at least some situations, especially where convection is important or at temperatures below ~295 K, but they remain a smaller and less well-understood part of the response.

### BQ07 — MameLoshnLM: Yiddish Language Model and Evaluation Benchmark

**Q:** What is MameLoshnLM and what parameter scale does it have?

**Sources:** nlp__2608.05850__mameloshnlm-yiddish-language-model-and-evalu.md

**Answer:** MAMELOSHNLM is the first open-source large language model for Yiddish (named after the Yiddish term "mame-loshn", "mother tongue"), trained on a Yiddish corpus and paired with an evaluation benchmark. It was produced by continued pretraining of Llama-3.1-8B with a causal language modeling objective, giving it an 8B parameter scale; it is compared against other open-weight baselines of similar scale (Llama 3.1 8B, Qwen3 8B, BLOOMZ 7B, Gemma-2 9B, EuroLLM 9B) and reaches the best average score (62.6) across 14 Yiddish evaluations.

### BQ08 — Oxygen redox in battery cathodes: A brief overview

**Q:** How does oxygen redox contribute to the capacity of battery cathodes?

**Sources:** materials__2408.09942__oxygen-redox-in-battery-cathodes-a-brief-overvie.md, materials__2211.04977__design-of-battery-materials-via-defects-and.md

**Answer:** Oxygen (anionic) redox adds capacity beyond what transition-metal redox alone can supply: oxide anions O2- donate electrons during charging, effectively acting as reducing agents and compensating for the absence of oxidizable transition metals, which permits greater de-intercalation of Li or Na and thus higher measured capacity than cationic redox would allow. It is described as peroxo-type species formation, O2- <-> (O2)n-, or alternatively as electron holes on oxygen, and is enabled when orphaned/nonbonding O 2p states are lifted near the Fermi level — in Li-excess (Li-O-Li) or Na-excess layered oxides, or where oxygen is under-coordinated by transition metals (ilmenite-type NaTMO3). A concrete figure given is Na2-xRuO3, which reaches ~180 mAh/g, corresponding to ~1.4 electrons per formula unit, with the additional ~0.4-electron capacity attributed to reversible oxygen redox (and a voltage spike from 2.2 V to 3.4 V); Li2MnO3 capacity is likewise attributed to oxygen redox since Mn remains +4. The review cautions that this excess capacity is often detrimental: oxygen oxidation in oxides with insufficient TM-O covalency causes transition-metal diffusion and O2 gas release near particle surfaces, irreversibly decaying structure and capacity after the first cycle, and quantifying the cationic versus anionic share of capacity remains debated.

### BQ09 — MLP-SLAM: Multilayer Perceptron-Based Simultaneous Localization and Mapping

**Q:** What problem of visual SLAM in dynamic environments does MLP-SLAM address and how?

**Sources:** robotics__2410.10669__mlp-slam-multilayer-perceptron-based-simultaneou.md

**Answer:** MLP-SLAM addresses the precision degradation of visual SLAM systems in dynamic environments (outdoor scenes with pedestrians, cars, buses), where most SLAM systems rely on a static-world assumption and prior methods either use purely geometric rules or, like DynaSLAM, discard every feature inside the bounding box of a potentially dynamic object—causing information loss, manual parameter tuning, and poor generality. It builds on ORB-SLAM2 and adds a learned dynamic/static feature-point discriminator: YOLOv7 plus Deep Sort detect and track objects, a Depth Filter Module reclassifies background features inside the bounding box as static, and a multilayer perceptron classifies each remaining in-box point using complete geometric information (image intensity error, epipolar error, and re-projection error) rather than partial cues. Static features from outside the boxes, DFM-filtered points, and MLP-labelled static points are used for coarse-then-fine camera pose estimation by minimizing re-projection error, with no manual parameter configuration. The paper also contributes a public dataset of over 50,000 annotated feature points for direct evaluation, and reports the highest average precision on KITTI Odometry/KITTI360 and fastest speed among dynamic SLAM systems (1.48 average ATE, 62.81 ms latency).

### BQ10 — Strategies for tumor elimination and control under immune evasion and chemotherapy resistance

**Q:** What strategies for tumor control emerge under immune evasion and chemotherapy resistance?

**Sources:** immunology__2604.01385__strategies-for-tumor-elimination-and-control.md

**Answer:** The only relevant file, the immunology modeling paper, finds that immune dynamics alone are generally insufficient to eliminate tumors, so combination immuno-chemotherapy is required: chemotherapy reduces tumor burden and targets the sensitive/resistant subpopulations while immunotherapy enhances immune-mediated suppression, together expanding the tumor-free or low-population parameter region and delaying resistance. Effective therapy must be phenotype-guided by the dominant evasion mechanism: under immune checkpoint evasion, reducing immune exhaustion (μ) with checkpoint inhibitors plus moderate chemotherapy is best; under reduced antigen presentation, raising effector activation (ρ) and lowering μ via CAR-T, vaccines, or checkpoint inhibitors works best, while when the immune-sensitive phenotype dominates, increasing effector recruitment (σ) and decreasing effector death (δ) (adoptive T-cell transfer or cytotoxic therapy) is preferred. The authors also propose sequential strategies guided by tumor composition — e.g. debulking chemotherapy first then immunotherapy in T1-dominant or coexistence states, or immunotherapy after chemotherapy in T2-dominant tumors — and adaptive therapy that controls rather than eradicates the tumor to exploit competition and prevent resistance from becoming dominant; they note small parameter changes can trigger transitions between immune control and tumor escape, favoring patient-specific parameter identification.

---

## Track C — RAG reproduction (dense baseline)

_methods.dense over Corpus-Chunks800 (fixed 800-char chunks, top-10) → same 4000-char budget → same unified answer prompt_

| QID | Field | Latency | Gold keywords in answer |
|---|---|:---:|---|
| BQ01 | artificial-intelligence | 14.5 s | scaled dot-product, multi-head, recurrence |
| BQ02 | quantum-physics | 66.5 s | noisy intermediate-scale, error correction |
| BQ03 | clinical-medicine | 66.6 s | multimedqa, 67.6 |
| BQ04 | genomics | 4.3 s | molecular function, biological process, cellular component |
| BQ05 | economics | 46.8 s | unified growth theory |
| BQ06 | climate-science | 42.6 s | precipitation efficiency |
| BQ07 | nlp | 55.5 s | yiddish, 8b |
| BQ08 | materials | 23.1 s | cathode |
| BQ09 | robotics | 12.7 s | — |
| BQ10 | immunology | 56.9 s | immune evasion, chemotherapy |

### BQ01 — Attention Is All You Need

**Q:** How does the Transformer compute attention, and why does it replace recurrence and convolution?

**Answer:** The evidence does not describe the actual attention computation (e.g. queries, keys, values or scaled dot-product), so the mechanism itself is insufficient in the excerpts. It does state that the Transformer is the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention. It can be trained significantly faster than architectures based on recurrent or convolutional layers, achieving state of the art on WMT 2014 English-to-German and English-to-French, which is why recurrence and convolution are replaced.

### BQ02 — Quantum Computing in the NISQ era and beyond

**Q:** What defines NISQ technology and what is its central limitation?

**Answer:** NISQ stands for "Noisy Intermediate-Scale Quantum" — a term coined to describe the impending era in quantum technology, where "intermediate scale" refers to the size of quantum computers that will be available in the next few years. Its central limitation is that these machines are noisy and lack fault-tolerant quantum error correction: quantum error correction carries a significant overhead cost, since encoding protected quantum information in a highly entangled state requires many additional physical qubits, so reliable error-corrected quantum computers are not likely to be available very soon.

### BQ03 — Large Language Models Encode Clinical Knowledge

**Q:** What is MultiMedQA and how did Flan-PaLM perform on the MedQA benchmark?

**Answer:** MultiMedQA is a benchmark used to assess large language models in medicine, built from datasets including MedQA, MedMCQA, PubMedQA, and MMLU clinical topics, as well as question sets consisting of commonly searched health questions. On the MedQA (USMLE) dataset with 4 options, Flan-PaLM (540B) achieved 67.6% accuracy, exceeding the previous state of the art by over 17%.

### BQ04 — Primer on the Gene Ontology

**Q:** Which three independent ontologies subdivide the Gene Ontology?

**Answer:** The Gene Ontology is subdivided into three distinct, non-redundant ontologies representing different biological aspects: Molecular Function (MF), Biological Process (BP), and Cellular Component (CC). These share a common space of identifiers and a well-specified syntax.

### BQ05 — Unified Growth Theory Contradicted by the Economic Growth in Europe

**Q:** Why does historical European economic growth contradict Unified Growth Theory?

**Answer:** The evidence argues that historical European economic growth contradicts Unified Growth Theory because the data never show a transition from stagnation to growth: there was no stagnation, and no Malthusian trap to escape. Industrial Revolution, which should have had the strongest effect in Western and Eastern Europe, had no impact on changing economic growth trajectories. The expected signature of Galor's takeoff — a clear downward change in the trajectory of reciprocal growth values, consistent with hyperbolic rather than suddenly boosted growth — is missing from the European data, so Unified Growth Theory is said to rest on mythical features rather than the observed mechanism of growth.

### BQ06 — Precipitation extremes under climate change

**Q:** Which physical factor primarily controls the response of precipitation extremes to climate change?

**Answer:** The evidence indicates that the thermodynamic response is the dominant, well-understood control: if changes in dynamics and precipitation efficiency are negligible, precipitation extremes increase with warming because of increases in the saturation vapor pressure of water (the thermodynamic contribution). This thermodynamic contribution is described as robust and well understood, while the microphysical and dynamical contributions remain less certain, particularly where convection is important. Thus saturation vapor pressure (thermodynamics) primarily controls the response, modulated by dynamical and precipitation-efficiency effects.

### BQ07 — MameLoshnLM: Yiddish Language Model and Evaluation Benchmark

**Q:** What is MameLoshnLM and what parameter scale does it have?

**Answer:** MameLoshnLM (Mame-Loshn, "mother tongue") is the first open-source large language model for Yiddish, trained on the paper's Yiddish corpus and reported to outperform strong baselines of similar scale on Yiddish evaluation benchmarks. It was produced by continued pretraining of Llama-3.1-8B using a causal language modeling objective (bfloat16, 8-bit AdamW, LR 2e-5, cosine schedule with 2% warmup, weight decay 0.01, one epoch). Its parameter scale is therefore 8B, inherited from the Llama-3.1-8B base; it is released under a non-commercial license.

### BQ08 — Oxygen redox in battery cathodes: A brief overview

**Q:** How does oxygen redox contribute to the capacity of battery cathodes?

**Answer:** Oxygen (anionic) redox contributes to cathode capacity by supplying additional electron transfer beyond that of the transition metal cations: in Li-excess disordered spinel-type cathodes the high O redox contribution is attributed to orphaned oxygen states from oxygen ions with fewer than three coordinating transition metal elements, and similar behavior occurs in ilmenite-type oxides where oxygen is under-coordinated by both alkali and transition metal ions, with vacancies creating orphaned O states. In both cases the orphaned O 2p states lie closer to the Fermi level than fully hybridized O states and are therefore more labile for the redox reaction, so anionic redox increases the cathode capacity. The contribution varies with crystal structure and transition metal type, being more dominant in oxides containing 4d (fifth row) transition metals.

### BQ09 — MLP-SLAM: Multilayer Perceptron-Based Simultaneous Localization and Mapping

**Q:** What problem of visual SLAM in dynamic environments does MLP-SLAM address and how?

**Answer:** MLP-SLAM 针对的问题是：视觉 SLAM 在含大量可移动物体（行人、汽车、公交车等常见室外场景）的动态环境中性能下降，而现有人工数学方法普遍通用性差且存在信息损失。为此，作者提出基于多层感知机（MLP）的方法，利用完整几何信息来避免信息损失，并能在多种场景下适用，用于区分动态与静态特征点；据作者所述，这是首次将基于机器学习的方法引入 SLAM 领域的动静态特征点判别。此外，该工作还构建了一个包含 5 万余个特征点的公开数据集以填补评测空白。

### BQ10 — Strategies for tumor elimination and control under immune evasion and chemotherapy resistance

**Q:** What strategies for tumor control emerge under immune evasion and chemotherapy resistance?

**Answer:** {"answer": "The excerpts only partially address this: the paper frames strategies for tumor elimination and control under immune evasion and chemotherapy resistance, and reports that bifurcation diagrams for immune-resistant tumors (with immune checkpoint regulation and reduced antigen presentation) show which biological processes most strongly determine treatment success and identify effective therapeutic strategies that shift key parameter values. The killing probability θ1 is pivotal

---

## Notes

- Gold-keyword check is a coarse indicator: an answer can be correct
  without echoing the exact keyword string (e.g. paraphrase).
- Track A and C answered from their own retrieved evidence under the
  identical prompt and budget; Track B chose which files to read itself,
  which explains its higher per-question latency.
- Raw records (full evidence lists, raw model output): `results/threeway_qa.json`
