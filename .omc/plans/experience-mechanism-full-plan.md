# Experience 经验机制 — 三位一体实现计划

> 状态: `pending approval`

---

## 一、需求总结

**核心目标**: 在知识库中增加"经验"维度，让知识库系统不仅能存文档，还能存"经验教训/最佳实践/故障排查流程"这种带有**评分、应用记录、场景绑定、关联文档**的半结构化知识。

**关键约束**:
1. experience/ 文件夹在 KB 创建时自动初始化
2. 经验不干扰已有文档操作，但可互相链接
3. API + MCP + Skill 三位一体设计
4. 经验支持：场景分类、量化评分、成功/失败标记、关联文档
5. 路径规范: 所有路径用 pathlib/import.meta.url 动态解析
6. 零硬编码端口

---

## 二、RALPLAN-DR 摘要

### Principles (原则)

| # | 原则 | 说明 |
|:-:|------|------|
| P1 | **不破坏现有架构** | experience 是并行子系统，不修改已有文档/KB CRUD |
| P2 | **存储一致性** | `.experience-index.yml` 同 `.knowledge-base.yml` 一样的双写机制 |
| P3 | **渐进式检索** | 经验检索继承搜索引擎风格——按场景→按评分→按向量 |
| P4 | **可溯源** | 每一条经验必须追溯：创建者→关联文档→应用记录 |
| P5 | **API/MCP/Skill 三层桥接** | MCP 是用户交互层、API 是服务层、Skill 是 Agent 决策层 |

### Decision Drivers (决策驱动因素)

| # | 驱动因素 | 权重 |
|:-:|----------|:----:|
| D1 | **经验的价值 = 可复用的程度** —— 需要有评分/应用次数来排序 | 高 |
| D2 | **场景是经验的第一索引** —— 不是搜关键词，是匹配作业场景 | 高 |
| D3 | **经验不是文档** —— 需要有结构化的元数据：严重程度/成功率/关键教训 | 中 |

### Viable Options (方案选择)

#### Option A: 独立的文件系统 + 独立的 MCP 工具 (推荐)
- **方案**: experience/ 文件夹独立于现有文档体系，10个新 MCP 工具
- **Pros**: 职责清晰、不干扰现有文档、容易扩展
- **Cons**: 工具数量多、需要完整的 CRUD 实现

#### Option B: 在现有文档上增加 experience 标签
- **方案**: 文档 metadata 扩展 experience 字段
- **Pros**: 工具少、复用现有 CRUD
- **Cons**: 数据结构混杂、无法独立排序/评分、可维护性差

**决策**: 选 Option A。经验不是文档，需要独立的元数据、检索逻辑、评分体系。

---

## 三、存储架构设计

### 文件系统结构

```
web/storage/tree-file-system/
├── Thermal-Power-Monitoring/
│   ├── .knowledge-base.yml          # 已有 — 文档索引
│   ├── experience/                   # ★ 新建
│   │   ├── .experience-index.yml    # 经验元数据索引
│   │   ├── exp-coal-mill-001.md     # 经验正文
│   │   ├── exp-turbine-002.md
│   │   └── images/                  # 经验相关图片
│   ├── doc1.md
│   └── images/
├── .tree-fs.json
```

### `.experience-index.yml` 元数据索引

