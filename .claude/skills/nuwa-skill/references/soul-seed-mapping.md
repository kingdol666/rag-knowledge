# nuwa → SOUL 种子映射 — 女娲产物落地细则

> 配合 butian skill 使用: nuwa 蒸馏完成后, 产物经 nuwa_to_seed.py 转换为
> 补天种子包, 再经 ragctl soul distill 落地为 SOUL 人格。本文是章节级映射权威。

## 1. 双产物模型

```
nuwa 蒸馏完成
  ├─ 产物 A: [person]-perspective/SKILL.md      ← 独立可运行的人物 Skill(开源分发)
  ├─ 产物 B: references/research/0X-*.md        ← 6 维调研原始材料(自包含)
  └─ 产物 C: soul-seed/ (转换器生成)             ← 补天种子包(SOUL 落地输入)
       ├─ meta.json  persona.md  work.md  values.md
```

产物 A 始终生成(nuwa 本职); 产物 C 由 butian 调度器一键转换, 不重复劳动。

## 2. 章节 → 种子 → SOUL 文档映射

| nuwa SKILL.md 章节 | → 种子文件 | → SOUL 文档 | 说明 |
|---|---|---|---|
| `## 身份卡` | persona.md | soul-definition.md 追加段 | 我是谁/起点/现状 → 身份定位 |
| `## 表达DNA` | persona.md | soul-definition.md 追加段 | 句式/词汇/节奏/幽默/确定性 → 语言风格 |
| `## 角色扮演规则` | persona.md(截取至退出角色) | soul-definition.md 追加段 | 输出纪律/未表态标推断 |
| `## 诚实边界` | persona.md | soul-definition.md 追加段 | 知识边界/调研截止时间 |
| `## 回答工作流(Agentic Protocol)` | work.md | thinking-style.md 追加段 | 先做功课再回答 → 推理模式 |
| `## 核心心智模型`(### 模型N:) | work.md | thinking-style.md 追加段 | 思维镜片(三重验证过的) |
| `## 决策启发式` | work.md | thinking-style.md 追加段 | 判断规则 |
| `## 智识谱系` | work.md | thinking-style.md 追加段 | 思想来源与位置 |
| `## 人物时间线(关键节点)` | work.md | thinking-style.md 追加段(背景) | 语境知识 |
| `## 失败模式与 Fallback 树` | work.md | thinking-style.md 追加段 | 降级规则 |
| `## 价值观与反模式` | values.md | values.md 追加段 | 宪法层价值观(ragctl --values) |
| `## 附录：调研来源` | (留在 skill 目录) | — | 溯源依据, 不入种子 |
| frontmatter `name` | meta.json.slug | soul-<slug> 库名 | name 去掉 -perspective 后缀 |
| frontmatter `description` | meta.json.impression + tags | KB description + domain_labels | 首句作印象, 模型名作路由标签 |
| 身份卡「我是谁」 | meta.json.display_name | KB 名/展示 | 截取 30 字 |

## 3. 路由标签生成规则(domain_labels)

1. display_name(如 "Steve Jobs")
2. slug(如 "steve-jobs")
3. 心智模型名(### 模型N: 标题, 最多补足 8 个)
4. 可选 --labels 显式追加

落地时 ragctl 缺省取前 3 + impression 前 12 字 → 路由:「什么问题派给谁」由
人格名+模型名命中, 比通用标签更精准。

## 4. values.md 的宪法层处理

- nuwa 的「价值观与反模式」→ values.md 追加段, 在 **创建时** 经
  `ragctl soul distill --values values.md` 融合进模板 values.md
- 模板的通用研究价值观(真实性优先/诚实边界/知识谦逊)保留在文档前半,
  蒸馏价值观追加在后 → 两份价值观并列, 训练/评估同时参考
- **创建后不可改**(宪法层只读); 要调整走 soul_reflect 漂移报告 + 人工决策

## 5. 主题 Skill 变体(xx-framework, 非人物)

- 无身份卡 → display_name 回退 frontmatter name
- 无表达DNA → persona.md 只含角色规则/边界(若存在)
- 无价值观与反模式 → 不产出 values.md(ragctl 不传 --values)
- 其余映射不变

## 6. 校验清单(转换后)

- [ ] persona.md / work.md 非空
- [ ] meta.json 可解析, slug 无 -perspective 后缀
- [ ] values.md 存在(人物类)
- [ ] ragctl soul distill 落地成功(docs_created=4 + profile)
- [ ] soul_list 可见, domain_labels = 人格名+模型名
