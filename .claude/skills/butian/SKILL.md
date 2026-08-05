---
name: butian
description: >
  补天 — SOUL 人格初始化蒸馏调度器: 统一调度 nuwa-skill(公开人物/主题/思维框架
  深度调研蒸馏)与 dot-skill(同事/熟人/关系/本地材料蒸馏)双引擎, 蒸馏产物统一
  转换为补天种子包(meta.json/persona.md/work.md/values.md), 经 ragctl soul
  distill 落地为 soul-<name> 人格(模板+种子融合的 4 宪法文档 + soul-config),
  随后驱动好奇心训练(learn → 审批 → 定时进化)与人格增强检索问答
  (soul_qdcvr_ask)。与 soul skill 分工: soul 管"人格全生命周期", butian 管
  "初始人格从哪来"。触发词: 补天, 造SOUL, 创建初始人格, 蒸馏人格, 蒸馏XX,
  造个XX人格, XX的思维方式, XX视角人格, nuwa, 女娲, dot-skill, 初始人格定义,
  把XX蒸馏成SOUL, distill persona to soul, butian。
---

# 补天 — SOUL 人格蒸馏调度器(先天基因 × 后天进化)

**执行者:主 Agent 直接执行(蒸馏编排 + 种子落地,不委托 Archival)**

> **⭐ 心智模型**:补天 = 两条"基因生产线"(nuwa × dot-skill) + 一个"受精口"
> (ragctl soul distill)。蒸馏产物 → 种子包(统一契约) → SOUL 人格(先天种子)
> → 好奇心训练(后天进化) → 检索增强问答(使用)。
>
> **MANDATORY — 按需加载参考**:
> - 架构/文件定义/数据流 → [references/butian-architecture.md](references/butian-architecture.md)
> - 种子包格式契约 → [references/seed-contract.md](references/seed-contract.md)
> - 落地后的训练/评估/问答细节 → `../soul/SKILL.md` §B/§C/§D
> - nuwa 蒸馏细节 → `../nuwa-skill/SKILL.md`(女娲造人术)
> - dot-skill 蒸馏细节 → `../dot-skill/SKILL.md`
> - SOUL × 补天完整协议 → `../soul/references/soul-distill-integration.md`

---

## 思维框架:意图分流 ⭐

```
用户需求
  └── 要"创建/蒸馏一个人格/SOUL"?
       ├── 是 → 判断素材形态(见场景分类表)→ 选引擎 → 蒸馏 → 种子 → SOUL 落地 → 训练 → 问答
       ├── 否,但含"XX的思维方式/用XX视角" → 已有 SOUL? 有→soul 问答; 无→走蒸馏
       └── 否 → 交回 soul / knowledgebase skill(人格管理/训练/检索)
```

匹配后按 **分流 → 蒸馏 → 转换 → 落地 → 进化 → 使用** 六步执行。

---

## 场景分类表

| Signal keywords | 引擎/路径 | 产物 → 落地 |
|---|---|---|
| 蒸馏XX(公开人物), 女娲, nuwa, XX的思维方式, 造个XX视角, 思维顾问 | **nuwa-skill** | `[person]-perspective/SKILL.md` → `nuwa_to_seed.py` → seed |
| 蒸馏同事/熟人, 关系人格, 本地材料(飞书/钉钉/文件), dot-skill, /dot-skill | **dot-skill** | `<dir>/meta.json+persona.md+work.md` → 直接用(已是 seed 契约) |
| 直接源材料(聊天记录/文档/描述)+ 需求, distill-text, distill-files | **后端 LLM 蒸馏** | `ragctl soul distill-text / distill-files` → 直接建 SOUL |
| 已有种子目录(meta.json+persona.md+work.md), soul distill | **ragctl 落地** | 跳过蒸馏, 直接 `ragctl soul distill` |
| 蒸馏名人但已有本地一手素材(传记PDF/访谈字幕) | **nuwa 本地语料模式** 或 dot-skill celebrity | 二选一(见下) |

**三种初始化 SOUL 创建方式(前端创建 modal 三模式 + skill 三入口一一对应)**:

| 前端模式 | skill 入口 | 输入 → 流程 |
|---|---|---|
| **女娲** | `Skill("butian")` → `Skill("nuwa-skill")` | 知名人物/主题 → (快速) LLM 蒸馏 or (深度) 6 Agent 网络搜索 → SKILL.md → 种子 → SOUL |
| **dot-skill** | `Skill("butian")` → `Skill("dot-skill")` | 材料(文本/文件/种子包) → 蒸馏 → 种子契约 → SOUL |
| **补天·集成** | `Skill("butian")` 直接调度 | 人物需求 + 材料 双通道 → 融合蒸馏 → SOUL |
| 模板初始化 | `soul_init` | 无蒸馏输入 → 模板人格 |