```yaml
knowledge_base:
  id: "Thermal-Power-Monitoring"
  path: "Thermal-Power-Monitoring"
experience_count: 3
experience_tags:
  - coal-mill-fault
  - turbine-diagnostics
  - best-practice

experiences:
  - id: "exp-coal-mill-001"
    title: "磨煤机堵煤故障排查流程"
    path: "Thermal-Power-Monitoring/experience/exp-coal-mill-001.md"
    scenario: "coal-mill-fault-prediction"      # 场景标识
    category: "troubleshooting"                  # 类别
    severity: "critical"                         # critical/important/normal/tip
    status: "published"                          # draft/published/archived
    tags: ["磨煤机", "堵煤", "CNN-LSTM"]
    
    # 核心内容结构化
    problem: "磨煤机压差异常升高，疑似堵煤故障"
    solution: "CNN-LSTM偏差度+MSET比对+压差趋势三重确认后降给煤量10%"
    result: "success"                            # success/partial/failed/inconclusive
    key_lessons:
      - "CNN-LSTM偏差度>0.7且压差上升→即将堵煤概率>90%"
      - "快速操作：降给煤量10%并维持5分钟"
    
    # 量化指标
    metrics:
      effectiveness: 95
      difficulty: 60
      success_rate: 88
    
    # 关联
    related_docs:
      - "Thermal-Power-Monitoring/基于CNN-LSTM磨煤机故障预警_7cbcc650.md"
    related_experiences: []
    prerequisites: ["CNN-LSTM模型已运行"]
    
    # 生命周期
    author: "chief-engineer-li"
    created_at: "2026-06-28T14:30:00Z"
    updated_at: "2026-07-01T09:15:00Z"
    
    # 使用统计
    applied_count: 12
    rating_avg: 4.5
    review_count: 8
    
    # 向量索引
    vector_index:
      collection: "exp_Thermal-Power-Monitoring"
      total_chunks: 5
```

### 经验正文 Markdown 格式

```markdown
# 磨煤机堵煤故障排查流程

## 经验概览
- **知识库**: Thermal-Power-Monitoring
- **类别**: 故障排查 | **严重程度**: 🔴 紧急
- **创建时间**: 2026-06-28 | **成功率**: 88%

## 问题
磨煤机压差异常升高，CNN-LSTM模型偏差度 >0.7

## 排查步骤
### 第1步：确认信号
检查CNN-LSTM偏差度、压差趋势、传感器交叉验证

### 第2步：快速响应
降给煤量10%，维持5分钟观察

### 第3步：深度诊断
MSET模型比对、多参数联合分析

## 关键结论
> 三重确认后诊断准确率可达95%以上

## 关联知识
- 📄 [CNN-LSTM磨煤机故障预警论文](./based...)

## 应用记录
| 使用者 | 场景 | 效果 | 日期 |
|--------|------|------|------|
| shift-lee | #3机 | 成功避免堵煤 | 2026-07-01 |
```

---

## 四、Backend API 设计

### 4.1 新增文件

| 文件 | 用途 |
|------|------|
| `backend/app/api/routes/experience.py` | 经验 API 路由 (router) |
| `backend/app/models/experience_models.py` | Pydantic 请求/响应模型 |
| `backend/app/services/experience_service.py` | 经验核心服务 (ExperienceService class) |

### 4.2 路由定义

```python
# backend/app/api/routes/experience.py
router = APIRouter(prefix="/api/v1/experience", tags=["Experience"])

# CRUD
POST   /api/v1/experience/{kb_id}                  → create
GET    /api/v1/experience/{kb_id}                   → list
GET    /api/v1/experience/{kb_id}/{exp_id}          → read
PUT    /api/v1/experience/{kb_id}/{exp_id}          → update
DELETE /api/v1/experience/{kb_id}/{exp_id}          → delete

# 操作
POST   /api/v1/experience/{kb_id}/{exp_id}/apply    → apply (记录应用)
POST   /api/v1/experience/{kb_id}/{exp_id}/review   → review (评审)
GET    /api/v1/experience/{kb_id}/summary           → summary (统计)

# 初始化
POST   /api/v1/experience/{kb_id}/init              → init (创建experience文件夹)
```

### 4.3 Pydantic 模型 (experience_models.py)

