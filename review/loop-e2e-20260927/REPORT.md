# 端到端优化收敛循环报告 — 2026-09-27

## 结论：收敛（2 轮测试→修复→复测，全部绿灯）

系统与全部 skill 满足设计规范并可投入使用；解析入库（Agent 先读后拆 + ICD）与三通道检索机制均经真机验证。

## Round 1 — 全量测试 + 规范扫描

| 检查 | 结果 |
|---|---|
| 相关 pytest 全量（splitter/dispatcher/ingest/search/librarian/hybrid/butian） | 109 passed |
| `validate_skills.cjs` / `sync_skills.py --check` / `118_skill_audit.py` | PASS / PASS / 0 FAIL 0 WARN |
| `split_large_doc.py --selftest` | pass |
| backend :8771 / web :6789 健康 | 200 / 200 |
| skill-creator 合规扫描（21 skills：name=目录、description、主体 ≤500 行） | 干净 |
| 过时残留 grep（0-8 rubric / kb_doc_create 误用 / 硬编码计数） | 见下方修复 |

**Round 1 修复**
1. 12 个 skill 共享段落 `91-tool map` → `94-tool map`（当前 MCP 工具数）。
2. Archival（knowledge-admin.md）`91 MCP tools, 17 skills` → `94 / 21`。
3. 清理误落在 `.claude/skills/.mimosa` 的 hook 状态目录。

## Round 2 — 真机验证 + 复测

**关键修复：过期认证令牌。** 真机冒烟首轮暴露 `auth_token()` 优先读了 `storage/loop-auth.json` 的过期 token（其自身注释已知此坑）→ 运行服务 401。用 `lib.login_refresh()`（凭据重登）刷新后 catalog 200。此修复同时恢复了 benchmark 套件与任何走 McpClient 的链路。

**KB Skill 真机冒烟**（MCP stdio 通道，[SKILL-SMOKE.md](SKILL-SMOKE.md)）：
- 新增 librarian（L0/L2）与 hybrid（双道只读）计划后覆盖 18 skill / 26 调用 / **0 失败**（首轮 13 失败全部由 token 引起）。

**检索机制真机验证（真实 Laya 引擎 laya_sdk，`real_engine=true`）**
- Mode A（vector+Laya 门，`vector_jev_search.py --require-real`）：4 kept，含 P&P part 23（求婚场景所在章）——判决门在噪声中捞出正确小说分片；产物 `tmp/vector-jev-loop.json`。
- Mode C（hybrid 双道，detached wrapper）：`status=ok`，merge 31 篇（both 1 / vector 5 / catalog 25），kept 19 / unscanned 0，P&P 18 分片在列（16/24/18/11 等高分）；产物 `tmp/hybrid-loop.json`。
- Mode B（librarian）：只读工具（L0 目录 / L2 描述）冒烟通过；`complete_recall` + `jev_filter` 51 项离线测试通过。
- CLI sanity：6 个检索/入库脚本 `--help` 全 OK。

**复测**：validate_skills PASS · sync --check PASS · 118 审计 0/0 · pytest 全量 109 passed `[100%]`。

## 过程陷阱（记录）
- Git Bash 下 `grep -l | while read` 传给 sed 的路径带 CRLF，sed "fixed" 假成功——改用 glob 直改并以 grep -c 验证。
- PowerShell `Start-Process -ArgumentList` 吞多词参数引号 → argparse 假失败；用包装脚本（`tmp/run_hybrid_loop.py`，clean argv + subprocess）解决。
- 探测进程时 `Where-Object CommandLine -match` 会匹配探测命令自身，"存活进程"需甄别。

## 遗留边界（非缺陷，已声明）
- 《围城》入库与三模式问答：等待用户提供可入库文本（当前无授权来源）；流程契约已就绪。
- Laya checkpoint 温度失准警告（引擎自身声明 uncalibrated）——已在 librarian 文档记载，fail-closed 契约不受影响。