**nuwa vs dot-skill 抉择**:
- 公开人物/主题 + 需要网络深研(6 Agent 多维调研 + 心智模型三重验证)→ **nuwa**
- 内部同事/熟人/关系 + 本地材料采集(飞书/钉钉/邮件/文件)→ **dot-skill**
- 名人 + 用户手握一手素材 → 两者皆可: 素材充分走 dot-skill(快), 要深度思维框架
  提炼走 nuwa(本地语料优先模式, 网络补缺口)
- 模糊需求(「我想提升决策质量」)→ nuwa Phase 0B 需求诊断, 推荐蒸馏对象

---

## Sequential Workflow

### Step 0 — Pre-Flight(强制)
- `soul_list` 可用 → MCP 在线; 后端 `ragctl soul list` 或 `curl :8765/api/v1/soul/list` 通 → 后端在线
- `ragctl` 可用(`command/ragctl.bat` 或 PATH 中的 ragctl)
- 失败 → 报"MCP/后端不可用", 不继续

### Step 1 — 意图分流
按上表匹配引擎。用户只说"补天/造个SOUL"没给对象 → 问 2 个问题:
1. 蒸馏对象是: 公开人物/主题(走 nuwa 深研)? 同事熟人(走 dot-skill 本地材料)? 还是你有现成源材料(直接文本蒸馏)?
2. 领域范围(后续 kb_scope)与用途(思维顾问/问答人格/工作人格)?

### Step 2 — 引擎蒸馏(委托对应 skill)
- **nuwa 路径**: 调用 `Skill("nuwa-skill")` 完整执行(Phase 0A 档位确认 → 0.5 目录
  → 1 采集 → 1.5 检查点 → 2 提炼 → 2.5 检查点 → 3 构建 → 4 验证 → 5 精炼)。
  **在 Phase 0A 确认时就告知用户**: 本仓库会自动把产物落地为 SOUL 人格(补天集成),
  默认执行; 用户可取消。
- **dot-skill 路径**: 调用 `Skill("dot-skill")` 执行(注意: dot-skill 是自包含
  skill, 需按其 SKILL.md 的 Execution Root 规则运行 tools/ 脚本)。

### Step 3 — 产物转换(统一种子契约)
- dot-skill 产物目录: 已含 `meta.json + persona.md + work.md`, 即种子契约, 直接用
- nuwa 产物目录: 运行转换器(确定性章节拆分, 无 LLM 成本):
```
python .claude/skills/butian/scripts/nuwa_to_seed.py <perspective-skill-dir> \
  [--out <seed-dir>] [--labels 额外路由标签]
```
- 产物: `meta.json / persona.md / work.md / values.md(可选, 价值观增强)`
- 转换后核对: persona/work 非空, meta.tags.personality 有路由标签
- 展示种子摘要给用户确认(人格名/路由标签/scope)

### Step 4 — SOUL 落地(受精)
```
ragctl soul distill <seed-dir> --name soul-<名字> \
  --scope kb1,kb2            # 缺省 ["*"] 全部公开库
  [--labels 标签1,标签2]      # 缺省 = meta.tags.personality 前3 + impression
  [--values <seed-dir>/values.md]   # nuwa 产物: 价值观增强(创建时融合, 宪法层一次定型)
  [--harness omp|claude]
```
- 自动完成: 建库 → 写 4 文档(模板+种子融合)→ bootstrap(profile+config)→ 索引
- 验证: 输出含 `docs_created=4` + `profile_summary_generated=true`;
  `ragctl soul list` 可见新人格
- **无 ragctl/离线时** → MCP 手动编排(见 soul-distill-integration.md §3b,
  主 agent 用 kb_create + kb_doc_create×4 + POST /api/v1/soul/bootstrap + index_document)

### Step 5 — 后天好奇心进化(种子成长)
```
ragctl soul learn-all soul-<名字> --rounds 2     # 好奇心训练(四层问题→自答→四维自评→蒸馏)
ragctl soul review soul-<名字> --action list     # 审记忆草稿
ragctl soul review soul-<名字> --action approve --draft <id>
ragctl soul harness soul-<名字> omp               # 训练引擎(可选)
# 定时进化(可选):
#   experience_meditation_config_update(soul_kb_id, {enabled: true, interval_hours: 24, rounds_per_run: 2})
```
- 进化闭环: 训练产出草稿 → 审批注册 → profile 刷新 → 路由更准 → 持续学新文档
- 细节与预算敬畏 → soul skill §B

