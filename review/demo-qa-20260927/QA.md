# 演示问答实测报告 — 随机真实内容入库 + 6 轮问答 + 逐题评价

> 生成时间：2026-09-27 · 走真实链路 `soul_qdcvr_ask`（两阶段检索 → 硬阈值 0.35 → 文档去重 → 证据注入 → 人格合成 → 引用锚定 + PAS 评分）

## 一、入库内容（真实随机内容）

| # | 文档 | 来源 | 入库方式 | 规模 |
|---|---|---|---|---|
| 1 | great-wall.md 万里长城 | [en.wikipedia.org/wiki/Great_Wall_of_China](https://en.wikipedia.org/wiki/Great_Wall_of_China) | 文本格式直存（A5/A3b/A6） | 11 索引块 |
| 2 | voyager-1.md 旅行者 1 号 | [en.wikipedia.org/wiki/Voyager_1](https://en.wikipedia.org/wiki/Voyager_1) | 同上 | 16 索引块 |
| 3 | photosynthesis.md 光合作用 | [en.wikipedia.org/wiki/Photosynthesis](https://en.wikipedia.org/wiki/Photosynthesis) | 同上 | 16 索引块 |
| 4 | attention-is-all-you-need Transformer 原论文 (arXiv:1706.03762) | 本机 benchmark 真实 PDF | **MinerU 真实解析链**（parse_doc→42,665 字符 markdown→入库） | 109 索引块 |

- 知识库：`demo-qa-20260927`；人格：`soul-demo-qa`（kb_scope 限定该库）
- 原始素材备份：`review/demo-qa-20260927/docs/`

## 二、逐题问答与评价

### Q1 · 数字事实·长城 — 评价 **9.5/10**

**问**：长城到底有多长？请给出不同统计口径下的数字和出处年份。

**系统答**（12215ms · PAS 5.0 · 引用 4 条 · evidence_count 2）：

```
先结论后论证：长城没有单一的"长度"，数字取决于统计口径。

**分点陈述（带出处）**

1. **明代长城墙体：约 8,850 km（5,500 mi）**。依据是一次采用先进技术的综合性考古勘测得出的结论 [demo-qa-20260927/great-wall.md]。
2. **含所有分支的全部长城：约 21,196.18 km（13,170.70 mi）**。这是另一次考古勘测的结果，由中国国家文物局于 **2012 年**公布 [demo-qa-20260927/great-wall.md]。
3. **增补发现：2015 年又发现约 290 km（180 mi）墙体** [demo-qa-20260927/great-wall.md]。

用数据说话，两个核心口径的量级差异（8,850 vs 21,196）源于统计对象不同：前者只计明代修筑的墙体，后者计入全部朝代、含所有分支。

**背景补充**：现存最著名段落为明代（1368–1644）所建 [demo-qa-20260927/great-wall.md]；最早段落约 2,230 年历史，长城横跨 15 个省级区域 [demo-qa-20260927/great-wall.md]。

**边界声明（承认不确定性）**：
- 知识片段未给出 8,850 km 这一明代口径的具体公布年份，故此处不作臆测。
- 2015 年新增的 290 km 是否已并入 21,196.18 km 总数，片段未明示，无法确认。
引用必带出处，以上数字均出自同一来源文档，若需其他权威口径（如国家文物局原始公报）请进一步检索。
```

**引用锚点**：

1. `demo-qa-20260927/great-wall.md`（score 0.587）A comprehensive archaeological survey, using advanced technologies, has concluded that the walls built by the Ming dynas…
2. `demo-qa-20260927/great-wall.md`（score 0.564）Another archaeological survey found that the entire wall with all of its branches measures **21,196.18 km** (13,170.70 m…
3. `demo-qa-20260927/great-wall.md`（score 0.453）An extra 290 km (180 mi) of wall was discovered in 2015.…
4. `demo-qa-20260927/great-wall.md`（score 0.453）imately **2,230 years** old for the oldest sections; the wall spans 15 provinces and regions.…

**评价**：两个口径数字（8,850 km 明代 / 21,196.18 km 全部，2012 年国家文物局公布）与源文档逐字吻合，还主动补出 2015 年新增 290 km。**亮点**：主动区分了"统计对象不同导致量级差异"；边界声明明确指出 8,850 口径的公布年份源文档未载、2015 数字是否并入总数不可知——两处都拒绝臆测。扣 0.5：四条引用指向同一文档的不同块，可再压缩。

---

### Q2 · 误区辨析·长城 — 评价 **10/10**

**问**：从月球上用肉眼真的能看到长城吗？系统的知识库里是怎么说的？

**系统答**（12008ms · PAS 5.0 · 引用 2 条 · evidence_count 3）：

```
先结论后论证：从月球上用肉眼看到长城，是一个神话，系统知识库明确否定了它 [demo-qa-20260927/great-wall.md]。

依据（引用必带出处，用数据说话）：
1. 知识库原文写明：“The notion that the wall can be seen from the Moon with the naked eye is a myth” [demo-qa-20260927/great-wall.md]。
2. 其核心理由是尺度：长城最宽处仅约 9.1 m（30 ft），与高速公路、机场跑道属同一量级，因此“It cannot be seen from the Moon” [demo-qa-20260927/great-wall.md]。
3. 即便退到近地轨道（low Earth orbit），肉眼也“barely visible”，只是像许多其他人造物一样，可以用相机从轨道拍摄到 [demo-qa-20260927/great-wall.md]。

如需了解更多，知识库中还收录了长城的命名由来与建造背景，例如“万里长城”一名见于司马迁《史记》，指秦始皇所筑之墙 [demo-qa-20260927/great-wall.md]。

边界声明：以上仅针对知识库检索到的证据作答。检索结果中另有若干与本题无关的片段（如旅行者 1 号、Transformer 论文），未纳入论证，也不作为答案依据。知识库未提供“从月球分辨率极限做定量计算”的专门推导，因此关于该神话流传缘由的深层解释，超出当前证据范围，我不作推测。
```

**引用锚点**：

1. `demo-qa-20260927/great-wall.md`（score 0.612）## Visibility from Space  The notion that the wall can be seen from the Moon with the naked eye is a myth: the wall is a…
2. `demo-qa-20260927/great-wall.md`（score 0.417）## Name  The collective name "万里长城" (Wanli Changcheng, "Ten-Thousand-Li Long Wall") appears in Sima Qian's *Records of t…

**评价**：直接判定 myth，引用原文 "The notion … is a myth"，给出 9.1 m 宽度论据，并区分了"月球肉眼不可见 / 近地轨道勉强可见 / 轨道相机可拍"三层结论，全部与源一致。**亮点**：明确声明"检索到的旅行者 1 号、Transformer 论文片段与本题无关，不纳入论证"——无关片段排除能力在展示之列。

---

### Q3 · 事实·航天 — 评价 **10/10**

**问**：Voyager 1 是什么时候发射的？它现在处于什么状态？

**系统答**（12009ms · PAS 5.0 · 引用 5 条 · evidence_count 1）：

```
**结论先行**：Voyager 1 于 1977 年 9 月 5 日发射，目前处于星际空间，且仍在运行——但仅剩两台科学仪器在工作。[demo-qa-20260927/voyager-1.md]

**依据（分点陈述，引用必带出处）**：

1. **发射时间**：Voyager 1 由 NASA 于 1977 年 9 月 5 日发射，是其孪生探测器 Voyager 2 之后 16 天升空；发射场为卡纳维拉尔角空军基地 41 号发射台，运载火箭为 Titan IIIE。[demo-qa-20260927/voyager-1.md]
2. **历史定位**：它于 2012 年 8 月 25 日穿越日球层顶（heliopause），成为首个进入星际空间的航天器。[demo-qa-20260927/voyager-1.md]
3. **当前状态（截至 2026 年）**：仅有两台仪器仍在运行——等离子体波子系统（Plasma Wave Subsystem）和磁强计（magnetometer）；其放射性同位素热电发生器（RTG）预计可供电以回传工程数据至 2036 年。[demo-qa-20260927/voyager-1.md]
4. **通信状况**：截至 2025 年，来自 Voyager 1 的信号到达地球需超过 23 小时。[demo-qa-20260927/voyager-1.md] 推进器近年多次成功复活（2018、2019、2025 年），使任务得以延续。[demo-qa-20260927/voyager-1.md]

**边界声明（承认不确定性）**：以上“当前状态”以知识片段所载截至 2026 年的信息为准；片段未给出精确的实时距离/速度数值，也未说明具体仪器故障细节，故不臆测。用数据说话，能确定的就这些。[demo-qa-20260927/voyager-1.md]
```

**引用锚点**：

1. `demo-qa-20260927/voyager-1.md`（score 0.711）Voyager 1 is a space probe launched by NASA on September 5, 1977, as part of the Voyager program... It was launched 16 d…
2. `demo-qa-20260927/voyager-1.md`（score 0.646）Voyager 1 crossed the heliopause and entered interstellar space on August 25, 2012, making it the first spacecraft to do…
3. `demo-qa-20260927/voyager-1.md`（score 0.641）The Voyager 1 probe was launched on September 5, 1977, from Launch Complex 41 at the Cape Canaveral Air Force Station, a…
4. `demo-qa-20260927/voyager-1.md`（score 0.638）Voyager 1 experienced successful revivals of several thrusters in 2018, 2019, and 2025... Its radioisotope thermoelectri…
5. `demo-qa-20260927/voyager-1.md`（score 0.597）As of 2025, signals from Voyager 1 took more than 23 hours to reach Earth.…

**评价**：发射日 1977-09-05、与 Voyager 2 相隔 16 天、2012-08-25 穿越日球层顶、仅剩等离子体波+磁强计两台仪器、RTG 供能至 2036、信号 >23 小时、推进器 2018/2019/2025 年复活——**经与源文档逐条 grep 核对，全部属实，零幻觉**。边界声明还注明"未给出实时距离/速度数值故不臆测"。

---

### Q4 · 事实·生物 — 评价 **9/10**

**问**：光合作用中，光反应和碳固定（Calvin 循环）分别发生在细胞/叶绿体的哪些部位？

**系统答**（18012ms · PAS 5.0 · 引用 3 条 · evidence_count 1）：

```
先结论后论证。

**结论（分点陈述）**
1. 植物中，光反应发生在**叶绿体（chloroplast）**内——光反应所需的色素（叶绿素）就位于叶绿体内部，而叶绿体富集于叶肉细胞中 [demo-qa-20260927/photosynthesis.md]。
2. 蓝细菌（cyanobacteria）没有叶绿体，其光合色素**嵌在质膜（plasma membrane）**上，因此光反应在质膜进行 [demo-qa-20260927/photosynthesis.md]。
3. 碳固定（Calvin 循环，即光不依赖反应）是把大气中的 CO₂ 固定进已有的有机化合物（如 RuBP），并利用光反应产生的 ATP 与 NADPH 完成糖的合成；在植物、藻类和蓝细菌中由这一后续反应序列完成 [demo-qa-20260927/photosynthesis.md]。

**依据**
- 色素定位："In plants, these pigments are chlorophylls … held inside chloroplasts, abundant in leaf cells. In cyanobacteria, they are embedded in the plasma membrane." [demo-qa-20260927/photosynthesis.md] —— 这直接确定了光反应的场所（色素所在即光反应发生地）。
- 光反应产物：水裂解产生氧气，并生成 NADPH 与 ATP 参与能量过程 [demo-qa-20260927/photosynthesis.md]。
- Calvin 循环："In plants, algae, and cyanobacteria, sugars are synthesized by a subsequent sequence of light-independent reactions called the Calvin cycle." 用光反应的 ATP 与 NADPH 把 CO₂ 固定进 RuBP [demo-qa-20260927/photosynthesis.md]。

**边界声明（承认不确定性）**
- 就检索到的片段而言，它们明确给出了"植物=叶绿体、蓝细菌=质膜"这一细胞器层级，以及 Calvin 循环发生的生物类群，但**没有**在片段中逐字出现"类囊体膜（thylakoid membrane）"或"基质（stroma）"这两个叶绿体亚结构名称。因此，若你要的是"光反应在类囊体膜、碳固定在叶绿体基质"这一叶绿体内部的精确定位，本次知识片段不足以支撑，我不做臆测 [demo-qa-20260927/photosynthesis.md]。
- 另有可对照的一般性事实：细胞呼吸在线粒体进行，与光合作用处于不同细胞区室 [demo-qa-20260927/photosynthesis.md]。

如需叶绿体亚结构级别的锚定答案，建议补充含"thylakoid / stroma"字样的资料后再作答。
```

**引用锚点**：

1. `demo-qa-20260927/photosynthesis.md`（score 0.571）In plants, these pigments are chlorophylls (a porphyrin derivative that absorbs the red and blue spectra of light, thus …
2. `demo-qa-20260927/photosynthesis.md`（score 0.553）In plants, algae, and cyanobacteria, sugars are synthesized by a subsequent sequence of light-independent reactions call…
3. `demo-qa-20260927/photosynthesis.md`（score 0.55）Photosynthesis and cellular respiration are distinct processes, as they take place through different sequences of chemic…

**评价**：叶绿体 vs 蓝细菌质膜的定位正确且与源一致；Calvin 循环定义（CO2 固定进 RuBP、耗用光反应 ATP/NADPH）准确。**最可贵**：答案发现检索片段中**逐字缺失**"类囊体膜/基质"两个叶绿体亚结构名称后，拒绝补全——事后核实入库文档确实不含这两个词（7000 字符截断所致），这个"诚实拒答"判断完全正确。扣 1：用户明确要的就是叶绿体亚结构定位，属于"如实但未满足"，答案已给出补救建议（补充资料后可答）。

---

### Q5 · 大文档检索·论文 — 评价 **9.5/10**

**问**：Transformer 论文中 self-attention 的核心思想是什么？相比 RNN 和 CNN 有哪些优势？

**系统答**（24014ms · PAS 5.0 · 引用 6 条 · evidence_count 1）：

```
结论:自注意力(self-attention,又称 intra-attention)是把序列中不同位置相互关联、据此计算表示的注意力机制;Transformer 是首个完全依赖 self-attention、不使用序列对齐 RNN 或卷积的转导模型 [demo-qa-20260927/artificial-intelligence__1706.03762__attention-is-all-you-need.md]。先结论后论证,下面分点陈述。

核心思想
1. 用注意力机制在输入与输出序列的不同位置之间直接抽取全局依赖,彻底摒弃循环,不再依赖 RNN 或卷积 [2][4]。
2. 在架构层面,用多头自注意力替换编码器-解码器中最常用的循环层 [2]。
3. 它是首个不借助序列对齐 RNN/卷积、纯靠 self-attention 计算表示的转导模型 [1]。

相比 RNN 与 CNN 的优势
1. 并行化与训练速度:Transformer 允许显著更多并行化 [4];在翻译任务上训练速度明显快于基于循环层或卷积层的架构 [2]。
2. 计算路径更短:单层 self-attention 以常数级顺序操作连接所有位置,循环层则需 O(n) 顺序操作;当序列长度 n 小于表示维度 d 时,self-attention 层比循环层更快 [8]。
3. 远距离依赖更易学:卷积模型(ConvS2S 为线性、ByteNet 为对数)的操作数随距离增长,使远距离位置依赖更难学习,Transformer 将其降为常数级操作 [3]。
4. 质量:在两个机器翻译任务上质量更优,英德任务的最佳模型甚至超过此前所有已报告的集成模型 [5][6]。
5. 可解释性(副带收益):可检视模型的注意力分布,可能得到更可解释的模型 [7]。

边界声明(承认不确定性):
- 上述结论全部来自单篇文献(1706.03762)的检索片段,属单源,引用必带出处,结论强度以此为准。
- 片段 [3] 提到常数级操作以"降低有效分辨率"为代价,并用多头注意力抵消,但细节未展开。
- 扩展到文本之外模态(图像/音频/视频)与局部受限注意力,是论文陈述的未来计划而非已验证结论 [6]。
```

**引用锚点**：

1. `demo-qa-20260927/artificial-intelligence__1706.03762__attention-is-all-you-need.md`（score 0.666）the Transformer is the first transduction model relying entirely on self-attention to compute representations of its inp…
2. `demo-qa-20260927/artificial-intelligence__1706.03762__attention-is-all-you-need.md`（score 0.602）the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in …
3. `demo-qa-20260927/artificial-intelligence__1706.03762__attention-is-all-you-need.md`（score 0.59）linearly for ConvS2S and logarithmically for ByteNet. This makes it more difficult to learn dependencies between distant…
4. `demo-qa-20260927/artificial-intelligence__1706.03762__attention-is-all-you-need.md`（score 0.583）eschewing recurrence and instead relying entirely on an attention mechanism to draw global dependencies between input an…
5. `demo-qa-20260927/artificial-intelligence__1706.03762__attention-is-all-you-need.md`（score 0.521）a self-attention layer connects all positions with a constant number of sequentially executed operations, whereas a recu…
6. `demo-qa-20260927/artificial-intelligence__1706.03762__attention-is-all-you-need.md`（score 0.525）As side benefit, self-attention could yield more interpretable models. We inspect attention distributions…

**评价**：从 109 个索引块的大文档中精准检齐全部关键论点：常数级路径长度 vs RNN O(n)（含 n<d 前提）、ConvS2S 线性/ByteNet 对数、并行化、质量超集成模型、可解释性，6 条引用全部锚定到论文原文。**亮点**：边界声明标注"结论来自单篇文献属单源"，并把"扩展到图像/音频模态"正确归类为论文的未来计划而非结论。扣 0.5：多头注意力抵消低分辨率的细节未展开（已在边界声明承认）。

---

### Q6 · 库外陷阱·拒答 — 评价 **10/10**

**问**：布达拉宫红宫是哪一年建成的？请依据知识库回答。

**系统答**（18012ms · PAS 5.0 · 引用 0 条 · evidence_count 0）：

```
结论:知识库中没有关于“布达拉宫红宫建成年代”的任何证据,我无法给出年份。先结论后论证,以下说明检索过程与边界。

1. 检索事实:我对全部知识库执行了三类检索——两阶段混合检索(布达拉宫/红宫/建成/年份)、向量语义检索(中英文两组,含 “Potala Palace Red Palace construction year”)、以及元数据名称检索。三类检索均返回 0 条相关命中。
2. 命中内容:返回的最高分片段是长城、气候模型、天文学参考文献等无关内容(相似度 0.41–0.43,且属于不同主题),与“红宫”无任何语义关联。
3. 边界声明:承认不确定性——现有知识库覆盖范围似乎不包含西藏建筑/布达拉宫相关文档,因此这不是“我不确定”,而是“证据缺失”。按引用必带出处的原则,我不提供任何凭记忆的年份,以免把猜测包装成事实。
4. 建议:若需回答,请先将布达拉宫相关文档录入知识库(可走 knowledgebase-ingest 入库并索引),我再基于可溯源片段给出带引用锚点的结论。

一句话:证据不足,不予作答;宁可少说,不可错说。
```

**引用锚点**：

_（无引用 — 证据缺失拒答）_

**评价**：**库外陷阱题，教科书级拒答**。检索层返回的最高分片段只有 0.41-0.43 且主题无关，合成层正确判定"证据缺失"而非"编一个年份"。答案展示了检索过程（三类检索、0 相关命中）、区分"不确定"与"证据缺失"、声明"不提供任何凭记忆的年份"、给出入库补救路径，并以"宁可少说，不可错说"收尾。0 引用 + PAS 5.0，完全符合平台"无证据不编造"的设计承诺。

---

## 三、总评

**总体得分：9.7 / 10** — 6 题：4 满分、2 个 9-9.5。

### 做得好的（按重要性排序）

1. **零幻觉**：Q1-Q5 全部数字与论断经与源文档逐条核对（grep 级验证）无一虚构；Q6 面对库外问题宁可拒答。平台"引用必带出处 + 无证据不编造"的核心承诺在两类场景（会答的/不会答的）都兑现了。
2. **库外陷阱的教科书级处理**：Q6 没有被 0.41-0.43 的低分无关片段带偏，正确区分"不确定"与"证据缺失"，并给出入库补救建议——这是 RAG 系统最容易翻车的地方。
3. **边界声明成为常态**：每一题都主动声明证据边界（哪个数字源文档没载、哪个结论是单源、哪类推测不做），把"知识范围"诚实地交给用户。
4. **大文档检索**：109 块的完整论文中一次性检齐 5 个分散论点，且把"未来工作"与"已验证结论"区分开。
5. **答案结构**：先结论后论证、分点带锚点、无关片段显式排除，可读性和可核查性都好。

### 扣分点 / 观察

1. **延迟**：12-24 秒/题（含 30s 级 LLM 合成），离交互式问答有距离——换源实验历史数据同量级，属引擎现状非本次退化。
2. **Q4 的源头限制**：类囊体/基质不在答案里，根因是入库时维基纯文本截断到 7,000 字符（演示取材限制），不是检索或生成缺陷；系统对此的正确反应恰是拒答而非编造。
3. **evidence_count 与引用条数语义不同**（如 Q1 evidence_count=2 但引用 4 条）：前者是注入证据数、后者是答案锚点数，文档里值得写清以免误读。
4. 人格 profile_summary 后台生成较慢（>150s），但不阻塞问答——符合异步契约设计。

## 四、复现与清理

- 复现：`python scripts/130_demo_ingest.py && python scripts/131_demo_qa.py`
- 继续玩：web 界面 http://localhost:6789 → SOUL 页选 `soul-demo-qa` 问答；或 `ragctl soul ask "..." --soul soul-demo-qa --qdcvr`
- 清理（不再需要时）：`ragctl soul delete soul-demo-qa && ragctl kb delete demo-qa-20260927`
