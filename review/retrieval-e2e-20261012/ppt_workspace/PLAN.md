# PPT制作规划文件

## 一、基本信息

| 字段 | 值 |
|------|-----|
| PPT标题 | 三种检索模式端到端实测：30 个真实检索臂，A/C 车道全绿，B 车道暴露 1 个系统性盲区 |
| 副标题 | RAG Knowledge 平台 · 三通道 × 三模式 × 同题集 Benchmark（2026-10-12） |
| 总页数 | 3页（其中2页配图，1页text-only+原生数据图） |
| 制作引擎 | huashu-slides + gpt-image-2 |
| 路径 | Path A（可编辑HTML）· slide尺寸 16:9（960pt×540pt, LAYOUT_WIDE） |
| 风格 | Study Style #20 — 学术研究双模系统（暖学术 + 锐学术） |
| 语言 | 中文为主，保留关键英文术语（InstructDS / gold / baseline / Laya） |
| 受众 | 论文评审 + 技术评审 + 项目组（学术/工程混合） |
| 研究笔记 | ppt_workspace/references/（下游读 _index.md 定位；数据源 ref-experiment-data.md，背景 ref-context.md） |

## 二、风格参数速查

### 暖学术模式（Warm Academic）— 第1、3 页
- **页面底色**: #FAF9F6（暖纸白）
- **主色**: #1B2A4A（深蓝黑 — 标题、图表主色）
- **强调色**: #C8963E（暖琥珀金 — 关键数字、装饰线）
- **正文色**: #1E1D1A（暖近黑）· **辅助色**: #6B6760（暖中灰）
- **卡片底色**: #F2F0EB（暖浅灰）、#FEF9F0（暖象牙白重点卡片 + #C8963E 左边框）
- **分割线色**: #E5E0D8
- **签名元素**: 顶部2pt solid #1B2A4A 全宽细线 + 底部1pt solid #E5E0D8 细线 + 右下角 #C8963E Georgia Bold 10pt 页码
- **标题字体**: 思源宋体/宋体 Bold 22-30pt #1B2A4A · **正文字体**: 微软雅黑 Regular 10-12pt #1E1D1A
- **英文/数字**: Georgia Bold（标题/数字）、Georgia Regular（正文）
- **暖学术生图关键词**: "clean academic schematic, warm off-white #FAF9F6 background, navy #1B2A4A + amber #C8963E accents, flat vector illustration with subtle textures, no photographic elements, no gradients, no text"

### 锐学术模式（Crisp Academic）— 第2 页
- **页面底色**: #FFFFFF（纯白）
- **主色**: #000066（海军蓝 — 正文、图表轴线）· **强调色**: #A50021（深绯红 — 标题、关键数据）
- **卡片底色**: #F0F4F8（浅蓝灰）、#FFF0F0（浅绯红重点卡片 + #A50021 左边框）
- **签名元素**: 顶部标题栏 bg #A50021 h=36pt 白字 + 底部信息栏 bg #000066 h=24pt 白字
- **章节标签**: pill 形状 bg #000066 或 #A50021 白字 border-radius 3pt
- **标题字体**: 微软雅黑 Bold 24pt #A50021 · **正文字体**: 微软雅黑 Bold/Regular 13-14pt #333333
- **英文/数字**: Times New Roman Bold / DIN Bold（数字）
- **锐学术生图关键词**: "publication-quality scientific figure, clean white background, navy #000066 + crimson #A50021, crisp vector-quality lines, flat 2D, color-blind friendly, no rounded corners, no shadows, no gradients, no text"

### 图表扩展色板（两种模式共用）
- #3A5A80 中蓝（第3数据系列）· #D4A853 中琥珀（第4数据系列）· #8FA3B5 灰蓝（背景/辅助）

## 三、逐页规划