```python
from enum import Enum
from typing import Optional

class ExperienceCategory(str, Enum):
    BEST_PRACTICE = "best_practice"
    TROUBLESHOOTING = "troubleshooting"
    LESSON_LEARNED = "lesson_learned"
    OPTIMIZATION = "optimization"
    TIP = "tip"
    WORKFLOW = "workflow"
    DECISION = "decision"

class ExperienceResult(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"

class ExperienceSeverity(str, Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    NORMAL = "normal"
    TIP = "tip"

class ExperienceStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class ExperienceCreate(BaseModel):
    title: str
    scenario: str = ""
    category: ExperienceCategory = ExperienceCategory.TIP
    problem: str = ""
    solution: str = ""
    result: ExperienceResult = ExperienceResult.SUCCESS
    key_lessons: list[str] = []
    tags: list[str] = []
    severity: ExperienceSeverity = ExperienceSeverity.NORMAL
    related_docs: list[str] = []
    prerequisites: list[str] = []
    metrics: dict = {}

class ExperienceUpdate(BaseModel):
    title: str = ""
    scenario: str = ""
    category: ExperienceCategory = None
    problem: str = ""
    solution: str = ""
    result: ExperienceResult = None
    key_lessons: list[str] = None
    tags: list[str] = None
    severity: ExperienceSeverity = None
    status: ExperienceStatus = None
    related_docs: list[str] = None
    metrics: dict = None

class ExperienceApplyRequest(BaseModel):
    user: str = ""
    context: str = ""
    result: str = ""
    notes: str = ""

class ExperienceReviewRequest(BaseModel):
    reviewer: str = ""
    rating: float
    comment: str = ""

# 响应模型
class ExperienceResponse(BaseModel):
    success: bool
    experience: dict | None = None
    error: str | None = None
```

### 4.4 Service 核心 (experience_service.py)

```python
class ExperienceService:
    """经验管理系统服务。单例模式，同 config 一致。"""
    
    STORAGE_PATH = None  # 延迟解析，避免循环依赖
    
    @property
    def storage_root(self) -> Path:
        return self._get_storage_root()  # 从 get_storage_root() 获取
    
    def _exp_dir(self, kb_path: str) -> Path:
        return self.storage_root / kb_path / "experience"
    
    def _index_path(self, kb_path: str) -> Path:
        return self._exp_dir(kb_path) / ".experience-index.yml"
    
    # ── 初始化 ──
    async def init_experience_folder(self, kb_path: str) -> bool:
        exp_dir = self._exp_dir(kb_path)
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "images").mkdir(exist_ok=True)
        if not self._index_path(kb_path).exists():
            yaml_content = {
                "knowledge_base": {"id": kb_path, "path": kb_path},
                "experience_count": 0,
                "experience_tags": [],
                "experiences": []
            }
            self._write_index(kb_path, yaml_content)
        return True
    
    # ── CRUD ──
    async def create_experience(self, kb_id: str, data: ExperienceCreate) -> dict:
        exp_id = f"exp-{uuid4().hex[:12]}"
        md_content = self._generate_markdown(data, exp_id)
        rel_path = f"{kb_id}/experience/{exp_id}.md"
        fs_path = self.storage_root / rel_path
        fs_path.write_text(md_content, encoding="utf-8")
        self._append_to_index(kb_id, exp_id, data, rel_path)
        return {"id": exp_id, "path": rel_path}
    
    async def read_experience(self, kb_id: str, exp_id: str) -> dict | None:
        index = self._read_index(kb_id)
        for exp in index.get("experiences", []):
            if exp["id"] == exp_id:
                return exp
        return None
    
    async def list_experiences(self, kb_id: str, scenario: str = "",
                                category: str = "", tags: list = None) -> list:
        index = self._read_index(kb_id)
        exps = index.get("experiences", [])
        # 过滤逻辑略
        return sorted(exps, key=lambda x: x.get("rating_avg", 0), reverse=True)
    
    async def update_experience(self, kb_id: str, exp_id: str, data: ExperienceUpdate) -> bool:
        # 更新索引 + 重新生成 md（如果标题/内容变了）
        pass
    
    async def delete_experience(self, kb_id: str, exp_id: str) -> bool:
        # 删除索引条目 + 删除 md 文件
        pass
    
    # ── 操作 ──
    async def apply_experience(self, kb_id: str, exp_id: str,
                                req: ExperienceApplyRequest) -> bool:
        # 增加 applied_count + 记录应用日志
        pass
    
    async def review_experience(self, kb_id: str, exp_id: str,
                                 req: ExperienceReviewRequest) -> bool:
        # 更新 rating_avg + review_count
        pass
    
    # ── 搜索 ──
    async def search_experience(self, kb_id: str = "", query: str = "",
                                 scenario: str = "", tag: str = "") -> list:
        # 搜索 .experience-index.yml 元信息
        pass

experience_service = ExperienceService()
```

