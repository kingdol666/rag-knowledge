# 种子包契约 — 补天蒸馏产物统一落地格式

> 消费方: `ragctl soul distill`(command/ragctl.js) · 生产方: dot-skill 原生 /
> butian `nuwa_to_seed.py`。本契约是"蒸馏产物 → SOUL 人格"的唯一落地接口。

## 1. 目录结构

```
seed-dir/
├── meta.json      # 必选 — 元数据(路由标签/印象)
├── persona.md     # 必选 — 身份/性格/表达风格/诚实边界(→ soul-definition.md 追加段)
├── work.md        # 必选 — 职责/思维框架/决策启发式/工作流程(→ thinking-style.md 追加段)
└── values.md      # 可选 — 价值观与反模式(→ values.md 追加段, ragctl --values 消费)
```

## 2. meta.json 字段

```json
{
  "slug": "steve-jobs",                    // 库名后缀: soul-<slug>
  "name": "Steve Jobs",                    // 展示名
  "display_name": "Steve Jobs",
  "character": "celebrity",                // colleague | relationship | celebrity
  "research_profile": "budget-unfriendly", // dot-skill 兼容字段(默认 budget-friendly)
  "tags": { "personality": ["Steve Jobs", "聚焦即说不", "端到端控制"] },
  "impression": "乔布斯的思维框架与表达方式",  // 前12字参与路由
  "source": "nuwa-skill"                   // 生产引擎(溯源)
}
```

- ragctl 落地时: `--name` 缺省 = `soul-<slug>`; `--labels` 缺省 =
  `tags.personality` 前 3 + `impression` 前 12 字
- `impression` 同时写入 KB description

## 3. persona.md 要求(→ soul-definition.md)

- 内容: 身份卡 / 角色扮演规则(摘要) / 表达DNA / 诚实边界
- 落地融合: `模板 soul-definition.md` + `# 补天蒸馏人格: <name>` + persona.md
- **模板章节必须保留**(profile-summary 生成器与 language-style 解析依赖模板结构);
  补天内容只做追加段

## 4. work.md 要求(→ thinking-style.md)

- 内容: 回答工作流(Agentic Protocol) / 核心心智模型 / 决策启发式 / 智识谱系 /
  人物时间线(背景) / 失败模式与降级规则
- 落地融合: `模板 thinking-style.md` + `# 补天蒸馏工作方式: <name>` + work.md

## 5. values.md(可选, 补天增强)

- 内容: 价值观与反模式(我追求的 / 我拒绝的 / 我没想清楚的)
- 落地融合: `模板 values.md` + `# 补天蒸馏价值观: <name>` + values.md
- **宪法层一次定型**: 仅在创建时融合(ragctl --values), 创建后自动流程不得修改

## 6. 验收标准

| 检查 | 达标 |
|---|---|
| meta.json 可 JSON.parse, slug 非空 | ✅ |
| persona.md / work.md 非空 | ✅ |
| tags.personality 非空(否则 ragctl 用 --labels 兜底) | ✅ |
| ragctl soul distill 输出 docs_created=4 + profile_summary_generated=true | ✅ |
| soul_list 可见新人格, domain_labels 正确 | ✅ |

## 7. 生产方对齐

| 生产方 | 对齐方式 |
|---|---|
| dot-skill | 原生产物即契约(meta.json+persona.md+work.md); values.md 不产出 |
| nuwa-skill | `python .claude/skills/butian/scripts/nuwa_to_seed.py <dir>` 转换, 额外产出 values.md |
| 后端文本蒸馏 | 不经种子包, 直接 `ragctl soul distill-text/files`(LLM 提取 persona/work/meta) |

## 8. 兼容性

- ragctl 契约只读 meta.json/persona.md/work.md → 新增字段/文件不破坏旧产物
- 旧 dot-skill 产物(无 source 字段)→ 正常落地(source 缺省 "dot-skill")
- 无 values.md 的种子 → ragctl 不传 --values, values 保持纯模板(行为与既有一致)