### 第1页：封面 + 实验设计总览（暖学术）
- **标题**: 三种检索模式端到端实测——A/C 车道全绿，B 车道暴露 1 个系统性盲区
- **密度**: 中等（标题1句 + 3条设计 + 4个大数字）
- **论证逻辑**: 建立第一印象：这是一次"全部走官方 harness 对外 API"的真实端到端评测；先给出总量级（30 臂、三通道）再收进细节。
- **视觉主角**: 右侧 hero 概念图（三车道汇入知识库）+ 左下 4 个关键数字
- **布局**: 非对称双栏（左 58% / 右 42%）。左栏：顶部小 pill「Benchmark 实测报告」→ 26pt 宋体断言标题（2行内）→ 琥珀短 rule 60pt → 3 条实验设计（每条 10pt：问题集=3题含1域外拒答题 cm3；三通道=harness 流式 SSE / exp --chatmodes 非流式门禁 / exp --retmodes 纯检索；门禁口径=拒答优先修正版）→ 底部 4 个数字横排（30 真实检索臂｜8/9 + 8/9 + 12/12 门禁｜13–54× 提速｜$0.18–0.30/题）。右栏：hero 占位图（右下签名细线），图下 8pt 图注一行。顶部 2pt 主色线 + 右下角页码。密度：中等。
- **内容要点**:
  - 要点1：实验定位——三通道全部经官方对外 API（POST /api/claude/chat, engine=claude, kbEnhanced=true），与外部调用方完全同构；工具门禁/MCP 挂载/Laya 判卷均为服务端真实行为 [来源：_user_materials.md §1]
  - 要点2：问题集 3 题——cm1=InstructDS 对话摘要合成（金标 arXiv:2310.10981）；cm2=EHR 中风预测（金标 arXiv:1904.11280）；cm3=Herbert-Moulton collider（域外题，应如实拒答）[来源：_user_materials.md §1]
  - 要点3：门禁口径=拒答优先修正版（原 marker 门被拒答复述问题关键词欺骗，已修）——数字：通道1 8/9、通道2 8/9、通道3 12/12 [来源：_user_materials.md §3-5]
  - 要点4：关键数字——30 个真实检索臂；历史提速 13–54×（B 342/234s→25.0/10.2s，C 1152/1818s→37.3/33.7s）；成本 $0.182–0.300/题 [来源：§5-6]
- **图片决策**: Q1✓ Q2✓ Q3✓ Q4✓ → 1张 hero-cover（概念图传达"三车道检索架构"，文字给不出结构感）
- **配图类型**: hero-cover
- **内容锚点**: 三个并行的检索通道（vector lane / librarian lane / hybrid lane）汇入一个知识库建筑，车道上有数据点在流动；其中一条车道末端另有"裁决/判卷"节点符号——传达"多车道检索 + 判卷引擎"的核心架构
- **配图Prompt**: "Three parallel retrieval lanes as clean flat vector paths, each carrying small data-dot streams, converging into a stylized classical library building; one lane has a small gavel/judgement node glyph at its end; abstract academic schematic, warm off-white #FAF9F6 background, navy #1B2A4A + amber gold #C8963E accents, flat vector illustration with subtle paper texture, no text, no gradients, 16:9 with generous margins"

### 第2页：同题对照数据（锐学术）——核心页
- **标题**: 同题对照：三模式全部真实命中金标；baseline 只会"返回"，不会判卷与拒答
- **密度**: 深度（表格 + 双图 + 底部三条）
- **论证逻辑**: 用同题同金标数据证明：(a) 三模式在活库上全部命中金标（含脚本臂 6/6 + baseline 6/6）；(b) baseline 虽然 rank-1 命中但只是"静态语料排名"，没有判卷/读全文/拒答能力——差异化价值在能力维度不在排序；(c) 系统自身相比 2026-09-26 提速 13–54×。
- **视觉主角**: 左侧对比表（三模式 vs 三 baseline，含"能力"差异列）；右上历史提速 paired bars
- **布局**: 顶部 36pt 绯红标题栏（白字标题）。主体上下两层：上层左 62% 为对比表（6 行：mode_A/B/C + bm25/vector/rrf；列=方法/金标/耗时/保底或排名/性质与能力差异），表格头底 #000066 白字、行交替 #F0F4F8/白、mode 三行用 #FFF0F0 浅绯红底 + 左侧 #A50021 4pt 边条突出；上层右 38% 为"历史提速"原生条形图（4 组 paired bars：B 342→25.0、B 234→10.2、C 1152→37.3、C 1818→33.7，旧值灰蓝 #8FA3B5、新值绯红 #A50021，右端标注倍率 13.7×/22.9×/30.9×/54.0×）。下层全宽：3 个浅蓝灰数据条（A：48.0s 端到端 · $0.182/题 · 门禁 3/3；B：66.4s · $0.300 · 2/3；C：68.9s · $0.219 · 3/3）+ 右下角 8pt 灰脚注（来源：通道2 run chatmodes-20261012T061102Z-5f9faac + 通道3 run-20261012T062847Z-5f9faac）。底部 24pt 海军蓝信息栏白字（含页码）。密度：深度。
- **内容要点**:
  - 要点1：对比表数据（逐字）——mode_A 25.0/22.7s 金标✅✅ 18/18 文档"活库+Laya判卷"；mode_B 25.0/10.2s ✅✅ 23/11 "脚本化图书管理员"；mode_C 37.3/33.7s ✅✅ 12/12 "A∥B 并行合并"；bm25 ≈0s ✅✅ 10/10 "本地静态100篇语料，doc 级，无判卷"；vector 0.1s ✅✅ 1/3 "平台向量 chunk 级，rank-1 (0.756/0.842)，无判卷"；rrf ≈0s ✅✅ 10/10 "bm25+vector 融合，无判卷" [来源：retmatrix.json + _user_materials.md §5]
  - 要点2：baseline 的局限——两道 found 题对 baseline 也是"能找到"（均 rank-1），说明题目检索难度不高；三模式的差异化价值=①活库跨书架取证（18 KB）②判卷+读全文（答案带引文与数字）③域外题如实拒答（baseline 无弃答能力，cm3 上必然假阳性）[来源：§5 + REPORT.md 发现 3]
  - 要点3：历史提速（paired bars 数据）——B q1 342.0→25.0s (13.7×)；B q2 234.0→10.2s (22.9×)；C q1 1152.0→37.3s (30.9×)；C q2 1818.0→33.7s (54.0×)；注：A 13.3/7.4s→25.0/22.7s（A 臂口径含 real-engine 硬门禁，非退化）[来源：§5 历史对照 + retmodes-20260926 run]
  - 要点4：底部三条——A 钉库向量快车道 48.0s / $0.182 / 门禁3/3；B 全库逐级 66.4s / $0.300 / 2/3（cm1 假拒答）；C 混合 68.9s / $0.219 / 3/3；弃答延迟 A=36.4s/B=29.9s/C=65.0s [来源：§4]