### 4.5 路由注册修改 (backend/app/main.py)

```python
# 新增导入
from app.api.routes.experience import router as experience_router

# 注册路由
app.include_router(health_router)
app.include_router(parse_router)
app.include_router(mineru_router)
app.include_router(search_router)
app.include_router(graph_router)
app.include_router(experience_router)  # ← 添加
```

### 4.6 路由导出发送

```python
# backend/app/api/routes/__init__.py (新增)
from app.api.routes.experience import router as experience_router

__all__ = [
    ...,
    "experience_router"
]
```

---

## 五、Web Nuxt 代理层

### 5.1 新增 Nuxt 路由

Nuxt 3 文件系统路由模式：文件路径 = API 路径。

```typescript
// web/server/api/experience/[kbId]/init.post.ts
export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  // POST 转发到 backend /api/v1/experience/{kbId}/init
})

// web/server/api/experience/[kbId]/index.get.ts        → list
// web/server/api/experience/[kbId]/[expId].get.ts       → read
// web/server/api/experience/[kbId]/index.post.ts         → create
// web/server/api/experience/[kbId]/[expId].put.ts        → update
// web/server/api/experience/[kbId]/[expId].delete.ts     → delete
// web/server/api/experience/[kbId]/[expId]/apply.post.ts → apply
// web/server/api/experience/[kbId]/[expId]/review.post.ts → review
```

### 5.2 代理模式 (遵循现有设计)

沿用 Nuxt 代理到后端的方式：

```typescript
// web/server/api/experience/[kbId]/index.get.ts
import { defineEventHandler, getRouterParam } from 'h3'
import { getServerConfig } from '~/utils/paths.mjs'

export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  const config = getServerConfig()
  const backendUrl = process.env.BACKEND_URL || config.backend_url
  
  const response = await fetch(
    `${backendUrl}/api/v1/experience/${encodeURIComponent(kbId)}`
  )
  return await response.json()
})
```

---

## 六、MCP 工具设计

### 6.1 客户端方法 (kb_client/client.py)

