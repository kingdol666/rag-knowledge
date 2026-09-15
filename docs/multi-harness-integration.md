# 多 Harness 集成说明（rag-knowledge 版）

> 日期：2026-09-10 · 对齐 `D:\codes\ABO\AgentWorkShop\docs\multi-harness-architecture.md`（可移植版多 Harness 适配架构指南）
> 本平台按「一次性回合作业」模型移植其七条核心原则：meditation 经验合成 / SOUL 补全统一经 `complete()` / `synthesize_experiences()` 驱动任意引擎。

## 1. 支持的引擎（14 + 内置 heuristic）

| id | 引擎 | 投递方式 | 输出形态 | 能力（本集成口径） |
|---|---|---|---|---|
| mock | 进程内剧本引擎 | inprocess | 剧本 JSON | 恒可用，联调/CI 用 |
| omp | oh-my-pi | @临时文件 | JSONL 事件流 | usage 统计 |
| opencode | OpenCode | arg（7.5K 上限） | 纯文本 | — |
| codex | OpenAI Codex CLI | stdin（`-`） | NDJSON（item.completed） | usage 统计 |
| dsh | DeepSeek Harness | ACP 内嵌 | session/update 聚合 | — |
| claude | Claude Code | stdin | 单 JSON（result） | usage 统计 |
| gemini | Gemini CLI | arg（7.5K 上限） | JSON（response） | usage 统计 |
| copilot | GitHub Copilot CLI | stdin | JSON（response） | — |
| cursor | Cursor CLI | arg（30K 上限） | JSON（result） | usage 统计 |
| crush | Charm Crush | arg（30K 上限） | 纯文本 | — |
| goose | Block Goose | arg `-t`（30K 上限） | stream-json | usage 统计 |
| qwen | Qwen Code | arg `-p`（7.5K 上限） | JSON（response） | usage 统计 |
| pi | pi coding agent | @临时文件 | JSONL（message_end） | usage 统计 |
| hermes | Hermes Agent | ACP 内嵌 | session/update 聚合 | — |
| heuristic | 内置启发式回退 | inprocess | 结构化抽取 | 无 LLM，调度静默回退用 |

能力六元组（steer/supervise/hitl/terminal/context_stats/compact）如实声明于
`backend/app/services/harness_registry.py`：本平台为一次性作业模型，无常驻会话 →
steer/hitl/terminal/compact 全部显式为 false（不支持的面写明降级语义，不虚报）；
supervise 是平台 prompt 驱动、全部支持；context_stats 仅在解析到 usage 事件时声明。

## 2. 架构与文件

```
上层（meditation 路由 / soul 服务 / 调度器 / 前端下拉）
            │ 只依赖
   agent_harness.complete() / synthesize_experiences()   ← 单一契约
            │ 装配
   harness_registry.py   单一事实源：14 引擎 id/label/能力/模型目录/探测声明
            │                + resolve_command（探测与拉起同源）
            │                + assert_harness_usable（未知400/未装409/可用）
   harness_specs.py      OneShotEngineSpec：build_args/promptDelivery/parse_output
            │                + ACP 单回合驱动器（dsh/hermes）+ mock 剧本引擎
   harness_runner.py     run_engine()：统一作业通道
                            Windows Job Object / taskkill /T /F、stdout→.out stderr→.err
                            日志路径 sanitize+锚定、mkstemp 临时 prompt 文件、超时收割
```

- **探测与拉起同源**：`resolve_command()` 同时服务 probe 与真实 spawn；命令覆盖链
  `config.yml → harness.commands.<id>` 是最后一环（npm shim 损坏时指包内真实 bin）。
- **Windows 纪律**：`.cmd/.bat` shim 以字面量 `cmd.exe /d /s /c` 包装，包装链逐参数校验
  （拒绝引号/换行/NUL）；`.exe` 直启走 list-form Popen（无 shell 重解析）。
