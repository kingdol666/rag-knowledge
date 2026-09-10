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

## 6. 本机实测记录（2026-09-10，第二轮全量实测）

**已装 12/14**（claude / cursor / hermes 未安装 —— 前端以 ❌+红标+置灰删除线差异化渲染并禁用）。

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