### Step 6 — 使用(人格增强检索问答)
```
ragctl soul ask "问题" --soul soul-<名字>           # 人格问答
ragctl soul ask "问题" --soul soul-<名字> --qdcvr   # 一键: 知识库检索→人格合成(推荐)
# 或 MCP: soul_qdcvr_ask(query, soul_kb_id="soul-<名字>", task_goal, task_type, async_mode=True)
```
- 自动路由(不指定人格)→ `soul_router` 按 domain_labels 选最优
- 前端: SOUL 页面 → 问答 modal "一键检索+人格回答"

---

## 补天流水线速览(一条命令到成品人格)

```
需求 → 蒸馏(nuwa/dot-skill) → 转换(nuwa_to_seed.py) → 落地(ragctl soul distill)
     → 训练(learn-all --rounds 2) → 审批(review approve) → 问答(soul_qdcvr_ask)
```

---

## Rules — 强制执行

1. **统一契约**: 一切蒸馏产物先归一为种子包(meta.json+persona.md+work.md+可选
   values.md)再落地, 禁止绕过契约直接写 SOUL 文档
2. **宪法层一次定型**: 价值观/记忆约定只允许在创建时融合(ragctl --values/--mem),
   创建后自动流程不得修改宪法层(唯一例外: RL 认知草稿审批通道)
3. **不污染人格记忆**: 种子 persona/work 是"先天身份"(初始化文档), 不是"后天
   知识"(记忆), 绝不写入 memories/
4. **委托而非重造**: nuwa/dot-skill 蒸馏细节在各自 skill, 补天只做调度与转换;
   训练/评估/问答走 soul skill 协议
5. **预算敬畏**: 蒸馏档位在 Phase 0A 确认(快速/标准/深度); 训练前看
   soul_status.estimated_cost_usd
6. **检查点是纠偏不是阻塞**: nuwa Phase 1.5/2.5/4/5 的确认给默认值, 不卡交付
7. **三入口一致**: 前端(SOUL 页面)/ ragctl / MCP 走同一后端同一数据

## NEVER 清单

| ❌ | ✅ | 为什么 |
|---|---|---|
| 把 nuwa SKILL.md 直接塞给 ragctl soul distill | 先 nuwa_to_seed.py 转种子包 | ragctl 契约是 meta.json+persona.md+work.md, 不转换必失败 |
| 创建后用 kb_doc_update 改 values.md | 创建时 --values 融合定型 | 宪法层创建后只读, 改=绕过受控通道 |
| 把 persona/work 当记忆入库 | 只走 soul_learn → 审批 | 先天身份混入后天知识, 破坏质量闸门 |
| 蒸馏和训练一条龙跑到底不确认 | 蒸馏检查点(1.5/2.5/4)+ 落地确认 + 训练 dry_run | 长任务成本失控, 用户有权随时纠偏 |
| 跳过 ragctl 直接 curl 拼接口 | ragctl 已封装完整编排 | 重复实现=新 bug 源; MCP 离线时才手动编排 |
| 用户已有 SOUL 还用补天新建 | 先 soul_list 查重, 走 soul 更新/进化 | 人格重复=路由混乱 |

**失败回退**: ragctl 不可用 → MCP 手动编排(§3b 协议); MCP 不可用 →
REST `http://localhost:8765/api/v1/soul/*`(与 MCP 同数据)。

## Tool Quick Reference

- `python .claude/skills/butian/scripts/nuwa_to_seed.py <dir> [--out] [--labels]` — nuwa 产物 → 种子包
- `ragctl soul distill <seed-dir> [--name] [--scope] [--labels] [--values] [--harness]` — 种子 → SOUL(推荐入口)
- `ragctl soul distill-text <name> --req R --material M` / `distill-files <name> <files>` — 直接源材料蒸馏
- `ragctl soul learn-all <soul> --rounds N` / `soul review` / `soul harness` — 后天进化
- `ragctl soul ask <q> --soul <soul> [--qdcvr]` — 人格增强问答
- `soul_list()` / `soul_qdcvr_ask()` / `soul_learn_all()` / `soul_review_drafts()` — MCP 等价
- `Skill("nuwa-skill")` / `Skill("dot-skill")` / `Skill("soul")` — 引擎与生命周期细节