- **错误即事件**：spawn 失败 / 非 0 退出 / 超时 / 解析失败一律结构化返回（stderr 尾部优先）；
  解析器对未知事件忽略并计数（schema 漂移防护）。
- **显式降级**：长 prompt 超 arg 投递上限 → 显式报错（不截断）；`.cmd` 包装引擎丢弃
  `--json-schema`（prompt 已内嵌格式模板，runner 从回复文本提取 JSON）。

## 3. API

| 端点 | 说明 |
|---|---|
| `GET /api/v1/meditation/harnesses` | 注册表全景（能力面/模型目录/实时可用性），前端下拉数据源 |
| `GET /api/v1/meditation/models?harness=<id>` | 模型目录（omp 动态发现，其余静态）；未知引擎 400 |
| `POST /api/v1/meditation/run` | body 支持 `harness` 覆盖本次作业引擎；未知 400 / 未安装 409 |
| `GET /api/v1/soul/settings` | 附 `harness_list`（注册表派生清单） |

前端：`web/components/KbMeditationSettings.vue` 与 `web/pages/soul.vue` 的引擎下拉均由
注册表驱动（含已安装徽标 / 能力提示 / 未安装禁用）；「立即运行」携带当前选中引擎。

## 4. 配置

`config.yml`：
```yaml
soul:
  default_harness: omp     # 注册表内任一 id（非法值回落 omp）
harness:
  commands:
    crush: "C:/path/to/crush.exe"   # 命令覆盖链最后一环
```

## 5. 测试

```bash
cd backend
python -m pytest tests/test_harness_registry.py   # 70 项：注册表/规格/解析器/mock 全链路/三态校验
python ../scripts/e2e_multi_harness.py mock       # 无 LLM 全链路
python ../scripts/e2e_multi_harness.py omp        # 真实子进程 + 真实 LLM 双场景
python ../scripts/e2e_multi_harness.py all        # 全部已装引擎逐一跑（无凭据引擎会真实失败）
```

约定（对齐原架构文档）：真实引擎 e2e 未安装/无凭据 → SKIP（有因跳过 ≠ 失败）。

## 6. 本机实测记录

### 6.3 第三轮（2026-09-13）—— 外部 API 端到端复验 + 6 项适配缺陷修复

复验方式：`python scripts/e2e_multi_harness.py all --quick`（真实子进程 + 真实 LLM 单回合）
＋ `python .ui-audit/e2e_platform.py`（纯外部 HTTP，覆盖 KB/检索/图谱/经验/人格/Harness）。

**探测口径修复前 → 后：已装从 11/15 修正为 13/15**（此前 claude、pi 被误判为不可用）。

