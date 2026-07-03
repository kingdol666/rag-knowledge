# Experience 经验机制 — 三位一体实现计划

> 状态: `pending approval`  
> 计划版本: v1.0  
> 计划路径: `.omc/plans/experience-mechanism-full-plan.md`

---

## 设计概览

**核心思想**: 在现有知识库系统中增加"经验"维度，让知识库不仅能存文档，还能存"经验教训/最佳实践/故障排查流程"这种带有**评分、应用记录、场景绑定、关联文档**的半结构化知识。

### 三位一体架构

```
┌─────────────────────────────────────────────────────┐
│                   Agent / User                       │
├─────────────────────────────────────────────────────┤
│                     ▼                                │
│           Skill（knowledge-experience）               │
│          Agent决策 + 工作流编排                       │
├─────────────────────────────────────────────────────┤
│                     ▼                                │
│           MCP 工具层（10个工具）                       │
│    create / read / list / update / delete            │
│    apply / review / find_by_scenario / summary       │
├─────────────────────────────────────────────────────┤
│                     ▼                                │
│           HTTP API（Backend + Web Nuxt）              │
│    POST/GET/PUT/DELETE /api/v1/experience/*          │
├─────────────────────────────────────────────────────┤
│                     ▼                                │
│       文件系统：experience/ 目录                       │
│   .experience-index.yml + exp-xxx.md + images/       │
└─────────────────────────────────────────────────────┘
```

### 设计决策

| 维度 | 决策 | 理由 |
|------|------|------|
| 存储 | 独立 `experience/` 文件夹 | 不干扰已有文档，职责分离 |
| 索引 | `.experience-index.yml` | 与 `.knowledge-base.yml` 一致的设计哲学 |
| 检索 | 场景优先 + 评分排序 | 经验的核心价值在于可复用性 |
| 评分 | 用户评审 + 应用统计 | 群体智慧决定经验可信度 |

### 10 个 MCP 工具

| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `experience_create` | 创建经验 | kb_id, title, scenario, category, problem, solution, key_lessons |
| `experience_read` | 读取经验 | kb_id, exp_id |
| `experience_list` | 列经验（可过滤） | kb_id, scenario?, category?, tag? |
| `experience_update` | 更新经验 | kb_id, exp_id, ...任意字段 |
| `experience_delete` | 删除经验 | kb_id, exp_id |
| `experience_apply` | 标记应用 | kb_id, exp_id, user, result |
| `experience_review` | 评审经验 | kb_id, exp_id, reviewer, rating |
| `experience_find_by_scenario` | 按场景检索 | kb_id, scenario |
| `experience_summary` | 经验统计 | kb_id |

### 计划共 5 个 Phase，约 5 天

| Phase | 内容 | 时间 |
|:-----:|------|:----:|
| 1 | Backend 存储层 + API 路由 | 2天 |
| 2 | MCP 工具层 | 1天 |
| 3 | Nuxt 代理 + 自动初始化 | 1天 |
| 4 | Skill 集成 | 0.5天 |
| 5 | 测试验证 | 0.5天 |

---

**完整设计文档: `.omc/plans/experience-mechanism-full-plan.md`**
