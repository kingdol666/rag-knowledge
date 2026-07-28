# Plan: Experience Auto-Meditation System v3.0 🧘

**Status:** pending approval | **Date:** 2026-07-28 | **Estimated effort:** 10 days | **Risk tier:** MEDIUM-HIGH
---

## Requirements Summary

构建**生产级经验自动沉淀系统**，核心设计理念：**每条经验就是一个 Skill**——结构化、可执行、可检索、持续进化。

### 用户需求（精确映射）

| # | 需求 | 实现方案 |
|---|------|---------|
| 1 | **前端 KB 级冥想管理** | `knowledge-base.vue` 设置面板，每个 KB 独立开关/配置 |
| 2 | **冥想设置随元数据移动** | `metadata.meditation` 存入 `.knowledge-base.yml`，随 KB 文件夹移动 |
| 3 | **Claude Code / OMP 作为 Harness** | 后端 spawn `claude -p` 或 `omp -p` 子进程（MinerU 同款 Job Object 生命周期） |
| 4 | **默认 OMP，可自定义 Harness** | KB 配置 `harness: "omp"\|"claude"\|"heuristic"`，默认 `"omp"` |
| 5 | **自定义冥想间隔 + 开关** | `interval_hours`, `enabled` 存在 KB YAML metadata |
| 6 | **自动冥想 = 定时总结** | 后台 scheduler 按 KB 配置周期 spawn agent 子进程 |
| 7 | **手动总结 = 调用 Skill** | 用户说"总结经验" → Archival agent 调 `knowledgebase-experience-summarize`（现有机制） |
| 8 | **经验按 Skill 模板创建** | Agent prompt 嵌入 quality-standards.md + SKILL.md 规范，产出严格格式 |
| 9 | **增删改查 + 持续进化** | 现有 CRUD + apply/review 可信度升降级 + vetted 升级 + stale 检测 + decay |
| 10 | **综合对话信号生成最佳经验** | meditation_signals 表捕获 Q&A + retrieved_docs + feedback → agent context |

---

## Architecture: Agent-Harness Meditation Model

### 核心洞察：后端不调 LLM，Spawn Agent Harness

**不采用** "后端 httpx 直调 Anthropic API" 方案，而是：

```
后端 Scheduler（机械）
  │
  ├─ harvest → cluster → score → per-KB filter（全部机械，无 LLM）
  │
  └─ 当某 KB 有合格 cluster 待合成：
       │
       ▼
  spawn Agent Harness 子进程（MinerU 模式）
       │
       ├─ claude -p --dangerously-skip-permissions \
       │   --mcp-config .mcp.json \
       │   --system-prompt-file prompts/meditation_agent_system.txt \
       │   --max-budget-usd 0.05 \
       │   "<task prompt with signals/docs/existing experiences>"
       │
       └─ Agent 内部自动：
           ├─ 读 KB 文档（MCP 工具 kb_doc_read）
           ├─ 检已有经验（experience_search_smart）
           ├─ 按 SKILL.md 规范提炼经验
           ├─ quality-standards.md 质量门控
           └─ 调 MCP 工具 experience_create / save_draft 持久化
```

**为什么这个架构最优？**
1. **复用所有现有基础设施**：kb-mcp 的 20 个经验工具、skill 规范、质量门控、Archival agent 的全部能力——不需要在后端重写任何 LLM 逻辑
2. **零 API key 管理**：agent 子进程使用用户已有的 Claude Code / OMP 认证（OAuth/API key/env），后端永远不接触 API key
3. **经验质量 = 人工总结质量**：agent 执行的就是 `knowledgebase-experience-summarize` skill 本身（同一套 prompt、同一套质量门控），不是后端重写的缩水版
4. **进程级隔离**：agent 崩溃/超时/超预算不影响后端（MinerU Job Object 模式已有成熟的生命周期管理）
5. **Harness 可插拔**：claude 和 omp 只是 `subprocess.Popen` 的不同 executable + flags
6. **MCP 工具自动可用**：通过 `--mcp-config .mcp.json`，agent 子进程连上 kb-mcp，直接调用全部 66 个工具

### 双层运行模式

| 模式 | 触发者 | 流程 | 用途 |
|------|--------|------|------|
| **🧘 自动冥想** | 后端 scheduler（定时/增量） | spawn `claude/omp -p` → agent 读 signals + docs → 按 SKILL.md 提炼 → save_draft/experience_create | 定期沉淀高频问题 |
| **✋ 手动总结** | 用户对话 | Archival agent（当前会话内） → 调 `knowledgebase-experience-summarize` skill | 特定场景经验 |

> 两者底层**用同一套 skill 规范和质量门控**，区别只是 agent 运行在 scheduler 子进程 vs 用户会话。

### 🧘 经验 = Skill：哲学与格式

**核心设计理念：每条自动生成的经验，其质量和结构等同于一个手写的 Skill。**

经验的 Markdown 正文采用**类 SKILL.md 格式**，具备：

1. **YAML Frontmatter**（用于向量索引和检索元数据）：
   ```yaml
   ---
   id: exp-a1b2c3d4e5f6
   title: "MCP 启动失败排查"
   scenario: mcp-startup-connection-failed
   category: troubleshooting
   severity: critical
   tags: [mcp, startup, connection, debug]
   kb: 高分子双拉加工
   auto_extracted: true
   harness: omp
   confidence: 0.85
   vetted: false
   created_at: 2026-07-28T03:00:00Z
   applied_count: 0
   rating_avg: 0.0
   ---
   ```