| 缺陷 | 现象 | 根因 | 修复 |
|---|---|---|---|
| **pi 版本探测** | `installed=true` 但 `version=""`，且在不同 run 间抖动为 `installed=false` | `pi --version` 把版本写到 **stderr**（stdout 为空），探测只读 stdout | `_probe_impl` 改为 stdout→stderr 兜底取版本；退出码非 0 但有可读版本输出同样判为已安装 |
| **claude 被误判不可用** | 已安装 v2.1.267 且 OAuth 已登录，仍 `installed=false`（UI 置灰 + 409 拒绝） | 探测硬要求 `ANTHROPIC_API_KEY`；但适配器无条件带 `--bare`，而 `--bare` 恰恰绕过本地登录态 | 新增自有凭据库探测（`_CREDENTIAL_PATHS` / `harness_credentials()`）；`--bare` 改为**仅当 key 存在时**才传 |
| **claude 默认模型已废弃** | 报 "model 'claude-sonnet-4-20250514' is deprecated, EOL 2026-06-15" | 适配器硬编码了一个会过期的模型名作为默认值 | 只在调用方显式指定时才传 `--model`，否则用引擎自身当前默认（与注册表 `""`=引擎默认 的语义一致） |
| **claude 预算上限过低** | 每个作业 `terminal_reason=budget_exhausted`（实测一次合成 ~0.168 USD，上限 0.05） | 兜底 `max_budget_usd` 太紧，而本平台会注入 KB/persona 上下文 | 兜底提到 0.50（是**上限**不是消费）；调用方仍可覆盖 |
| **goose 假成功** | `success=true` 但 `exit_code=1`、正文是 `error: No provider configured` | runner 只要解析出非空文本就报成功，忽略退出码 | 新增 `_looks_like_engine_error()`：退出码非 0 且输出就是一条引擎级错误 → 结构化失败 |
| **copilot 解析错位** | `parse_failed`（或把整段事件流当答案返回） | 事件负载在 `data.content` / `data.deltaContent`，解析器只在**顶层**找 `response/text/content` | `_parse_copilot` 按实测 schema 重写（`assistant.message` 终稿 → `message_delta` 拼接 → `result.usage`），保留顶层兜底 |
| **hermes 被永久禁用** | `requires_env: ["GLM_API_KEY"]` | 官方 ACP 文档：provider 解析走 Hermes 自己的运行时解析器，ACP 继承**当前已配置**的 provider；GLM 只是 ~40 个可选 key 之一 | 移除该要求（`requires_env: []`），notes 补上 `uv pip install -e '.[acp]'` 前置步骤 |
| **error_code 误分类** | 预算耗尽被报成 `HARNESS_AUTH_OR_CONFIG` | 认证关键词在整段 JSON 事件流上裸扫，命中 `cache_read_input_tokens`、`maxOutputTokens` 等**字段名** | 预算标记优先判定（新增 `HARNESS_BUDGET_EXHAUSTED` + 可读 hint）；认证扫描先剔除结构性字段名 |

**修复后本机真实 LLM 单回合实测（`all --quick`）：**

| 引擎 | 结果 | 说明 |
|---|---|---|
| omp | ✅ "2" | 默认引擎，原生可用 |
| codex | ✅ "2" | ChatGPT 登录态 |
| dsh | ✅ "2" | ACP 单回合打通（早前 `acp_parse_failed` 系本机 `~/.dsh` 配置问题，现已恢复） |
| claude | ⚠️ 适配链已通 | 探测/OAuth/模型/预算四项已修；`--max-budget-usd` 仍会拦住超大作业（预期行为） |
| copilot | ✅ "2" | 解析器修复后正确取到终稿 + usage |
| pi | ✅ "1+1 = 2" | @临时文件投递 + JSONL message_end |
| mock | ✅ | 进程内剧本，零 token |
| goose | ❌ exit_1 | **正确报错**（`No provider configured`）—— 修复前是假成功 |
| gemini / crush / opencode / qwen | ❌ | 凭据/provider 未配置（各自引擎自有登录面），非适配缺陷 |

**仍未安装（2/15）**：`cursor`（需 `cursor-agent`，`curl https://cursor.com/install -fsS | bash`）、
`hermes`（需 `pip install -e '.[acp]'`，见上）。两者前端已按 ❌ 差异化置灰。

### 6.2 第二轮（2026-09-10）

**已装 12/14**（claude / cursor / hermes 未安装）。真实 LLM 双场景 e2e 通过：mock / omp / codex / pi。

### 真实 LLM 双场景 e2e 通过（简单任务，低 token）
| 引擎 | 场景 A 单次补全 | 场景 B 知识库作业（meditation 形态） |
|---|---|---|
| mock | ✅ | ✅（剧本，零 token） |
| omp | ✅（"1+1=2"） | ✅（meditation_result 提取成功；thinking 模型，需 ≥240s 超时） |
| codex | ✅（答 "2"，NDJSON/usage 解析 ✓） | ✅（首次因上游限流 turn.failed，冷却后重试通过 —— 错误即事件 ✓） |
| pi | ✅（--mode json @argFile 投递 ✓） | ✅ |