```python
# ── 经验 CRUD ──

async def experience_init(self, kb_id: str) -> dict:
    """初始化经验文件夹"""
    return await self._post_backend_json(f"/api/v1/experience/{kb_id}/init", {})

async def experience_create(self, kb_id: str, title: str, scenario: str = "",
    category: str = "tip", problem: str = "", solution: str = "", result: str = "success",
    key_lessons: list = None, tags: list = None, severity: str = "normal",
    related_docs: list = None, metrics: dict = None) -> dict:
    body = {
        "title": title, "scenario": scenario, "category": category,
        "problem": problem, "solution": solution, "result": result,
        "key_lessons": key_lessons or [], "tags": tags or [],
        "severity": severity, "related_docs": related_docs or [],
        "metrics": metrics or {},
    }
    return await self._post_backend_json(f"/api/v1/experience/{kb_id}", body)

async def experience_read(self, kb_id: str, exp_id: str) -> dict:
    return await self._get_backend(f"/api/v1/experience/{kb_id}/{exp_id}")

async def experience_list(self, kb_id: str, scenario: str = "",
    category: str = "", tag: str = "") -> dict:
    params = {}
    if scenario: params["scenario"] = scenario
    if category: params["category"] = category
    if tag: params["tag"] = tag
    return await self._get_backend(f"/api/v1/experience/{kb_id}", **params)

async def experience_update(self, kb_id: str, exp_id: str, **kwargs) -> dict:
    return await self._put_backend_json(f"/api/v1/experience/{kb_id}/{exp_id}", kwargs)

async def experience_delete(self, kb_id: str, exp_id: str) -> dict:
    return await self._request("DELETE", f"/api/v1/experience/{kb_id}/{exp_id}",
                               base=self.backend_url)

# ── 经验操作 ──

async def experience_apply(self, kb_id: str, exp_id: str, user: str = "",
    context: str = "", result: str = "", notes: str = "") -> dict:
    body = {"user": user, "context": context, "result": result, "notes": notes}
    return await self._post_backend_json(
        f"/api/v1/experience/{kb_id}/{exp_id}/apply", body)

async def experience_review(self, kb_id: str, exp_id: str,
    reviewer: str = "", rating: float = 5.0, comment: str = "") -> dict:
    body = {"reviewer": reviewer, "rating": rating, "comment": comment}
    return await self._post_backend_json(
        f"/api/v1/experience/{kb_id}/{exp_id}/review", body)

async def experience_summary(self, kb_id: str) -> dict:
    return await self._get_backend(f"/api/v1/experience/{kb_id}/summary")
```

### 6.2 MCP 工具 (server.py — 标签块)

