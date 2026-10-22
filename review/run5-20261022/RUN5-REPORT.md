# Run 5 报告（2026-10-22 夜）：设计符合性 · 复现性 · 全功能/API/harness · 启动验证 · 提交推送

> 工件：`run5_probe_results.json` · `agent_chat_retry.json` · `run5_probe.log` ·
> `benchmark-suite/results/a_retrieval_regression.json`（复跑再生成）。

## 1. 系统设计符合性（US-401）

**结论：符合设计承诺，无架构性偏差。** 逐项对账：
- 三服务拓扑（web 6789 代理+文档层 / backend 8771 向量·图·经验·SOUL / kb-mcp stdio+HTTP 8000）：活体进程与端口核验一致；本轮受控重启演练亦验证了"backend 先行"拉起序。
- 五层存储（L1 文件/L2 树/L3 注册表/L4 Chroma/L5 Neo4j）：Chroma 25 collection 2879 chunks（CS 库）直读在册；注册表 venv 直读 21 库（UUID 与探针金标一致）。
- 工具面 95（kb 42/exp 26/soul 20/其他 7）：`tools/list` 当日实测一致。
- 检索分层契约（服务端 gather/judge/read/预算门 + workflow 提示层）：图书管理员车道零越车道工具，与契约一致。
- **启动路径健壮性偏差（已当场修复，非架构缺陷）**：多日连跑产生双实例漂移 + 令牌文件过期（见 §4），属运维态劣化，设计本身的启动/自愈机制（SOP/看门狗/login_refresh）覆盖。

## 2. 实验结果与复现性（US-402）

- `TEST-RESULTS/verify.py`：**PASS**——论文每个 grounded/strict/cited/chunk/时延/成本主张从冻结 run `run-20261013T094350Z-5f9faac` 复算命中（30 格成本求和 17.2454 = manifest）。**复现性成立**。
- 158 检索回归探针：复跑首得 **0/15**（见 §4 排障），双层修复后 **15/15**、金标全部 rank 1——复现链修复。
- 冻结 manifest：`sha256sum -c` 仍为 3 OK / 3 既知漂移（n8a/n8b/n8c_eval.tex），未扩大。
- 论文论据结论不变：30 单元网格/E4/E6/E7/E5b 可作主证据；探针 15/15 行有可执行再生路径。

## 3. 全功能 · 对外 API · harness 执行（US-403）

| 面 | 检查 | 结果 |
|---|---|---|
| 平台自检 | `scripts/dev_smoke.py` | **21/21 PASS**（harness diagnostics: mock/claude/codex/dsh + chat SSE + 平台端点） |
| MCP 工具面 | tools/list（stdio 冷启动 spawn） | **95 工具**正常 |
| 对外 chat API | `/api/claude/chat` kbEnhanced（SSE） | 图书管理员车道金标命中（InstructDS，47.8s），零越车道工具 |
| 对外 agent API | `/api/kb/agent/chat`（web 层，claude 原生） | **真执行 35s**：原生 harness 列出全部 21 库名单（success/tools_used/session_id/num_turns 齐全）；注意该端点在 web(6789) 不在 backend(8771) |
| 管理作业 | 一次性库七步冒烟 | **7/7 PASS**（create→入文→索引→向量检索命中→**改名内联卫生（run-4 修复持续有效）**→批量索引/删除→标签 dry-run→清理零残留） |

## 4. 启动验证（US-404）——受控重启演练实战化，排掉一个真故障

初查 158 探针 0/15 暴露双层叠加故障，全部定位并修复：

1. **服务层（陈旧双实例）**：backend 同时存在 anaconda 老进程（占 8771，其 Chroma 客户端与磁盘 HNSW segment 失配——日志 `Error creating hnsw segment reader: Nothing found on disk` 自 10-22 14:15 爆发）与 venv 进程；kb-mcp 同样双实例。按 SOP 全杀后 **backend(venv) 先行拉起 → kb-mcp(venv) 拉起**，curl 直击 8771 检索立即恢复正常（attention 段落命中）。
2. **探针层（令牌优先级陷阱）**：`lib.auth_token()` 优先取 `storage/loop-auth.json` 的登录令牌（已过期，curl 实证 401）并当作 MCP_AUTH_TOKEN 注入 stdio server → web 401 → `kb_list`/`kb_exists` 全空 → 探针报 "knowledge base not found"。用库内 `login_refresh()` 重新登录刷新令牌后 **15/15**。教训：**backend 重启后必须刷新 loop-auth.json（login_refresh 或环境变量 RAG_BENCH_TOKEN），否则所有 lib 系探针假性全灭**。
3. 排障中甄别并排除的假线索：8770 过时端口配置（kb-mcp 实际经 .env BACKEND_PORT=8771 覆盖）、tree_fs_root 相对路径（paths.py 已锚定仓库根）、localhost/IPv6 分裂（无）。

重启后全量复核：三服务健康、kb_list 21 库、检索 15/15、dev_smoke 21/21。

## 5. 提交推送（US-406）

分四个逻辑提交推至 `origin/feat/soul-persona-system`（见 git log）：
1. `fix(rename)`：update.patch.ts 内联索引卫生（run-4 修复）
2. `fix(platform)`：15-skill 审读修订 + mock subtype + dev_smoke stream/timeout + kb-mcp 跟页
3. `paper(kbs)`：论文工作区同步（eval 修订/补充材料/highlights）
4. `test+chore`：runs 1-5 验收与演示证据（review/*、benchmark 再生产物、.omc 状态、skills-archive 归档）

## 6. 生产判定（更新）

系统在单机边界内**继续满足投产条件**；本轮新增运维红线两条：
- backend 重启后必须 `login_refresh()` 刷新 loop-auth.json，否则 lib 系基准/探针全灭（探针层假故障，服务本身正常）。
- 服务连跑多日会出现双实例/HNSW 段失配劣化——158 探针作周期健康检查可直接暴露；修复=SOP 重启（backend 先行）。