- **图片决策**: Q2 不通过（精确数字必须原生渲染）→ **text-only + HTML 原生条形图/表格**（AI 生图会篡改数字，禁止用于数据图）

### 第3页：发现与定论（暖学术）
- **标题**: 一个诚实的负结果：131 文档书架的工具返回超引擎预算（74.9KB→仅 2KB 预览）——机械化扫描 25s 命中
- **密度**: 中等（缺陷链 4 节点 + 对照 2 数字 + 定论 3 条）
- **论证逻辑**: (a) 不掩盖负结果：B×cm1 三连失败=系统性缺陷，且根因已被实测锁定（65.5KB catalog 灌爆 L2 描述层注意力）；(b) 对照组证明"检索架构没问题，裸 LLM 扫大 catalog 才是瓶颈"（脚本化 librarian 同题 25.0/10.2s 双金标）；(c) 收束定论：A/C 达到论文主结果标准；B 需修复 catalog 灌注口径；含负结果的数据比全绿装饰更有说服力。
- **视觉主角**: 左侧缺陷证据链（时间轴式 3 条 + 根因卡）；右侧概念配图（"海量资料 vs 聚焦扫描"）
- **布局**: 顶部 2pt 暖学术主色线。左 56%：H1 标题（22pt 宋体）→ 缺陷链 3 行证据（每行：绯红数字 + 灰文说明——① 353.5s 假拒答（流式，kb_search_vector 兜底挂起 300.0s=MCP 超时）② 41.4s 假拒答（非流式独立复现）③ 600s 挂起（t+371.8s 触发 permission_request 无人审批））→ 根因卡（#FEF9F0 象牙白 + 琥珀左边框：**转录证据**——kb_get_documents(lightweight) 对 131 文档书架返回 **74.9KB 超引擎工具输出预算**，引擎落盘全文仅透传 **2KB 预览**（persisted-output 原文引用一行），模型实际只见约 2-3 个文档；对照 53 文档 33.1KB / 75 文档 46.7KB 在预算内正常透传）→ 对照行（琥珀高亮数字：脚本化图书管理员 同题 25.0s / 10.2s 双金标命中，绕开引擎工具预算）。右 44%：概念配图占位 + 8pt 图注。底部：3 条定论横排卡片（不等宽 1.2:1:1）——① A/C 达到论文主结果标准（正确性100%/时延36–65s/成本$0.18–0.22/拒答合规）② B 需修复 catalog 透传（分块/分页/脚本化 pre-scan——面向 LLM 的工具返回预算是一层隐藏检索依赖）③ 数据含负结果与根因，比全绿装饰更具论文说服力。右下角页码。密度：中等。
- **内容要点**:
  - 要点1：缺陷三连证据（逐字）——353.5s 假拒答 / 41.4s 假拒答（两通道独立复现）/ 600s 客户端超时挂起；confirm3 时间线两次 permission_request（t+48.9 two_stage、t+371.8 vector）[来源：c1_B-cm1.json、arm_B-cm1.json、extra_B-cm1_confirm3.json]
  - 要点2：根因（会话转录取证，最终版）——131 文档书架 catalog 74.9KB（MCP 同形 72.0KB）**超引擎工具输出预算**→引擎把完整输出落盘（tool-results/call_083862a61d774ca7985b9caf.txt 101,970B 现存）仅透传 2KB 预览→模型只见约 2-3 个文档；金标条目在完整清单中（描述明写"InstructDS：将指令微调引入对话摘要…"）；成功对照：53 文档 33,089 字符 / 75 文档 46,685 字符均在预算内 [来源：9631420d 会话转录 + c1_*.json result_chars + 本会话复测]
  - 要点3：架构对照——脚本化图书管理员（词法扫描+字典序拼包，绕开引擎工具预算）同题 25.0s/10.2s 双金标命中；判卷门修正（拒答优先+结论窗口 500 字）与 vector baseline 空库修复（RAG_BENCH_VECTOR_KB=""跨库口径→12/12）一并作为工程严谨性证据 [来源：§5-6]
  - 要点4：定论三条（见布局，含 A/C 主结果标准与 B 修复方向）
