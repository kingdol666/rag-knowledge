# E2E 全链路实机验收报告 — master@8f09799b（2026-11-17）

## 0. 环境与干净启动

- 版本：`master` 最新提交 `8f09799b`（分支已全量收拢：master = feat/soul-persona-system）
- 旧进程清理：anaconda 旧后端(8771)、nuxt(6789)、kb-mcp(8000)、2 个 laya_worker 孤儿、torch DLL 占用链全部 taskkill /T
- 陈旧配置修正：`.env` 的 `BACKEND_PORT=8771`（旧端口）→ `8770`（对齐当前 config.yml）
- venv 修复：此前中断的 uv sync 把 torch dist-info 撕成半删除态（modelscope 导入链崩溃）；停服后补完 `uv sync --frozen`（torch 2.12.1+cu130 手工残留 → 锁定的 2.11.0+cu128），`uv sync` 现已幂等
- 启动：`project_manager.start_project` headless（backend 先行 → web → kb-mcp --http），全部监听干净端口

| 服务 | 端口 | 健康状态 |
|---|---|---|
| FastAPI backend | 8770 | healthy，vector ready / embedding available / BM25 ready |
| Nuxt web | 6789 | HTTP 200 |
| kb-mcp SSE | 8000 | `/sse` 握手正常（event: endpoint） |

## 1. 全栈冒烟（scripts/dev_smoke.py，端口已对齐 8770）

**21/21 PASS**：backend 12 项（health/meditation×5/config/graph/search/experience/soul/debug-paths/vector）、web 页面 3 项、web API 5 项（harnesses/models/diagnostics×3）、chat SSE（mock 引擎 events+result）。

## 2. 真实案例 E2E（review/e2e-master-20261117/e2e_demo.py，14/16 PASS）

真实 arXiv PDF（`corpus/multi-domain-docs-20261101/science-en/bert_pretraining.pdf`）：
MinerU 真实解析 13.0s → 65,653 字符 Markdown + 16 张图 → save_parsed 入库（A5 门）→ 自动建索引 0.8s 可检索（122 chunks，A6-V 门）→ 检索/整理/回答全链路。演示库**保留**：`实机演示-E2E-20261117-194145`（kb_id 6789ebf9-…）。

| 检查 | 结果 | 证据 |
|---|---|---|
| kb_create（MCP） | PASS | kb_id 6789ebf9 |
| MinerU 真实解析 | PASS | 13.0s / 65,653 chars / 16 images |
| kb_doc_save_parsed（A5） | PASS | 实机演示-E2E-20261117-194145/bert_pretraining.md |
| A6-V 自动索引可检索 | PASS | 0.8s 出hit（异步索引，重试窗口内） |
| 英文 gold rank1 | PASS | score 0.712，top1=bert 文档 |
| 中文跨语言 rank1 | PASS | 掩码语言模型查询 → 同文档 |
| kb_search_stats | PASS | chunk_count=122 |
| 目录可见性 kb_list | PASS | 演示库在目录中 |
| two-stage（BM25+向量+图谱） | PASS | total_results=5 |
| kb_doc_update_tags | PASS | 工具成功 |
| 已知缺陷复现：get_by_tag 注册表缺口 | 已复现 | count=0（文档级写入成功、全局注册表滞后） |
| kb_doc_update_meta 改名 | PASS | 工具成功 |
| 改名内联卫生（向量元数据标签） | **FAIL（真缺陷）** | 见 §3-1 |
| force reindex 完成 | PASS | task done |
| reindex 后标签一致性 | **FAIL（同上缺陷）** | 见 §3-1 |
| 回答层 KB 增强回答（claude） | PASS | 149.8s / 8 工具调用；正确答出 MLM+NSP 并引用库内文档原文 |

create 路径延迟微测：一次性小库 `kb_doc_create` → **0.7s** 可检索（同步自动索引）。

## 3. 发现的缺陷（本轮实证，均与论文 E2 的诚实披露一致）

1. **MCP 改名路径缺内联卫生（真缺陷，可复现）**：`kb_doc_update_meta` 改名后，磁盘文件、`.knowledge-base.yml`、树注册表三源均为新名，但**向量 chunk 元数据里的 doc_path 仍是旧名**，且 `kb_reindex(force)` 完成后依旧不变；新会话搜索 0.8s 即返回旧标签。检索内容不受影响（回答层引用正常），但引用/溯源展示的文档名会陈旧。此前 run4 轮修复的"rename 三步卫生"只落在 web 层 `update.patch.ts`，MCP 路径未覆盖。建议：把 web 层同名 hygiene 镜像到 MCP 改名路径，或让 reindex 重建时以注册表当前路径刷新元数据。
2. **全局标签注册表滞后 + 跨库泄漏复现**：update_tags 成功后 `kb_doc_get_by_tag` 计数 0；只含 BERT 一篇的库 `kb_tags_list` 返回其他库的标签（Toolformer/医学影像等）。与论文 E2"orphan tags + cross-library registry leak"一致。
3. **（观察项）two_stage 图谱候选跨库**：kb_scoped 搜索的 stage1 graph 候选包含其他库文档（`source: "graph"`），属图谱邻居扩展的设计行为，但建议在返回中显式标注跨库来源。
4. **（运维）`uv run` 在拉取新 master 后会自动重同步 venv**；若 venv 中存在非 uv 安装的包（本机 torch 曾为手工 cu130），同步会以锁文件为准改写——需在服务停止窗口进行，否则 DLL 锁导致中断式损坏（本次即此成因）。

## 4. 实机演示入口

- Web UI：http://127.0.0.1:6789 （知识库页可浏览 `实机演示-E2E-20261117-194145`）
- Chat：http://127.0.0.1:6789/claude-chat （kbEnhanced 勾选、选择演示库即可提问）
- API：backend http://127.0.0.1:8770/api/v1/… （Bearer = .env 的 MCP_AUTH_TOKEN）
- MCP SSE：http://127.0.0.1:8000/sse

## 5. 诚实边界

- 本轮所有实验数字来自当次真实运行；未改动任何既有实验数据。
- 回答层为单问题单引擎（claude）演示，非统计性评测。
- 缺陷 3-1/3-2 未在本轮修复（定位+复现证据已留档），与论文当前"explicit failure visibility"的表述一致。