```python
# ============================================================
# EXPERIENCE MANAGEMENT — 经验管理（CRUD + 操作 + 搜索）
# ============================================================

@mcp.tool()
async def experience_create(kb_id: str, title: str, scenario: str = "",
    category: str = "tip", problem: str = "", solution: str = "",
    result: str = "success", key_lessons: list = None, tags: list = None,
    severity: str = "normal", related_docs: list = None) -> str:
    """创建一条经验记录。
    
    经验是实践总结的可复用知识，比文档多了评分、应用记录、场景绑定等维度。
    Args:
        kb_id: 知识库 ID 或路径
        title: 经验标题
        scenario: 场景标识（如 "coal-mill-fault-prediction"）
        category: 类别（best_practice/troubleshooting/lesson_learned/optimization/tip/workflow/decision）
        problem: 要解决的问题描述
        solution: 解决方案
        result: 结果（success/partial/failed/inconclusive）
        key_lessons: 关键教训列表（最重要的可执行条目）
        tags: 标签列表
        severity: 严重程度（critical/important/normal/tip）
        related_docs: 关联文档路径列表
    """
    return _j(await _client().experience_create(
        kb_id, title, scenario, category, problem, solution, result,
        key_lessons, tags, severity, related_docs
    ))

@mcp.tool()
async def experience_read(kb_id: str, exp_id: str) -> str:
    """读取一条经验的元数据和内容。
    Args:
        kb_id: 知识库 ID 或路径
        exp_id: 经验 ID（如 "exp-coal-mill-001"）
    """
    return _j(await _client().experience_read(kb_id, exp_id))

@mcp.tool()
async def experience_list(kb_id: str, scenario: str = "",
    category: str = "", tag: str = "") -> str:
    """列出知识库中的经验，支持按场景/类别/标签过滤。按评分排序。
    Args:
        kb_id: 知识库 ID 或路径
        scenario: 可选，场景过滤
        category: 可选，类别过滤
        tag: 可选，标签过滤
    """
    return _j(await _client().experience_list(kb_id, scenario, category, tag))

@mcp.tool()
async def experience_update(kb_id: str, exp_id: str, title: str = "",
    scenario: str = "", category: str = "", problem: str = "",
    solution: str = "", result: str = "", key_lessons: list = None,
    tags: list = None, severity: str = "", status: str = "",
    related_docs: list = None) -> str:
    """更新一条经验记录。提供要更新的字段即可。
    Args:
        kb_id: 知识库 ID 或路径
        exp_id: 经验 ID
        status: 状态（draft/published/archived）
    """
    return _j(await _client().experience_update(
        kb_id, exp_id, title=title, scenario=scenario, category=category,
        problem=problem, solution=solution, result=result,
        key_lessons=key_lessons, tags=tags, severity=severity,
        status=status, related_docs=related_docs
    ))

@mcp.tool()
async def experience_delete(kb_id: str, exp_id: str) -> str:
    """永久删除一条经验。
    Args:
        kb_id: 知识库 ID 或路径
        exp_id: 经验 ID
    """
    return _j(await _client().experience_delete(kb_id, exp_id))

@mcp.tool()
async def experience_apply(kb_id: str, exp_id: str, user: str = "",
    context: str = "", result: str = "", notes: str = "") -> str:
    """标记一条经验被应用，记录使用者和效果。
    Args:
        kb_id: 知识库 ID 或路径
        exp_id: 经验 ID
        user: 使用者标识
        context: 应用场景描述
        result: 应用结果（success/partial/failed）
        notes: 备注
    """
    return _j(await _client().experience_apply(kb_id, exp_id, user, context, result, notes))

@mcp.tool()
async def experience_review(kb_id: str, exp_id: str, reviewer: str = "",
    rating: float = 5.0, comment: str = "") -> str:
    """评审一条经验，评分并留下评论。
    Args:
        kb_id: 知识库 ID 或路径
        exp_id: 经验 ID
        reviewer: 评审人
        rating: 评分 (0-5)
        comment: 评审意见
    """
    return _j(await _client().experience_review(kb_id, exp_id, reviewer, rating, comment))

@mcp.tool()
async def experience_find_by_scenario(kb_id: str, scenario: str) -> str:
    """按场景查找经验，返回匹配的经验列表（按评分排序）。
    这是经验检索的核心入口——Agent 应该优先使用场景来定位经验。
    Args:
        kb_id: 知识库 ID 或路径
        scenario: 场景标识（如 "coal-mill-fault-prediction"）
    """
    return _j(await _client().experience_list(kb_id, scenario=scenario))

@mcp.tool()
async def experience_summary(kb_id: str) -> str:
    """获取经验统计摘要：总经验数、按类别分布、最常用经验、评分等。
    Args:
        kb_id: 知识库 ID 或路径
    """
    return _j(await _client().experience_summary(kb_id))
```

---

## 七、Skill 设计

### 7.1 `knowledge-experience` Skill

创建 `.claude/skills/knowledge-experience/SKILL.md`:

```markdown
---
name: knowledge-experience
description: >
  经验管理系统 — 记录/检索/应用经验。经验是实践总结的可复用知识，
  有评分、应用记录、场景绑定。用于故障排查、最佳实践、经验教训的
  动态管理和检索。Invoked by Archival 或用户直接请求。
---

# Knowledge Experience — 经验管理系统

## 触发场景
- 用户说"记录一个经验""保存这个操作经验""记住这个教训"
- 用户说"查一下有没有这方面的经验""这种情况以前怎么处理的"
- 用户说"这个经验有用/没用"、"给这个经验评分"
- 用户说"总结一下这个场景的经验"

## 经验管理流程

### E1 — 记录经验
1. 识别当前作业场景（scenario）
2. 引导用户或自动填写: 问题→方案→结果→关键教训→标签
3. 调用 `experience_create` 保存
4. 自动调用 `kb_index_document` 对经验正文建向量索引

### E2 — 检索经验
1. 解析用户问题的场景/技术关键词
2. 调用 `experience_find_by_scenario` 按场景匹配
3. 无场景匹配→遍历所有经验元信息搜索
4. 按 rating_avg + applied_count 排序返回
5. 需要详细内容→ `experience_read` 读取元数据 + 全文

### E3 — 应用经验
1. 找到匹配经验后记录应用
2. 调用 `experience_apply` 记录使用者和效果

### E4 — 评审经验
1. 对使用过的经验邀请评分
2. 调用 `experience_review` 记录评审

### E5 — 关联经验与文档
在知识检索（knowledge-search）的 G3 City 阶段：
判断文档内容→是否有相关经验？
有 → 一并返回
```