2. **结构化步骤章节**（类似 Skill 的 Step 流程）：
   ```markdown
   # MCP 启动失败：kb-mcp 连接被拒

   ## 触发场景
   重启 Claude Code 后，调用 mcp__kb-mcp__* 工具返回 "No such tool available"。

   ## 诊断步骤
   1. 运行 `backend_status` 检测 MCP 连通性
   2. 若 MCP 不可用 → `curl -s http://localhost:8765/api/v1/health` 检查后端
   3. 检查 `.mcp.json` 配置：`uv run --directory kb-mcp python server.py`
   ...

   ## 解决方案
   ```bash
   # 1. 检查后端健康
   curl http://localhost:8765/api/v1/health
   # 2. 重启 kb-mcp
   cd kb-mcp && start "kb-mcp" uv run python server.py
   ```

   ## 关键教训（可独立引用）
   - **MCP 工具不可用 ≠ 后端挂了**：先检查 `.mcp.json` 路径格式
   - **stdout 管道是罪魁祸首**：MinerU 子进程 stdout → log file，不能用 PIPE
   - **Windows Job Object 保证无孤儿**：后端 crash 时子进程自动被杀

   ## 关联文档
   - 📄 kb-mcp/server.py
   - 📄 docs/ARCHITECTURE.md#mcp-layer
   ```

3. **持续进化机制**（经验的"可信度"类似 Skill 的使用反馈）：
   - `apply` → 被成功采纳（类似"这个 Skill 帮到了你"）→ applied_count++
   - `review` → 评分（1-5）+ 评论 → rating_avg 更新
   - vetted=False → apply≥2 + rating≥4.0 → vetted=True（"经验经过实战验证"）
   - decay 机制 → 过时经验自动降级

> 这样设计的好处：经验不只是"一段笔记"，而是一个**微型的、可被 Agent 直接执行的 Skill**。
> Agent 检索到经验时，看到的是结构化的场景→诊断→方案→教训，而非散文式笔记。

---

## RALPLAN-DR Summary

### Principles (7)

1. **后端永远机械，Agent 永远智能** — 后端不调任何 LLM API；所有"思考"由 spawn 的 agent 子进程完成
2. **Agent Harness 用成熟的 CLI 模式** — `claude -p` / `omp -p` 都是官方支持的 non-interactive 模式，有 `--max-budget-usd`、`--auto-approve`/`--dangerously-skip-permissions`、`--output-format json`
3. **进程生命周期严格管控** — 复用 MinerU 的 Job Object（Win）/ prctl（Linux）模式，子进程必须随后端退出而死亡，不残留孤儿
4. **经验质量不打折** — agent prompt 嵌入完整 SKILL.md + quality-standards.md，产出与人工总结同标准
5. **零 API key 泄漏面** — 后端从不接触/存储/传递 API key；子进程继承用户环境的认证
6. **优雅降级链** — Harness 不可用（claude/omp 未安装/认证失败）→ 启发式 fallback（现有机械草稿生成）
7. **配置随 KB 生命周期** — meditation 配置存 `.knowledge-base.yml` metadata，移动/合并/迁移自动跟随

### Decision Drivers (top 5)

1. **复用最大化** — 不重写 LLM 逻辑，直接用 Claude Code/OMP 作为 reasoning engine
2. **KB 级独立控制** — 每个 KB 可自选 harness（omp/claude）、间隔、开关、模型
3. **24/7 自主运行** — 无用户会话时后端 scheduler 也能 spawn agent
4. **成本安全** — `--max-budget-usd` 硬上限（默认 $0.05/次）+ 进程超时（默认 10 分钟）+ max 1 次并发
5. **经验 = Skill 质量** — 所有生成经验必须通过 quality-standards.md 完整性检查清单

### Viable Options Considered

#### Option A: 后端 httpx 直调 Anthropic API
- 后端写 LLM 调用逻辑，需要管理 API key/cost/重试/timeout
- ❌ 违反"后端机械"原则；❌ 需要重写 SKILL.md 质量门控逻辑（重复劳动且质量打折）；❌ API key 管理面扩大
- **Rejected**

#### Option B: Agent Harness 子进程（MinerU 模式）⭐ RECOMMENDED
- 后端 spawn `claude -p` / `omp -p`，传入 MCP 配置 + system prompt + task prompt
- Agent 自主调用 kb-mcp 工具读文档/写经验，执行完整 skill 流程
- ✅ 复用全部现有 skill/MCP 工具/质量门控；✅ 零 API key 管理；✅ 进程隔离；✅ harness 可插拔
- **Chosen**

#### Option C: MCP/Agent 层轮询合成（无后端主动 spawn）
- 后端只暴露待合成 queue，等用户会话内的 Archival agent 轮询
- ❌ 无会话时不工作，违自主性要求
- **Rejected**

---

## Pre-Mortem (5 Failure Scenarios)

| # | Scenario | Likelihood | Mitigation |
|---|----------|------------|------------|
| 1 | **Agent 子进程挂起/僵尸** | Medium | 硬超时 600s（`asyncio.wait_for`）→ terminate → job object kill；stdout→log file（非 pipe） |
| 2 | **Agent 认证失败/OAuth 过期** | Medium | 启动时 pre-flight `claude --version` / `omp --version` 检查；失败 3 次 circuit breaker 24h；降级启发式 |
| 3 | **Agent 不遵守格式/产出乱码** | Low | Task prompt 强制 JSON 输出 + `--output-format json`；parse 失败 → 丢弃原始输出至 rejected 日志 |
| 4 | **成本失控（循环 tool 调用）** | Low | `--max-budget-usd 0.05`（claude）/ OMP 用模型上限；进程 10min 超时；max_drafts_per_run=3 |
| 5 | **并发 spawn 过多导致系统卡顿** | Low | 全局 asyncio.Semaphore(2) + KB 级锁；同一 KB 不并发；spawn 前检查资源 |

---

## Data Model

### KB Meditation Config（存入 YAML metadata）

```yaml
# .knowledge-base.yml
knowledge_base:
  id: "<uuid>"
  name: "..."
  metadata:
    meditation:
      enabled: false                     # 开关
      harness: "omp"                     # "omp" | "claude" | "heuristic"（默认 omp）
      model: ""                          # 空=用 harness 默认；可指定 "opus"/"sonnet"/"gpt-5"
      interval_hours: 24                 # 运行间隔
      min_cluster_count: 2               # 最小问题簇大小
      max_drafts_per_run: 3              # 每次运行最多生成
      auto_publish: false                # true=质量≥7直接发布(vetted=False); false=全部进草稿池
      max_budget_usd: 0.05              # 单次 agent 运行成本上限
      timeout_sec: 600                   # agent 进程超时（秒）
      last_run_at: null                  # ISO8601
      last_run_status: null              # "success" | "failed" | "timeout"
      last_run_report: {}                # 上次运行摘要
      total_runs: 0                      # 累计运行次数
      total_experiences_generated: 0     # 累计生成经验数
      incremental_enabled: true          # 信号积累到阈值立即触发（不等周期）
      created_at: "..."
      updated_at: "..."
```

**迁移策略**：所有字段有默认值，旧 YAML 加载时自动填充。

### Experience 模型扩展

```python
# backend/app/models/experience_models.py
class ExperienceCreate(BaseModel):
    # ... 现有字段 ...
    # 冥想来源追踪（自动填充，用户不可见）
    auto_extracted: bool = False
    harness: str = ""                    # "omp" | "claude" | "manual" | "heuristic"
    confidence: float = 1.0              # agent 自评 + 规则门控分
    source_questions: list[str] = []     # 来源问题
    source_cluster_count: int = 0
    vetted: bool = True                  # 自动生成默认 False
    meditation_run_id: str = ""
```

### 信号与运行记录表

```sql
-- web/server/utils/chat-db.ts
CREATE TABLE IF NOT EXISTS meditation_signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  kb_id TEXT NOT NULL,
  question_text TEXT NOT NULL,
  retrieved_docs TEXT DEFAULT '[]',   -- JSON [{path, score, kb_id}]
  assistant_answer TEXT,
  resolved INTEGER DEFAULT 0,
  user_feedback INTEGER DEFAULT -1,   -- -1 none, 0 down, 1 up
  experience_derived INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_signals_kb ON meditation_signals(kb_id, experience_derived);