### 仅环境/凭据受阻（适配链已由桩测试全覆盖，接入凭据即可用）
| 引擎 | 实测失败点 | 定性 |
|---|---|---|
| opencode | "Authentication Failed"（glm-4.7 网关 key 失效） | 凭据 |
| gemini | exit 41 无 GEMINI_API_KEY/OAuth | 凭据 |
| crush | 未配置 provider（需 `crush` 交互配置） | 凭据 |
| goose | 未配置 provider（需 `goose configure`） | 凭据 |
| qwen | 缺 OPENAI_API_KEY（stdin 管道非交互路径已实测打通） | 凭据 |
| copilot | 需 GitHub token | 凭据 |
| dsh | 本机 `~/.dsh` MCP 配置损坏（`args:[null]`）拒启动 | 本机配置 |

### 依探针修正的适配（勿信文档）
- **copilot**：`-p` 必须紧跟 prompt 值（空置时会吞后续旗标报 "prompt not quoted"）→ arg 投递、`-p` 置于末位。
- **qwen**：老 fork 无 `--output-format`；`-p` 语义为"追加到 stdin"→ 改为管道 stdin + 纯文本解析。
- **gemini**：`-p` 必带 prompt 参数（不接受 stdin 管道）→ arg 投递 + 7.5K 护栏。

### 默认引擎可用性感知
`resolve_default_harness()`：配置默认引擎已装则用之；否则取注册表顺序第一个已发现引擎
（mock 仅作最终兜底）。本机解析结果 = **omp**。同步路径（KB 配置读取）消费探测缓存。

### 假 CLI 桩测试（无凭据全覆盖）
`backend/tests/fake_harness_engine.py` 桩 + `TestFakeCliAdapters`：13 个 CLI 引擎各自
经桩可执行文件真实走完 resolve→wrap→spawn→投递→解析全链（含 dsh/hermes 的 ACP 协议桩），
断言 prompt 按「该引擎的投递方式」实际送达。共 88 项单测全绿。

## 7. 历史记录（2026-09-10 首轮）

- 已装 12/14：mock/omp/opencode/codex/dsh/gemini/copilot/crush/goose/qwen/pi（+heuristic）。
- **omp 真实 e2e 双场景通过**（A: 单次补全 "1+1=2"；B: meditation_result JSON 提取成功）。
- gemini 实测：`-p` 必带 prompt 参数，stdin 管道不被接受 → spec 改 arg 投递（勿信文档，探针为准）。
- dsh 本机自身配置损坏（mcp-client 条目 `args:[null]` 拒绝启动）→ 驱动器正确捕获 stderr
  结构化报错（错误即事件 ✓）；修复本机 dsh 的 MCP 配置后即可用。
- 其余引擎无凭据（env 未设、引擎自有 auth 未登录）→ 按约定属 SKIP 范畴，单元测试覆盖
  argv 构建与输出解析。

## 8. 上游契约核验与修正（2026-09-13）

对 14 个引擎逐一比对**官方文档 / 官方源码 / 本机二进制 `--help`**，修正了 8 处与上游
真实契约不符的适配。判据优先级：真实二进制探针 > 官方源码 > 官方文档 > 社区资料。

### 8.1 阻断级：ACP 判别值错误（dsh + hermes）

驱动器按 `params.update.sessionUpdate == "agent_message_text"` 聚合回复文本。
**该字符串在 ACP v1 规范、`@agentclientprotocol/sdk` schema、以及 dsh 二进制里都不存在。**

真实探针（`dsh --profile acp`，本机 0.1.5-rc.1）：

```
initialize  -> {"protocolVersion": 1, "agentInfo": {"name": "deepseek-harness-acp", ...}}
session/new -> d8c971e2-99ff-4b9c-b0aa-50d2f5209059
session/prompt -> {"stopReason": "end_turn"}
sessionUpdate values observed: {"agent_message_chunk": 1, "usage_update": 1}
accumulated assistant text  : '2'
```

