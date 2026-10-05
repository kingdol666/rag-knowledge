# 双 harness × 双检索道 × 找到/找不到 检索测试报告（2026-09-28）

## 结论

**8/8 格全部通过。** 两种检索方式（librarian 逐级检索、search 向量+内容验证）在 OMP 与
Claude Code 两个 harness 上，"找得到"与"找不到"两类问题均按 skill 契约执行：
MCP 预检先行、流程分层可追溯、Laya/Jev 真实引擎判卷（找到时）、描述层/双道穷尽后
如实返回找不到（找不到时，零编造、不无限检索）。

## 测试矩阵

| Harness | 检索道 | 找得到 | 找不到 |
|---|---|---|---|
| OMP v18.3.5 | search（向量+验证） | ✅ BERT 题（`omp-search-bert.log`）¹ | ✅ 红烧肉题（本目录 `omp-search-hongshaorou.log`） |
| OMP v18.3.5 | librarian（逐级检索） | ✅ Transformer 题¹（`../mode-b-subagent-20260928/omp-transformer.log`） | ✅ 红烧肉题¹（`../mode-b-subagent-20260928/omp-hongshaorou.log`） |
| Claude Code 2.1.278 | search（向量+验证） | ✅ BERT 题（`claude-search-bert.log`） | ✅ 红烧肉题（`claude-search-hongshaorou.log`） |
| Claude Code 2.1.278 | librarian（逐级检索） | ✅ Transformer 题（`claude-librarian-transformer.log`） | ✅ 红烧肉题（`claude-librarian-hongshaorou.log`） |

¹ OMP 三格跑于 skill 精简重写前（契约相同，重写后未变行为）；其余五格跑于重写后的 82 行版本。

## 各格要点

### 找得到（4 格）

| 格 | 检索路径证据 | 判卷 | 答案质量 |
|---|---|---|---|
| OMP×search×BERT | 预检 → MLM/NSP 拆分改写 → 宽网 30 候选 → 全文读取 → judge | real Laya，criterion=evidence | 80/10/10 遮蔽策略+消融数值，引 §3.1/§5.1/Table 8 |
| OMP×librarian×Transformer | **task 派 `LibrarianRetrieval` subagent** → 13 书架/158 篇全文 2.96M 字符 → 435 段全判 → 376 幸存 | real Laya，金标 1706.03762 双副本 0.9206/0.9063 | 机制主干/incidental 命中分层，带完整 Search Paths |
| claude×search×BERT | 预检 → 宽网 → `kb_doc_read` 全文 → 判卷（MCP 全通） | real Laya | 逐字引用原文（含 "see itself" 动机句、Table 8 全策略数值） |
| claude×librarian×Transformer | 预检 → subagent 走 L0-L4（19 书架/160 描述/6 候选全文）→ **subagent 上下文压缩丢 judge 工具，主 agent 核实后代跑 L5**（0.7182/0.8426 幸存）→ 作答 | real Laya，2/2 段 kept | Attention 公式/√d_k 缩放理由/多头 h=8 逐字引用，偏离处如实披露 |

### 找不到（4 格）—— 全部如实早退/如实返回，零编造

| 格 | 早退位置 | 关键证据 |
|---|---|---|
| OMP×search×红烧肉 | 双语向量变体 + Laya 门后 **0 有效命中** | 闸门放行 2 段经内容复核均为词形巧合（warmup-steps 图注 0.9134、《傲慢与偏见》"white soup" 0.7208），agent 质量复检推翻引擎假阳性并如实披露；未升级 librarian（遵守指令） |
| OMP×librarian×红烧肉 | L1/L2 描述层（~1 分钟） | 19/19 库+11 可能库 36 描述全读，0 候选即停；如实披露 8 库仅凭描述剪枝 |
| claude×search×红烧肉 | 向量宽网 10 命中全无关 | 逐条给出无关原因（"steps" 语义漂移 0.476×5、图片路径残留、短内容警告），按指令不进 librarian |
| claude×librarian×红烧肉 | L3（描述层+有界头部读取） | L0 19/19 → L1 全 out_of_scope → L2 19 描述 → L3 头部读取解决 10 个不可信描述 → 0 候选即停，未切向量道未编造 |

### 交叉发现（两个 harness 独立互证）

1. **孤儿标签陷阱**：`.tags.json` 存在 `红烧肉/家常菜/烹饪技巧/炒糖色…` 8 个零引用标签——
   claude 两格各自独立发现并正确判定"标签词汇表 ≠ 可检索内容"。建议择机
   `kb_tags_cleanup(dry_run=true)` 清理。