CREATE TABLE IF NOT EXISTS meditation_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kb_id TEXT NOT NULL,
  harness TEXT NOT NULL,              -- "omp" | "claude" | "heuristic"
  trigger TEXT DEFAULT 'scheduled',   -- scheduled|manual|incremental
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT DEFAULT 'running',      -- running|completed|failed|timeout
  pid INTEGER,                        -- 子进程 PID
  exit_code INTEGER,
  cost_usd REAL DEFAULT 0,
  experiences_created INTEGER DEFAULT 0,
  drafts_created INTEGER DEFAULT 0,
  signals_processed INTEGER DEFAULT 0,
  report_json TEXT DEFAULT '{}',
  error TEXT,
  agent_stdout_tail TEXT              -- 最后 500 字符（调试用）
);
```

---

## Implementation Steps

### Phase 0: 地基 + Bug 修复 + KB 配置模型（~1.5 days）

#### 0.1 修复去重 bug（CRITICAL）
**File:** `backend/app/services/experience_meditation_service.py:468`
- `e.get("_score", 0) > 0.6` 永远 False → 从 `search_experiences()` 返回值正确提取 score
- 单元测试覆盖

#### 0.2 修复 decay_flag 未接入 search
**File:** `backend/app/services/experience_service.py`
- `search_experiences_global()` 的 `_tier_experience()` 后应用 decay penalty：
  - `stale_unverified`: vector_score × 0.7
  - `disputed`: cap P2
- 同 tier 内无 decay 优先排序

#### 0.3 消除双重降级循环
**File:** `kb-mcp/server.py:1067-1089`
- 删除 MCP 层 `experience_search_smart` 外层 3 轮循环，单次调用透传

#### 0.4 并发锁替换
**File:** `backend/app/services/experience_meditation_service.py:256`
- `self._running: bool` → `self._lock = asyncio.Lock()` + KB 级锁 dict

#### 0.5 Event loop 非阻塞化
- `vector_service.search()`（BGE-M3 同步推理）→ `run_in_executor`
- `sqlite3.connect()` → `run_in_executor`

#### 0.6 ⭐ KB 冥想配置模型
**Files:**
- `web/types/knowledge-base-yaml.ts` — 新增 `MeditationConfig` interface
- `web/server/services/knowledge-base-yaml-service.ts` — `getMeditationConfig()` / `updateMeditationConfig()`
- `backend/app/services/experience_service.py` — `_get_kb_meditation_config(kb_path)` 读取 YAML metadata
- 默认值：`enabled=false, harness="omp", interval_hours=24, max_budget_usd=0.05`
- 所有现有 KB 自动获得默认配置（向后兼容）

#### 0.7 Experience 模型扩展
**File:** `backend/app/models/experience_models.py`
- 添加 auto_extracted/harness/confidence/source_questions/vetted/meditation_run_id 字段（全部默认值）
- create_experience 写入逻辑传递新字段
- approve_draft 时从 draft 复制 harness/auto_extracted 等字段
- 旧 YAML 经验加载无 KeyError

#### 0.8 ⭐ 经验 Markdown 格式升级（Skill-like）
**File:** `backend/app/services/experience_service.py` `_generate_markdown()`
- 升级 Markdown 生成逻辑，产出**类 SKILL.md 格式**：
  - YAML frontmatter（id/title/scenario/category/severity/tags/auto_extracted/harness/confidence/vetted/...）
  - 章节：触发场景 / 诊断步骤 / 解决方案 / 关键教训 / 关联文档
  - 教训用**加粗小标题 + 可独立引用**的格式
  - 方案部分：多行步骤/代码块，保持可执行性
- 旧经验不强制迁移；新经验（含自动生成）使用新格式
- 读取时兼容旧格式（`_parse_experience_md` 容错）
- Agent system prompt 要求按此格式组织 solution 章节

#### 0.9 后端信号/运行记录表 API
**File:** `backend/app/services/meditation_db.py`（新建，复用 chat-db.ts 的 SQLite 连接或独立 meditation.db）
- 独立 SQLite `storage/meditation.db`（避免与 chat DB 耦合锁）
- CRUD 函数：save_signal, get_pending_signals, mark_signals_derived, create_run, update_run, list_runs
- WAL mode，跨进程安全

**Phase 0 验收：**
- [ ] 4 个 bug 全部修复，单元测试通过
- [ ] KB 冥想配置读写正确，默认值填充，YAML 持久化
- [ ] KB move 后 YAML metadata.meditation 完好
- [ ] Experience 新字段向后兼容，旧经验加载正常

---

### Phase 1: 信号采集 + KB 感知调度（~1.5 days）

#### 1.1 Post-hoc 信号提取
**File:** `backend/app/services/experience_meditation_service.py`
- 重写 `harvest_questions()` → `harvest_signals(db_path, kb_filter)`：
  - 读 messages 表，解析 tool_use/tool_result（匹配 `mcp__kb-mcp__kb_search*` / `kb_doc_read`）
  - 从 tool 参数提取 `kb_id`，从 result 提取 `doc_path`/`score`
  - 提取 follow-up assistant answer 文本
  - 判断 resolved（后续用户消息无追问模式）
  - 按 KB 分组写入 `meditation_signals` 表
- **不修改 chat.post.ts**（post-hoc 解析，零侵入）

#### 1.2 Scheduler KB 感知改造
- `run_meditation_now()` 改为按 KB 遍历：
  ```python
  for kb in catalog:
      kb_cfg = _get_kb_meditation_config(kb.path)
      if not kb_cfg.enabled: continue
      if not _is_due(kb_cfg, kb_last_run): continue
      await _meditate_kb(kb, kb_cfg)  # Phase 2 spawns agent
  ```
- 全局 `experience_auto.enabled` 是 master switch
- 返回 per-KB 报告

#### 1.3 增量触发
- 新 signal 写入时检查：该 KB 该 cluster 计数 ≥ min_cluster_count + score ≥ 1.5
- 触发 fire-and-forget `_meditate_kb(kb, kb_cfg, incremental=True)`
- 标记相关 signals 的 `experience_derived=1`

#### 1.4 反馈 API
**File:** `backend/app/api/routes/meditation.py`
- `POST /api/v1/meditation/feedback` → 更新 signal feedback
- `GET /api/v1/meditation/signals?kb_id=X&days=N`
- `GET /api/v1/meditation/history?kb_id=X`
- `POST /api/v1/meditation/run?kb_id=X` — 手动触发

#### 1.5 前端 👍👎 + 保存经验
**File:** `web/pages/claude-chat.vue`
- assistant 消息下方 👍👎 按钮
- "💡 保存为经验" Modal → 预填 Q/A/文档 → 提交调 `experience_create`

**Phase 1 验收：**
- [ ] KB-enhanced 对话后 signals 表有正确的 kb_id/retrieved_docs/answer
- [ ] Scheduler 正确跳过 disabled KB
- [ ] 同类问题积累到阈值触发增量冥想（不等周期）
- [ ] 👍👎 持久化，保存经验正常工作

---

### Phase 2: ⭐ Agent Harness 子进程引擎（~3 days）CORE

#### 2.1 AgentHarnessManager（MinerU 模式）
**File:** `backend/app/services/agent_harness_manager.py`（新建 ~350 行）

```python
class AgentHarnessManager:
    """Spawn Claude Code / OMP as subprocesses for LLM synthesis.

    Design mirrors MinerU manager:
    - Windows: Job Object KILL_ON_JOB_CLOSE (no orphans)
    - Linux: prctl(PR_SET_PDEATHSIG)
    - stdout/stderr → log file (never PIPE)
    - Hard timeout + budget cap
    - Global concurrency semaphore
    """

    async def synthesize_experiences(
        self,
        kb_path: str,
        kb_id: str,
        signals: list[dict],      # harvested signals for this KB
        kb_config: dict,           # meditation config
        trigger: str = "scheduled",
    ) -> dict:
        """Spawn agent to synthesize experiences from signals.

        Returns {"success": True/False, "experiences": [...], "drafts": [...], "error": ...}
        """