- **图片决策**: Q1✓（"大量无序信息 vs 聚焦扫描"是抽象认知概念，文字描述不如一张隐喻概念图直观）Q4✓（图传达的是"认知负荷"概念，与左侧证据数字不重复）→ 1张 concept-illustration
- **配图类型**: concept-illustration
- **内容锚点**: 一名学者面前，一叠标着"2KB 预览"的薄纸无措地摊开（其余海量纸卡被一只机械臂收进了侧面档案柜）——画面另一侧一台整洁的机械扫描仪迅速挑出并照亮一张标有金色图章的卡片；传达"原始通道只收到极小预览 vs 机械化聚焦扫描全量命中"
- **配图Prompt**: "Left: a scholar silhouette holding only a tiny single sheet while a mechanical arm stacks the rest of a huge card pile into a closed side cabinet; right: a neat mechanical scanner with a lens beam highlighting one card bearing a golden seal; abstract editorial concept illustration, warm off-white #FAF9F6 background, navy #1B2A4A figures and amber gold #C8963E accent on the chosen card, flat vector illustration with subtle paper texture, no text, no gradients, 4:3"

## 四、配图生成清单

| 序号 | 文件名 | 页码 | 尺寸 | 类型 | 内容锚点 | Prompt摘要 |
|------|--------|-----|------|------|---------|-----------|
| 1 | p01_cover.png | 1 | 1536×864 | hero-cover | 三检索车道汇入知识库+判卷节点 | 三并行车道数据点流汇入古典图书馆建筑，一条车道末端有裁决节点；暖学术配色 flat vector |
| 2 | p03_finding.png | 3 | 1024×1024 | concept-illustration | 学者被纸卡山淹没 vs 机械扫描仪挑出金章卡片 | 认知过载 vs 聚焦扫描隐喻；暖学术配色 flat vector |

**配图统计**: 2页配图 / 3页总计 = 67%（第2页为原生数据渲染页，无需 AI 配图）

## 五、技术规范

- slide尺寸: **960pt×540pt（16:9, pptxgenjs LAYOUT_WIDE）** — 数据汇报场景
- 第1页: 暖学术签名（顶部2pt #1B2A4A线 + 底部1pt #E5E0D8线 + 右下 #C8963E 页码）
- 第2页: 锐学术签名（顶部 bg #A50021 h=36pt 标题栏 + 底部 bg #000066 h=24pt 信息栏）
- 第3页: 同第1页暖学术签名
- 内容区: padding 6pt 16pt；第2页表格/条形图必须为 HTML/CSS 原生元素（真实数字），禁止 AI 生图承担数据
- 图片: placeholder div + build.js addImage（Windows兼容）
- 编码: UTF-8 + meta charset
- 三页排版逻辑必须互不相同（非对称双栏 / 顶部标题栏+上下双层 / 左右分栏+底部非等宽横排）

## 六、知识直通

- 数据弹药库: `ppt_workspace/references/ref-experiment-data.md`（≈180 数据点，含逐跑明细、抽查核对、存疑口径）与 `ref-context.md`（评测口径/视觉叙事背景，标注"背景参考"不与实测混写）
- 构建者请先读 `references/_index.md` 定位，再按需深读 ref 文件；PLAN.md 中的数字已逐字校准，与 ref 文件一致（20+ 项抽查通过）
- 数字纪律：所有出现在幻灯片上的数字必须与 ref-experiment-data.md 逐字一致；存疑项（§8）不得上幻灯片