### 7.2 在 Archival agent 中添加引用

```yaml
# .claude/agents/knowledge-admin.md skills 中新增
skills:
  - knowledge-experience
  # ... 原有 skills
```

### 7.3 在 `knowledge-search` SKILL.md 中集成钩子

在 S-Street 阶段后增加 Experience 阶段：

```
├─ Globe     （看所有KB）
├─ Region    （定位候选KB）
├─ City      （读摘要确认）
├─ Street    （向量精排）
├─ 🆕 Experience  （检索该场景下的经验）  ← 新增
│   调用 experience_find_by_scenario(scenario)
│   匹配度 + 评分双重排序
└─ A4 Assembly（综合回答+经验建议）
```

---

## 八、实现步骤

### Phase 1: 后端存储 + API (2天)

| Step | 文件 | 说明 | 验收标准 |
|:----:|------|------|---------|
| 1.1 | `backend/app/models/experience_models.py` | Pydantic 模型（8个类） | 所有模型可导入使用 |
| 1.2 | `backend/app/services/experience_service.py` | ExperienceService 类含 init/create/read/list/update/delete/apply/review/search | 完整 CRUD 逻辑 |
| 1.3 | `backend/app/api/routes/experience.py` | 9 个路由端点 | curl 测试所有端点 |
| 1.4 | `backend/app/api/routes/__init__.py` | 导出 experience_router | — |
| 1.5 | `backend/app/main.py` | 注册 experience_router | — |

### Phase 2: MCP 层 (1天)

| Step | 文件 | 说明 | 验收标准 |
|:----:|------|------|---------|
| 2.1 | `kb-mcp/kb_client/client.py` | 添加 10 个 experience_* 方法 | Mock 客户测试 |
| 2.2 | `kb-mcp/server.py` | 添加 10 个 @mcp.tool() 定义 | MCP 客户端可调用 |

### Phase 3: 自动初始化和 Nuxt 代理 (1天)

| Step | 文件 | 说明 | 验收标准 |
|:----:|------|------|---------|
| 3.1 | `web/server/api/experience/[kbId]/init.post.ts` | 初始化代理 | — |
| 3.2 | `web/server/api/experience/[kbId]/index.get.ts` | 列表代理 | — |
| 3.3 | `web/server/api/experience/[kbId]/index.post.ts` | 创建代理 | — |
| 3.4 | `web/server/api/experience/[kbId]/[expId].get.ts` | 读取代理 | — |
| 3.5 | `web/server/api/experience/[kbId]/[expId].put.ts` | 更新代理 | — |
| 3.6 | `web/server/api/experience/[kbId]/[expId].delete.ts` | 删除代理 | — |
| 3.7 | `web/server/api/experience/[kbId]/[expId]/apply.post.ts` | 应用代理 | — |
| 3.8 | `web/server/api/experience/[kbId]/[expId]/review.post.ts` | 评审代理 | — |

### Phase 4: Skill 集成 (0.5天)

| Step | 文件 | 说明 | 验收标准 |
|:----:|------|------|---------|
| 4.1 | `.claude/skills/knowledge-experience/SKILL.md` | 经验管理 Skill | Skill 完整可用 |
| 4.2 | `.claude/agents/knowledge-admin.md` | 添加 skills 引用 | — |

### Phase 5: 测试 (0.5天)