```

**关键设计：**

1. **Harness 检测与命令构建**（基于实测 CLI flags）：
   ```python
   HARNESS_CONFIG = {
       "omp": {
           "exe": "omp",  # C:\Users\87287\.bun\bin\omp.exe (v17.1.5)
           "args": lambda cfg, prompt_file: [
               "-p",
               "--auto-approve",
               "--no-session",
               "--mode=json",
               "--max-time", str(cfg.get("timeout_sec", 600)),
               "--cwd", PROJECT_ROOT,
               "--model", cfg.get("model", "sonnet"),
               # OMP 原生支持 @file 语法包含文件内容
               f"@{prompt_file}",
           ],
           # OMP 自动发现 .mcp.json + skills；无需 --mcp-config
           # 用 --max-time 做硬超时（比 asyncio.wait_for 更可靠）
           "stdin_needed": False,
       },
       "claude": {
           "exe": "claude",  # C:\Users\87287\.local\bin\claude.exe (v2.1.220)
           "args": lambda cfg, prompt_file: [
               "-p",
               "--output-format", "json",
               "--model", cfg.get("model", "claude-sonnet-4-20250514"),
               "--max-budget-usd", str(cfg.get("max_budget_usd", 0.05)),
               "--dangerously-skip-permissions",
               "--no-session-persistence",
               # --bare: 跳过 hooks/LSP/插件/auto-memory,
               # auth 严格用 ANTHROPIC_API_KEY env（避免 OAuth popup 卡住子进程）
               "--bare",
               "--mcp-config", MCP_CONFIG_PATH,  # 显式传入 kb-mcp
               "--add-dir", PROJECT_ROOT,        # bare 模式需显式声明工作目录
               # system prompt 通过 --system-prompt-file 传入
               "--system-prompt-file", SYSTEM_PROMPT_PATH,
               # 强制输出 JSON schema，防止格式跑偏
               "--json-schema", json.dumps(RESULT_SCHEMA),
           ],
           # 注意: claude 不用 @file; task prompt 通过 stdin pipe 传入
           # cwd 在 subprocess Popen 中设置
           "stdin_needed": True,
       },
       "heuristic": {
           # No subprocess — use existing mechanical extraction
       },
   }
   ```
   > **实测验证**：`echo "say hello" | claude -p --bare` 可用；omp 支持 `@file` 语法。
   > OMP 自动发现 `.mcp.json`，无需 `--mcp-config`；claude `--bare` 模式必须显式传。

2. **进程启动（MinerU Job Object 复用 + ragctl 经验）**：
   ```python
   # 关键经验（来自 mineru_manager.py + ragctl.js）：
   # - 禁止 shell=True（Windows 破坏 fd 继承，log 文件空白）
   # - Windows 命令无扩展名需补 .exe
   # - stdout→log 文件（不是 PIPE），防止 [Errno 22]
   # - 子进程 stdin: claude 写 prompt 后关闭（EOF 触发执行）；omp 不用 stdin
   # - Windows: CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP（不用 DETACHED，
   #   因为子进程会 spawn 孙进程 mineru 式，DETACHED 会破坏 CREATE_NO_WINDOW）
   # - Linux: start_new_session=True + prctl(PR_SET_PDEATHSIG=SIGKILL)
   # - macOS: start_new_session=True + atexit cleanup

   prompt_file = _write_temp_prompt(task_prompt)
   log_fp = open(log_path, "a", encoding="utf-8")

   popen_kwargs = dict(
       cwd=PROJECT_ROOT,
       stdout=log_fp,
       stderr=subprocess.STDOUT,
       env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"},
       close_fds=True,
   )
   if harness == "claude":
       popen_kwargs["stdin"] = subprocess.PIPE  # 写完 prompt 后 close
   else:
       popen_kwargs["stdin"] = subprocess.DEVNULL

   if sys.platform == "win32":
       popen_kwargs["creationflags"] = (
           subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
       )
       si = subprocess.STARTUPINFO()
       si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
       si.wShowWindow = 0  # SW_HIDE
       popen_kwargs["startupinfo"] = si
   else:
       popen_kwargs["start_new_session"] = True
       if sys.platform == "linux":
           popen_kwargs["preexec_fn"] = _linux_set_pdeathsig

   proc = subprocess.Popen(cmd, **popen_kwargs)
   if harness == "claude":
       proc.stdin.write(task_prompt.encode("utf-8"))
       proc.stdin.close()  # EOF → agent 开始执行

   _assign_pid_to_job(self._job_handle, proc.pid)  # Win: kill-on-parent-death
   ```

3. **Task prompt 构建**（Phase 2.3）：claude → stdin pipe 写入；omp → 写入临时 `@prompt.txt` 文件并在 args 中引用
4. **等待 + 超时**：omp 用 `--max-time`（进程内硬超时）；claude 用 `asyncio.wait_for(self._watch_process(proc), timeout=cfg.timeout_sec)` 兜底
5. **读取 agent 输出**：从 stdout log 文件解析最后的 JSON 块（claude 因 `--json-schema` 保证合法 JSON；omp 从文本中提取 `meditation_result` JSON 块）
6. **结果处理**：agent 已通过 MCP 工具直接写入经验，后端只更新 run 记录 + KB metadata 状态

> **关键：为何用 --bare 模式**：claude 默认会尝试 OAuth keychain / hooks / plugin sync，在无交互子进程中可能卡死或弹窗。`--bare` 跳过所有这些，auth 严格使用 `ANTHROPIC_API_KEY` 环境变量（在启动前检查 env，若未设置则 fallback 到启发式）。Skills 仍通过 `/skill-name` 可用。

#### 2.2 System Prompt + Result Schema
**File:** `backend/app/services/prompts/meditation_agent_system.txt`

这个 prompt 嵌入**完整的 skill 规范**，让 agent 子进程按与手动总结完全相同的标准工作。同时定义 JSON Schema 让 `claude --json-schema` 强制校验输出（omp 用 prompt 内 JSON 指令）。

**Result JSON Schema**（Python 中定义，传给 claude --json-schema）：
```python
RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "meditation_result": {
            "type": "object",
            "properties": {
                "kb_id": {"type": "string"},
                "experiences_created": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "exp_id": {"type": "string"},
                            "scenario": {"type": "string"},
                            "quality_score": {"type": "number"}
                        }
                    }
                },
                "drafts_created": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "draft_id": {"type": "string"},
                            "quality_score": {"type": "number"}
                        }
                    }
                },
                "skipped": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "reason": {"type": "string"}
                        }
                    }
                },
                "total_signals_processed": {"type": "integer"},
                "summary": {"type": "string"}
            },
            "required": ["total_signals_processed", "experiences_created", "drafts_created"]
        }
    },
    "required": ["meditation_result"]
}
```

```
你是知识库经验提炼专家 agent。你的唯一任务是从用户的历史问答中提炼高质量结构化经验。

## 工作流程
1. 你已连接到知识库 MCP 服务（kb-mcp），拥有全部 experience_* 和 kb_doc_* 工具
2. 阅读 Task Prompt 中提供的用户问题和检索到的文档片段
3. 对每个待提炼的问题簇：
   a. kb_list(lightweight=true) 确认目标 KB
   b. experience_search_smart(query=代表性问题, top_k=5) 检查已有经验
   c. 若已有 P0/P1 经验覆盖该问题 → 跳过（去重）
   d. kb_search_two_stage(query, kb_id) 检索最新文档
   e. kb_doc_read(kb_id, doc_path, max_chars=3000) 读取文档原文
   f. 按【质量标准】提炼结构化经验
   g. 质量自检（见清单）
   h. 质量≥7 且配置允许自动发布：experience_create(...) 正式发布
   i. 质量 3-6：通过 save_draft 写入草稿池
   j. 质量<3：丢弃，记录原因

## 质量标准（必须全部满足）
{在此嵌入 .claude/skills/knowledgebase-experience-summarize/references/quality-standards.md 全文}