2. **Laya 假阳性实例**：对纯噪声片段（warmup 图注）给出 0.91 放行分——subagent 的
   内容质量复检层（契约 L6/Phase 3）是必要的最后防线，本次实测真实拦截。
3. **Corpus-Chunks800 空文档库**：doc_count=0 但向量索引残留（命中 0.71-0.80、正文
   400/404）——旧账，建议重建或清理该库索引。

## 测试过程中发现并修复的环境/平台缺陷

1. **Claude Code headless（`-p`）MCP 权限白名单缺失**（4 份 `*.preperm.log` 为证）：
   MCP 已连接但 `kb_get_documents/kb_doc_read/kb_laya_judge/kb_project_status` 不在
   allow 规则里，headless 权限提示无法批准 → 一律拒绝。agent 们行为分化正确：一份
   如实报"blocker"拒答（librarian-transformer.preperm），三份误判为"未连接"后回退
   磁盘直读（结果正确但违反 MCP-first，已如实自我披露）。
   **修复**：`.claude/settings.local.json` 预授权全部只读 `mcp__kb-mcp__*` 工具 +
   `kb_project_start`（预检自愈）。修复后 4 格重跑全过。
2. **web :6789 测试中途崩溃 + backend 双实例**（8765 旧实例 + kb-mcp 自动拉起的
   8771）。已清理游放实例并重启 web；`kb_project_start` 白名单化后，未来 headless
   会话可自愈拉起。web 单点依赖（所有读路径走 Nuxt 代理）是更根本的结构问题，
   建议后续评估 kb-mcp 直连 backend。
3. **OMP 派 subagent 失败（`No model selected`）**：宿主未给 agent 模板配模型。
   skill §6 的"无 subagent 工具则进程内自执行"兜底在 3 次失败中全部正确生效且
   如实披露。属 OMP 侧配置项，非平台缺陷。

## MCP 启动加载机制与"作业前确保"（2026-09-28 深夜补测）

**启动加载机制（查证结论）**：kb-mcp 是 **stdio 传输、每客户端会话各自 spawn** 的
本地 MCP 服务——`.mcp.json`（Claude Code / chat API 的 claude-agent-sdk）、
`.omp/mcp.json`（OMP）、`.zcode/mcp.json`（ZCode）三份配置用同一条命令
`uv run --directory kb-mcp python server.py` 在各自会话启动时拉起独立实例；
server.py 的 `main()` → `_startup_health_check_and_launch()` 启动钩子先探测
backend/web，若挂了则以 headless 方式自动拉起并等待 ~45s 就绪，然后才
`mcp.run()` 接受连接（这就是"先启动服务链、已启动则直接复用"的幂等语义所在）。
另支持 `--http` SSE 模式（KB_MCP_HTTP_PORT，默认 8000）但当前各 harness 均
未使用。

**标准前置检查**：`python scripts/mcp_ensure.py --config .mcp.json --config .omp/mcp.json --config .zcode/mcp.json`
——按配置原样命令 spawn 探活实例 → 真 MCP 握手（initialize/tools/list）→
确认 95 个工具与关键工具在位 → 轮询 backend/web 健康端点 → 全绿 exit 0。
幂等可重复，任何 harness 作业前先跑一次。
（脚本调试期修掉两个自坑：stderr 接 PIPE 无人读会塞满管道卡死子进程 →
DEVNULL + 看门狗强杀；`time.time()` 与 `perf_counter()` 两个时钟基准混用
导致超时条件永假 → 统一 `time.time()`。）

**ensure ALL GREEN 后的简单检索实测（同题换题各一道，均为快车道）**：
- claude（CoRoT 延伸期）：✅ "till March 2013" 逐字引用 + 文档来源 + 预检/宽网/
  逐段核验轨迹 + Corpus-Chunks800 副本 400 读失败如实披露，置信 P0（`simple-claude.log`）
- omp（BERT 分词器）：✅ WordPiece/30,000 逐字引用 + Laya 0.6767 + 检索轨迹
  queries=3/candidates=4/survivors=3，并披露引擎否决的干扰项（attention 论文
  0.2255 的 WMT 32k 词表陷阱）与库外事实（bert-base-uncased 实际 30,522）（`simple-omp.log`）

## 工件索引

- 本目录：claude 四格 + omp-search-红烧肉 + `*.preperm.log`（权限缺陷证据）+ web-restart.log
- `../mode-b-subagent-20260928/`：OMP librarian 双题 + OMP search BERT
- 会话转录：`~/.omp/agent/sessions/--D--codes-ClaudeGPT-rag_project-rag-knowledge--/`、
  `~/.claude/projects/d--codes-ClaudeGPT-rag-project-rag-knowledge/`