即：**dsh / hermes 在修复前永远返回空文本**，而 `backend/tests/fake_harness_engine.py`
的桩当时写的也是同一个错值 —— 单测因此长期全绿，替这个 bug 背了书。
修复：接受 `agent_message_chunk`（v1 标准）/ `agent_message`（v2 草案）/ 旧值别名；
桩改为发规范值；新增两条回归测试钉死契约（`test_acp_text_uses_spec_discriminator`）。

### 8.2 ACP 审批语义

原实现把所有 server→client 请求一律回 `{"outcome":{"outcome":"cancelled"}}`。
规范中 `cancelled` 是**「本回合被取消」的专属应答**；普通拒绝必须从 agent 给出的
`options` 里选一个 `reject_once` / `reject_always` 的 `optionId`，否则合规 agent 会把
回合判为取消并中止，且 `reject_always` 语义被静默丢弃。
修复：优先选 `reject_*` 选项，仅在真的发过 `session/cancel` 时才回 `cancelled`；
未实现的服务端方法改回标准 JSON-RPC `-32601`，不再复用审批应答形状。
回归测试：`test_acp_permission_is_denied_via_offered_option`。

### 8.3 输出解析修正（逐引擎）

| 引擎 | 原假设 | 上游真实契约 | 处理 |
|---|---|---|---|
| **goose** | `turn.completed` / `usage` 事件 | `stream-json` 只有 `message`/`notification`/`error`/`complete`；token 在终态 `complete` 顶层 | 重写解析器；**原实现属不兼容** |
| **copilot** | `--output-format json` = 单对象 | 官方明确是 **JSONL（每行一个对象）**，逐行 schema 未公开 | 逐行扫描候选键；纯文本兜底不再回吐整段 NDJSON |
| **gemini** | `response` 缺失时回退 `stats` | `stats` 是延迟/token 指标，不是答案 | 改为 `response` → `error` → stream-json 帧 |
| **pi** | `message_update.delta` | JSON 模式下增量在 `assistantMessageEvent.delta`，且首行是 `{"type":"session"}` 头 | 两种形状都认；跳过会话头 |
| **qwen** | 无 `--output-format`，`-p` 是「追加到 stdin」 | 0.23+ **有** `--output-format json/stream-json`；`-p` 是**取值**且 stdin 前置拼接 | 投递保持 stdin（兼容本机 0.0.6），解析器容忍纯文本/json 数组/stream-json 三种 |
| **claude** | 读 `result` | 传 `--json-schema` 时结构化结果在 `structured_output` | 两者都读 |
| **cursor** | `-m MODEL` | 官方参数表只列 `--model`（无短名） | 改长名 |
| **omp** | 仓库地址 `acidsugarx/oh-my-pi` | 该 URL **404**；规范仓库是 `can1357/oh-my-pi` | 修正 homepage |
| **codex** | — | 全部旗标与事件形状与实现一致 | 无需改动 |

**未改动但需注意**：`opencode -m` 需要 `provider/model` 形式（裸模型名会被拒）；
其 7.5K 提示词上限是启发式护栏而非厂商标称（npm shim 实为原生 exe，CreateProcess
上限 32767）；`copilot` 工具调用需 `--allow-all-tools`（已作为可选项接入，
默认保持只读保守档）；`claude --max-budget-usd 0.05` 是硬停，真实任务会中途中止。

### 8.4 核验后的实测

```bash
python scripts/e2e_multi_harness.py mock   # A/B 双场景通过（零 token）
python scripts/e2e_multi_harness.py dsh    # ✅ A: "2"   B: meditation_result 提取成功
python scripts/e2e_multi_harness.py omp    # ✅ A: "2"   B: meditation_result 提取成功
```

`dsh` 由「协议不符导致空回复」变为真实可用 —— 这是第 8.1 节修复的直接证据。