## 经验字段规范
- title: 含场景词+方法词
- scenario: kebab-case，含领域前缀（如 "mcp-connection-refused"）
- category: troubleshooting|best_practice|workflow|optimization|lesson_learned|decision|tip
- problem: 具体可复现场景，≥50字符，含错误码/数字/参数
- solution: 可执行步骤，≥100字符（troubleshooting≥80），必须基于读到的文档内容
- key_lessons: 3-5条，每条≥30字符，可独立引用
- tags: ≥2个，领域词+方法词
- related_docs: 你实际读取过的真实文档路径
- severity: critical|important|normal|tip
- result: success|partial|failed

## 禁止事项
- 不得编造文档中没有的内容
- 不得创建泛泛经验（"检查配置""注意安全"等）
- 不得在 related_docs 中写未读取的路径
- 如果文档片段不足以支撑高质量经验，返回 reject，不要强行生成

## 输出格式（严格 JSON）
完成后在最后一条消息中输出：
{
  "meditation_result": {
    "kb_id": "<目标KB>",
    "experiences_created": [{"title": ..., "exp_id": ...}],
    "drafts_created": [{"title": ..., "draft_id": ...}],
    "skipped": [{"query": ..., "reason": ...}],
    "total_signals_processed": N
  }
}
```

**Task Prompt**（通过 stdin 传入，每次运行动态构建）：
```
## 本次冥想任务

目标知识库: {kb_name} (id={kb_id}, path={kb_path})
触发器: {trigger} (scheduled|incremental|manual)
信号窗口: 最近 {lookback_days} 天

## 待处理问题簇（共 {n} 簇）
{for each cluster:}
### 簇 {i}（出现 {count} 次）
代表性问题: {representative}
样本问题:
{samples}

用户已获得的回答:
{answer_texts}

相关检索文档:
{for each doc: path={path}, score={score}, snippet={first 200 chars}}
{end for}

## 配置
- 自动发布阈值: quality≥{auto_publish_threshold} 且 auto_publish={auto_publish_enabled}
- 最大产出: {max_drafts_per_run} 条经验

请按 system prompt 中的工作流程开始工作。确保每条经验都经过 kb_doc_read 验证文档内容。
```

#### 2.3 Task Prompt 模板（动态构建，每次运行不同）
**File:** `backend/app/services/prompts/meditation_task_template.txt`

Task prompt 包含本次运行的具体数据（signals/cluster/docs），通过 stdin（claude）或临时 @file（omp）传入：

```
## 本次冥想任务

目标知识库: {kb_name} (id={kb_id}, path={kb_path})
触发器: {trigger} (scheduled|incremental|manual)
信号窗口: 最近 {lookback_days} 天
待处理问题簇: {n} 个
最大产出: {max_drafts_per_run} 条经验
自动发布: quality≥{threshold} 且 auto_publish={true|false}

## 待处理问题簇
{for each cluster i:}
### 簇 {i}（出现 {count} 次）
代表性问题: {representative}
同类样本:
- {sample1}
- {sample2}
- {sample3}

用户已获得的回答摘要:
{answer_texts}

相关检索文档（请用 kb_doc_read 读取全文验证）:
{for each doc: path={doc_path}, score={score}, snippet={first 200 chars}}
{end for}
{end for}

## 输出要求
完成后输出满足 JSON Schema 的 meditation_result。所有经验必须通过 kb_doc_read 验证后再创建。
```

#### 2.4 结果解析与持久化
- Agent stdout log 文件中提取最后的 JSON 块
- claude: `--output-format json` + `--json-schema` 保证合法 JSON，直接 parse
- omp: `--mode=json` 从文本中提取 JSON 块（容错：找最后一个 `{...}` 大括号块）
- 解析失败 → run.status="failed", error="agent_output_parse_failed", 保留 stdout_tail
- 成功但 agent 报告 0 experiences → run.status="completed", note="no qualifying patterns"
- Agent 自身已经调用了 MCP 工具写经验 → 后端只记录 run 报告
- **关键**：agent 通过 MCP 工具直接写经验到 KB → 后端不需再写经验内容，只需：
  1. 更新 `meditation_runs` 表记录
  2. 更新 KB YAML metadata.meditation（last_run_at, total_experiences_generated）
  3. 记录 agent 产出的 exp_id 列表到 report_json

#### 2.5 启发式 Harness（降级 fallback）
当 `harness="heuristic"` 或 agent harness 不可用时：
- 复用现有 `experience_meditation_service.py` 中的机械提取逻辑
- 直接构造 draft_data 调 `save_draft()`
- 产出标注 `harness="heuristic"`, confidence=0.3, vetted=False

#### 2.6 Harness 健康检查 + Circuit Breaker
- 启动时一次性探测：
  - `claude`: 检查 `claude --version` 成功 + `ANTHROPIC_API_KEY` env 存在（`--bare` 模式需要 API key，不使用 OAuth）
  - `omp`: 检查 `omp --version` 成功（OMP 使用其自己的 auth chain）
- 提供 `GET /api/v1/meditation/harness-status` 端点：
  ```json
  {
    "claude": {"installed": true, "version": "2.1.220", "api_key_configured": true},
    "omp": {"installed": true, "version": "17.1.5"},
    "circuit_breaker": {"tripped": false, "until": null, "consecutive_failures": 0}
  }
  ```
- 运行时：连续 3 次 agent 失败（超时/退出码非0/parse失败/认证错误）→ circuit breaker 24h
- Circuit breaker 状态暴露在 `/api/v1/meditation/status`
- 前端 UI 在 KB 设置面板显示 harness 可用性（✅ 可用 / ⚠️ 需配置 API key / ❌ 未安装）

#### 2.7 跨平台进程终止
复用 MinerU manager 的成熟逻辑（`mineru_manager.py:615-642`）：
```python
def _terminate_process(self, proc: subprocess.Popen) -> None:
    """Cross-platform process + subtree kill."""
    if sys.platform == "win32":
        # taskkill /T kills whole tree (agent may spawn children)
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True, timeout=10,
            **_run_silent_kwargs(),
        )
    else:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
            # Give 5s grace, then SIGKILL
            import time as _t; _t.sleep(5)
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
```

#### 2.8 Process Watcher（asyncio 集成）
```python
async def _watch_process(self, proc: subprocess.Popen, log_path: Path, timeout_sec: int) -> dict:
    """Wait for process in thread pool (non-blocking), parse output on completion."""
    def _wait_sync():
        proc.wait(timeout=timeout_sec)
    try:
        await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _wait_sync),
            timeout=timeout_sec + 10,  # extra buffer
        )
    except asyncio.TimeoutError:
        self._terminate_process(proc)
        return {"status": "timeout", "exit_code": -1}
    # Read log file and parse result JSON
    return self._parse_result_log(log_path, proc.returncode)