| Step | 测试 | 说明 |
|:----:|------|------|
| 5.1 | `kb_create` 自动初始化 experience 文件夹 | 新建 KB → 自动创建 |
| 5.2 | `experience_create` → `experience_list` → `experience_read` | 完整 CRUD 链路 |
| 5.3 | `experience_apply` + `experience_review` | 操作功能 |
| 5.4 | 经验 search | 搜索 |
| 5.5 | 大 KB 经验场景 | 边界：100 条经验 |
| 5.6 | 经验跨 KB 搜索 | 跨 KB |
| 5.7 | 删除 KB 时清理经验 | 清理 |

---

## 九、关键设计决策与风险

### 设计决策

| # | 决策 | 理由 |
|:-:|------|------|
| 1 | 经验存储在独立目录 experience/，不混入文档 | 职责分离，易于独立管理 |
| 2 | 使用 `.experience-index.yml` 作元数据索引 | 同 .knowledge-base.yml 一致的设计哲学 |
| 3 | MCP 工具 10 个（不压缩到 2-3 个） | 每个工具有明确职责，Agent 可精细操作 |
| 4 | 经验走 Backend API（不直接文件读写） | 一致的数据访问控制、可扩展 |
| 5 | category 使用 Enum（6 种） | 避免分类混乱，便于统计 |
| 6 | 经验创建时自动 `kb_index_document` | 经验立即可向量搜索 |
| 7 | `kb_create` 时自动 `experience_init` | 零配置初始化 |

### 风险与缓解

| # | 风险 | 缓解措施 |
|:-:|------|---------|
| 1 | 经验索引与文件不同步 | 同文档体系的双写模式，操作后立即刷新索引 |
| 2 | 经验过多导致查询慢 | 索引有场景/类别/标签过滤字段，按需加载 |
| 3 | 经验与文档关联弱 | 通过 related_docs 字段硬链接，向量搜索可联合 |
| 4 | 删除 KB 时经验残留 | 实现级联删除：`kb_delete` 同时删除 experience/ |
| 5 | 路径缓存刷新延迟 | 同现有文件系统 - reloadMetadata() 机制 |

---

## 十、验收标准

### 必须通过

| # | 验收项 | 验证方式 |
|:-:|--------|---------|
| A1 | 新建 KB 自动创建 experience/ 文件夹 | `fs_get_tree` 可看到 |
| A2 | 创建经验 → 索引文件正确写入 | 查看 `.experience-index.yml` |
| A3 | 创建经验 → .md 文件正确写入 | `preview_file` 可读 |
| A4 | 经验元信息完整 | id/title/scenario/category/severity/tags/key_lessons 全部填写 |
| A5 | 经验列表按评分排序 | rating_avg 高的在前 |
| A6 | 经验应用记录 | applied_count 增加 |
| A7 | 经验评审 | rating_avg 更新正确 |
| A8 | 经验场景检索 | `experience_find_by_scenario` 返回匹配结果 |
| A9 | 不破坏现有文档 | 已有文档全部正常 |
| A10 | 删除 KB 删除经验文件 | experience/ 目录被删除 |

### 非目标

- 不实现经验向量搜索（Phase 6 规划，依赖现有 `kb_index_document`）
- 不实现前端经验管理页面（MVP 只做 API + MCP + Skill）

---

## ADR

| 项目 | 内容 |
|------|------|
| **Decision** | 采用独立 experience/ 存储 + 10 个 MCP 工具 + 独立 Skill |
| **Drivers** | D1 (可复用性=价值), D2 (场景=第一索引), D3 (结构化元数据) |
| **Alternatives** | Option B: 复用文档体系（被否决，数据混杂） |
| **Why chosen** | 职责清晰，经验有独立的生命周期和评分体系 |
| **Consequences** | 维护 10 个新工具的成本，但每个工具职责单一 |
| **Follow-ups** | 经验向量搜索、经验前端 UI、跨库经验聚合 |