```

**Phase 2 验收：**
- [ ] `omp -p --auto-approve --mode=json` 子进程成功 spawn，agent 读 MCP 工具创建经验
- [ ] `claude -p --bare --output-format json --json-schema` 子进程同上（验证 ANTHROPIC_API_KEY 检查）
- [ ] 子进程 stdout 正确写入 log 文件（无 PIPE Errno 22）
- [ ] omp `--max-time` 超时生效；claude 超时 → `taskkill /T /F` 杀进程树
- [ ] 超时后无孤儿进程（Job Object kill-on-close / prctl 验证）
- [ ] Agent 产出经验字段 100% 符合 quality-standards 标准（人工审查 5 条产出）：
  - title/scenario/category/problem/solution/key_lessons/tags/severity/related_docs 全部达标
- [ ] Agent 通过 `kb_doc_read` 验证文档（不是仅靠 snippet 编造）
- [ ] `--json-schema` 强制 claude 输出合法 JSON，parse 100% 成功
- [ ] 启发式 fallback 在 harness 不可用/未配置 API key 时正常工作
- [ ] Circuit breaker 在连续 3 次失败后生效，24h 内不重试
- [ ] Harness 健康检查 API 返回正确的 installed/version/api_key_configured 状态
- [ ] 运行期间 health endpoint p99 < 500ms
- [ ] 全局并发 Semaphore(2) 限制同时运行的 agent 数
- [ ] 后端进程 kill 后，spawn 的 agent 子进程全部随之死亡（Job Object 验证）

---

### Phase 3: 前端 KB 冥想管理 UI（~2 days）

#### 3.1 KB 冥想设置 API
- `web/server/api/kb/meditation.get.ts` — GET `/api/kb/meditation?kbId=X`
- `web/server/api/kb/meditation.put.ts` — PUT `/api/kb/meditation` body: {kbId, config}
- `web/server/api/meditation/*.ts` — 代理 status/run/history/signals 到 backend

#### 3.2 KB 设置面板
**File:** `web/pages/knowledge-base.vue` + `web/components/KbMeditationSettings.vue`（新建）

在 KB 右侧面板增加 **"⚙️ 知识库设置"** 按钮，打开 Drawer/Modal：

```
┌──────────────────────────────────────────────┐
│ 🧘 自动经验总结（冥想）                        │
├──────────────────────────────────────────────┤
│ ☑ 启用自动冥想                                 │
│                                              │
│ 执行引擎:                                    │
│   ○ OMP (推荐)  ○ Claude Code  ○ 启发式      │
│                                              │
│ 模型: [sonnet ▾]  (opus/sonnet/haiku)        │
│                                              │
│ 运行间隔: [24] 小时                           │
│ 最小问题簇: [2] 个相似问题才触发               │
│ 每次最多生成: [3] 条经验                      │
│ 单次预算上限: $[0.05]                        │
│                                              │
│ ☐ 高质量经验自动发布（否则入草稿池）          │
│ ☑ 增量触发（问题积累到阈值立即触发，不等周期）│
│                                              │
│ ── 运行状态 ─────────────────────────────    │
│ 上次运行: 2026-07-28 03:00  ✅ 成功           │
│ 运行引擎: omp (sonnet)                       │
│ 累计生成: 12 条经验                          │
│ 待审草稿: 3 条                               │
│ 失败次数: 0                                  │
│                                              │
│ [🧘 立即运行冥想]  [💾 保存设置]              │
└──────────────────────────────────────────────┘
```

- Harness 选择下拉显示安装状态："OMP ✅ 已安装" / "Claude Code ✅" / "启发式"
- 模型选择根据 harness 动态调整（omp: "opus"/"sonnet"/"haiku"；claude: "claude-opus-4-..."）
- "立即运行冥想"按钮 → 调 meditation/run API → 轮询 status 显示进度（spinner + log 尾部）
- 设置保存后立即生效（scheduler 下次循环读取最新配置）

#### 3.3 KB 列表状态指示
- KB 列表项显示 🧘 图标（开启）或灰色图标（关闭）
- badge 显示待审草稿数

#### 3.4 经验管理主页面
**File:** `web/pages/experience.vue`（新建 ~500 行）
- Tab 布局：搜索 / 仪表盘 / 草稿审核 / 冥想历史 / 管理
- 冥想历史 Tab 表格：时间/KB/harness/状态/产出数/耗时/cost
- 点击行展开：agent stdout log 尾部 + 产出经验链接

#### 3.5 补充缺失代理路由
- smart-search、rerank、dashboard、drafts CRUD、extract、stale/decay/sync

**Phase 3 验收：**
- [ ] 前端能开启/关闭 KB 冥想，保存后 YAML 正确写入
- [ ] Harness 下拉正确显示安装状态
- [ ] "立即运行"触发 agent 子进程，页面轮询显示完成
- [ ] KB 移动后冥想设置完好
- [ ] 经验页面可搜索/审核草稿/查看冥想历史

---

### Phase 4: 经验进化闭环（~1 day）

#### 4.1 vetted 升级路径
- `apply_experience` + `review_experience` 后检查：
  - auto_extracted=True AND NOT vetted AND applied_count≥2 AND rating_avg≥4.0 → vetted=True
- vetted 经验可升 P0（突破 unvetted cap）

#### 4.2 低评自动降级
- review_count≥3 AND rating_avg<2.0 → decay_flag="disputed", vetted=False → cap P2

#### 4.3 冥想报告持久化
- 每次 run 完成后更新 KB YAML metadata.meditation：
  - `last_run_at`, `last_run_status`, `last_run_report`, `total_runs++`, `total_experiences_generated += N`

#### 4.4 经验 Stale 联动
- 文档更新触发 `check_stale` → agent 可被 spawn 重读文档更新经验（未来 v3.1，v3.0 只标记 stale）

#### 4.5 跨 KB 经验迁移保护
- KB merge 时：源 KB 经验 + 冥想配置一并迁移到目标 KB

**Phase 4 验收：**
- [ ] 自动经验被 apply 2次+好评 → vetted=True，可升 P0
- [ ] 3次差评 → disputed → cap P2
- [ ] 每次冥想后 KB YAML metadata 更新
- [ ] KB merge 后经验+配置完整

---

### Phase 5: MCP/CLI/Skill 文档（~1 day）

#### 5.0 手动经验总结流程（已有机制，不变）
用户触发关键词（"总结经验""记录教训""提炼经验"等）→ `knowledgebase-experience-summarize` skill
→ Archival agent（当前会话内）→ MCP 工具 `experience_create` → 持久化

**这是现有工作流，不做修改**。自动冥想只是让同一套流程在后台定时/增量触发。
两者共用：
- 同一个 quality-standards.md 质量标准
- 同一个 MCP 工具集（experience_create, save_draft, kb_doc_read 等）
- 同一个经验存储（.experience-index.yml + .md + ChromaDB）
- 同一个进化闭环（apply/review/vetted/decay）

#### 5.1 MCP 工具
**File:** `kb-mcp/server.py` + `kb_client/client.py`
- `experience_meditation_status(kb_id?)` — 状态（含 harness 健康）
- `experience_meditation_run(kb_id?, trigger="manual")` — 手动触发
- `experience_meditation_config_get(kb_id)` / `experience_meditation_config_update(kb_id, config)`
- `experience_meditation_history(kb_id?, limit=20)` — 运行历史

#### 5.2 ragctl meditation 子命令
```
ragctl meditation status [--kb KB_ID]
ragctl meditation run [--kb KB_ID] [--harness omp|claude|heuristic]
ragctl meditation config --kb KB_ID [--enable/--disable] [--interval H] [--harness omp|claude]
ragctl meditation history [--kb KB_ID] [--lines N]
ragctl meditation drafts --kb KB_ID
```

#### 5.3 Skill 文档更新
**File:** `.claude/skills/knowledgebase-experience-summarize/`
- `references/meditation.md` 更新：反映 agent-harness 自动冥想架构，手动/自动双模式共用同一质量规范
- `SKILL.md` NEVER 清单：冥想配置仅存 KB YAML metadata；自动冥想由 backend spawn agent，skill 内不自启定时器
- 新增 `references/meditation-harness.md`：后端 spawn agent 的技术实现说明（prompt 模板、环境变量、故障排查）

#### 5.4 CLAUDE.md 更新
- 已知坑：agent harness 需用户已认证 claude/omp；首次运行建议 `claude --version` 验证；超时检查 log 文件
- 经验章节：KB 级配置 + auto-generated 经验的 vetted 生命周期

**Phase 5 验收：**
- [ ] MCP 工具可获取/更新每个 KB 的冥想配置
- [ ] `ragctl meditation run --kb XXX --harness omp` 正确触发
- [ ] Skill 文档与代码行为一致
- [ ] Claude Code 会话中 Archival agent 可查询冥想状态

---

## Test Plan

### Unit Tests
| Test | 目标 |
|------|------|
| test_dedup_fix | 去重 bug |
| test_kb_meditation_config_crud | 配置读写/默认值/YAML持久化 |
| test_kb_move_preserves_config | KB move 后配置完好 |
| test_decay_penalty | stale/disputed 排序 |
| test_circuit_breaker | 3次失败禁用24h |
| test_vetted_upgrade | apply 2次+好评 → vetted |
| test_double_downgrade_removed | smart_search 单次调用 |
| test_harness_command_build | omp/claude cmd 构建正确 |
| test_prompt_contains_quality_standards | system prompt 包含完整 quality-standards 内容 |
| test_task_prompt_construction | 信号→task prompt 正确格式化 |
| test_result_json_parsing | agent stdout → JSON 解析（含边缘情况：前后噪声文本） |
| test_heuristic_fallback | harness 不可用时 fallback |

### Integration Tests
| Test | 步骤 |
|------|------|
| **test_omp_harness_synthesis** | mock omp → spawn 子进程 → 验证 agent 调了 MCP 工具 → 经验出现在 KB |
| **test_claude_harness_synthesis** | 同上用 claude -p |
| test_agent_timeout_kill | mock agent sleep 10s + timeout=5s → 进程被 kill → no orphan |
| test_budget_cap | max_budget=$0.01 → agent 在预算内停止 |
| test_job_object_cleanup | backend process kill → agent 子进程随之死亡 |
| test_non_blocking | agent 运行期间 health endpoint p99 < 500ms |
| test_signal_harvest_kb_scoped | 不同 KB 信号不串扰 |
| test_incremental_trigger | 连续写入 3 同类问题 → agent 立即 spawn |
| test_auto_publish_cap | 自动经验最高 P1（vetted=False） |
| test_feedback_loop | apply+review → vetted → 可到 P0 |

### E2E Tests (manual)
| Test | 步骤 |
|------|------|
| 端到端 OMP 冥想 | 创建 KB → 开启冥想(omp) → KB chat 问 5 个相关问题 → 等/触发冥想 → 检查经验质量 |
| 端到端 Claude 冥想 | 同上切换 harness=claude |
| KB 迁移配置 | 创建 KB+配置冥想+有经验 → move → 配置+经验+草稿全部完好 |
| 草稿审核 | 冥想产出草稿 → UI 编辑 → 批准 → 搜索可见 |
| 启发式降级 | 卸载 claude+omp → 冥想自动降级启发式 → 草稿产出 |
| 经验进化 | 自动经验 → apply 2次+好评 → vetted=True → 搜索升 P0 |

### Observability
- 结构化 log: `[Meditation] kb=<name> harness=<omp|claude|heuristic> pid=<N> signals=N exp_created=N drafted=N cost=$X elapsed=Xs`
- Agent log 文件: `backend/logs/meditation-agent-{run_id}.log`（agent 完整 stdout/stderr，排障用）
- `/api/v1/meditation/status` 全局状态 + 各 KB + harness 健康（claude_installed/omp_installed/circuit_breaker）
- Run 报告在 YAML metadata + meditation_runs 表双写

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Agent 子进程僵尸/挂起 | HIGH | 硬超时 600s + Job Object / prctl + stdout→file（非 pipe） |
| Claude/OMP 认证失败 | MEDIUM | 启动探测 + circuit breaker 24h + 自动降级启发式 |
| Agent 不遵守 JSON 输出格式 | MEDIUM | `--output-format json` + task prompt 明确标记 `meditation_result` + parse 失败日志记录 |
| Agent tool 调用循环成本失控 | MEDIUM | `--max-budget-usd` 硬上限 + 进程超时 + max_drafts_per_run=3 |
| Windows Job Object 创建失败 | LOW | try/except 包裹，降级 atexit + process group 清理（MinerU 同样降级路径） |
| 子进程并发过多资源耗尽 | MEDIUM | 全局 Semaphore(2) + KB 级锁；同一 KB 不并发；spawn 前检查已有运行 |
| 经验质量低于人工总结 | MEDIUM | prompt 嵌入完整 quality-standards.md + auto_publish 默认 false（先进草稿池） |
| YAML metadata 迁移与旧数据冲突 | LOW | 全部字段有默认值；metadata 是已有 `Record<string,any>` 字段，零 schema 迁移 |
| 首次运行下载 skill/MCP 配置慢 | LOW | prompt 模板内联（不依赖 agent 读文件）；MCP config 路径固定 |
| 用户未安装 claude/omp | LOW | harness 默认 omp（项目用 OMC 已带）；两工具都不可用时降级启发式 + UI 提示 |

---

## File Change Summary

| File | Action | Lines |
|------|--------|-------|
| `backend/app/services/agent_harness_manager.py` | **New** | ~350 (subprocess spawn, Job Object, cmd building, omp/claude/heuristic) |
| `backend/app/services/experience_meditation_service.py` | Modify | ~300 (KB感知调度, bug fixes, non-blocking, incremental trigger) |
| `backend/app/services/experience_service.py` | Modify | ~150 (decay wiring, vetted path, KB meditation config reader, new fields) |
| `backend/app/services/meditation_db.py` | **New** | ~120 (SQLite signals + runs CRUD) |
| `backend/app/services/prompts/meditation_agent_system.txt` | **New** | ~150 (system prompt with embedded quality-standards) |
| `backend/app/services/prompts/meditation_task_template.txt` | **New** | ~50 (task prompt template) |
| `backend/app/models/experience_models.py` | Modify | ~25 (new fields) |
| `backend/app/api/routes/meditation.py` | **New** | ~100 (status/run/history/signals/config) |
| `backend/app/config.py` | Modify | ~10 (add meditation_system_prompt path config) |
| `backend/app/main.py` | Modify | ~15 (lifespan init harness manager + circuit breaker probe) |
| `backend/app/utils/mineru_manager.py` | 复用 | 不修改，AgentHarnessManager 复用其 _create_kill_on_close_job / _assign_pid_to_job |
| `kb-mcp/server.py` | Modify | ~70 (remove double downgrade, add meditation MCP tools) |
| `kb-mcp/kb_client/client.py` | Modify | ~60 (new HTTP methods) |
| `web/server/utils/chat-db.ts` | Modify | ~40 (signals table — backend now owns DB, web only reads for feedback UI) |
| `web/types/knowledge-base-yaml.ts` | Modify | ~25 (MeditationConfig interface) |
| `web/server/services/knowledge-base-yaml-service.ts` | Modify | ~60 (get/update meditation config) |
| `web/server/api/kb/meditation.get.ts` | **New** | ~20 |
| `web/server/api/kb/meditation.put.ts` | **New** | ~30 |
| `web/server/api/meditation/*.ts` | **New** (×5) | ~80 (proxy routes) |
| `web/server/api/experience/*.ts` | **New** (×12) | ~180 (missing proxy routes) |
| `web/pages/knowledge-base.vue` | Modify | ~180 (settings button + drawer) |
| `web/pages/claude-chat.vue` | Modify | ~80 (feedback + save experience) |
| `web/pages/experience.vue` | **New** | ~500 (experience management page) |
| `web/components/KbMeditationSettings.vue` | **New** | ~250 (settings form) |
| `web/components/ExperienceDraftReview.vue` | **New** | ~200 |
| `web/layouts/default.vue` | Modify | ~5 (nav entry) |
| `config.yml` | Modify | ~5 (global defaults) |
| `.claude/skills/knowledgebase-experience-summarize/references/meditation.md` | Modify | ~80 (agent-harness architecture) |
| `.claude/skills/knowledgebase-experience-summarize/references/meditation-harness.md` | **New** | ~80 (technical implementation doc) |
| **Total** | | **~3500 lines** |

---

## ADR: Architecture Decision Record

### Decision
**Agent-Harness 模型**：后端 scheduler 机械地 harvest/cluster/score/filter，到达成条件时 spawn `omp -p` 或 `claude -p` 子进程，通过 stdin 传入任务上下文（signals + 文档片段），agent 子进程加载 kb-mcp MCP 配置后自主调用 MCP 工具完成经验提炼（与手动总结执行同一套 skill 规范），产出通过 MCP 工具直接持久化。

### Key Sub-Decisions
1. **复用 MinerU 子进程模式**：Job Object（Win）/ prctl（Linux）+ stdout→file + CREATE_NO_WINDOW — 成熟可靠
2. **默认 OMP**：项目是 OMC 生态，`omp` 已安装；用户可切换 claude
3. **Agent 直接用 MCP 工具写经验**：后端不解析/不重写 agent 产出的经验内容 → 避免后端二次逻辑导致质量降级
4. **Prompt 内联 skill 规范**：不依赖 agent 文件系统读取 `.claude/skills/`；system prompt 嵌入 quality-standards 全文确保一致
5. **经验 = Skill 格式**：Markdown 正文采用类 SKILL.md 格式（frontmatter + 触发场景/诊断/方案/教训章节），使经验可被 Agent 直接当 Skill 使用
6. **claude --bare 模式**：跳过 OAuth/hooks/插件，严格使用 ANTHROPIC_API_KEY env，避免子进程弹窗卡死
7. **双层配置**：全局 master switch（config.yml）+ 单 KB 开关（YAML metadata），冥想配置随 KB 移动

### Drivers
1. 最大化复用现有基础设施（skill/MCP/quality gate）
2. 零 API key 管理
3. 进程级故障隔离
4. KB 级 harness 可插拔
5. 自动经验 = 人工经验质量

### Consequences
- **Positive:** 后端代码简单（spawn + watch），所有智能在 agent 中（已有的 skill）；新增 harness 只需加一个 exe 配置 dict；agent 子进程超时/崩溃不影响主服务
- **Negative:** 每次冥想 spawn 冷启动 agent 有 ~5-15s 开销（可接受，间隔是 24h）；依赖用户环境有 claude/omp 认证；调试需要查 agent log 文件
- **Risk:** Agent 版本更新可能改变输出格式 → JSON marker + fail-soft 处理

### Follow-ups
- [ ] v3.1: stale 检测触发 agent 更新旧经验（spawn agent 读新文档 → update_experience）
- [ ] v3.1: 经验关系图谱（related_experiences + 跨 KB 迁移推荐）
- [ ] v3.2: Agent prompt 版本化（A/B test 不同 prompt 模板的产出质量）
- [ ] v3.2: 多模型对比（同一 cluster 用 sonnet/opus/haiku 分别生成，选最优）
- [ ] v3.3: 经验自然语言查询"给我看最近冥想生成了什么"→ MCP 工具直接回答
- [ ] v3.3: 经验执行反馈闭环（Agent 应用经验后自动调 experience_apply）

### 完整经验生命周期

```
                         ┌─────────────────────────────┐
                         │     🧘 自动冥想触发          │
                         │  (scheduler / incremental)  │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
              ┌─────────────────────────────────────────────┐
              │  Agent Harness (omp / claude subprocess)    │
              │  ┌─────────────────────────────────────┐   │
              │  │ 1. 读 meditation_signals (Q&A/docs)  │   │
              │  │ 2. kb_list → 确认目标 KB             │   │
              │  │ 3. experience_search_smart → 去重    │   │
              │  │ 4. kb_search_two_stage → 检索文档    │   │
              │  │ 5. kb_doc_read → 验证内容            │   │
              │  │ 6. 按 quality-standards.md 提炼      │   │
              │  │ 7. 质量自检（完整性清单）            │   │
              │  │ 8a. 质量≥7 + auto_publish → create   │   │
              │  │ 8b. 质量3-6 → save_draft             │   │
              │  │ 8c. 质量<3 → reject                  │   │
              │  └─────────────────────────────────────┘   │
              └────────────┬────────────────────┬───────────┘
                           │                    │
                           ▼                    ▼
              ┌────────────────────┐  ┌─────────────────────┐
              │ ✅ 正式经验         │  │ 📝 草稿池            │
              │ vetted=False       │  │ (draft/ folder)     │
              │ harness=omp/claude │  │ 等 UI/Agent 审核     │
              │ .md (Skill格式)    │  └─────────┬───────────┘
              │ .experience-index  │            │ approve/reject
              │ ChromaDB vector    │            ▼
              └────────┬───────────┘  ┌─────────────────────┐
                       │              │ ✅ 正式经验 (同上)    │
           ┌───────────┴───────────┐  │ vetted=True (人工审) │
           │  用户检索命中          │  └─────────────────────┘
           │  experience_search_   │
           │  smart (P0/P1/P2)    │
           └───────────┬───────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
┌──────────────────┐      ┌──────────────────────┐
│ experience_apply │      │ experience_review     │
│ (用户采纳+1)     │      │ (评分 1-5 + 评论)     │
└────────┬─────────┘      └──────────┬───────────┘
         │                           │
         └───────────┬───────────────┘
                     ▼
          ┌─────────────────────────────┐
          │  可信度进化                   │
          │  • apply≥2 + rating≥4.0     │
          │    → vetted=True (可升 P0)   │
          │  • review≥3 + rating<2.0    │
          │    → disputed (cap P2)       │
          │  • decay cycle (30天/7天)    │
          │    → stale_unverified ×0.7  │
          └─────────────────────────────┘
                     │
                     ▼
          ┌─────────────────────────────┐
          │  📄 文档更新 → check_stale   │
          │  → 经验过时 → 下次冥想更新   │
          └─────────────────────────────┘
```

---

## Execution Order

### Minimal Viable Path（~6 days）
1. Phase 0 (2d) — bug fixes + KB config + model fields + Skill-like markdown format
2. Phase 2 (2.5d) — agent_harness_manager + OMP harness + system prompt + process lifecycle
3. Phase 3.1-3.2 (1.5d) — KB settings API + frontend panel

### Complete Path（~10 days）
Phase 0 → 1 → 2 → 3 → 4 → 5

### 关键依赖与风险前置（执行顺序）
1. **先做 Phase 0.6/0.8**：KB config 模型 + Markdown 格式升级 → 所有后续构建在此之上
2. **再做 Phase 2.1/2.6**：AgentHarnessManager 骨架 + 健康检查 → 先验证 omp/claude 能成功 spawn 并连 MCP
3. **再做 Phase 2.2/2.3**：Prompt + 解析 → 验证 agent 产出符合质量标准
4. **前端 Phase 3 最后做**：等后端 API 稳定后再做 UI，避免返工

---

**Plan file:** `.omc/plans/experience-meditation-v2.md`
**Next step:** 审批通过后通过 `ralph` 或 `team` 执行
