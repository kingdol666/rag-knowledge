# E2E 全链路实机验收报告 — master@01793b31（2026-11-17，含缺陷复核轮）

## 0. 环境与干净启动

- 版本：`master` 最新提交（01793b31；分支已全量收拢：master = feat = origin 双同步）
- 旧进程清理：anaconda 旧后端(8771)、nuxt(6789)、kb-mcp(8000)、laya_worker 孤儿×3、torch DLL 占用链
- 陈旧配置修正：`.env` `BACKEND_PORT=8771` → `8770`（对齐当前 config.yml；CLAUDE.md 的 8765 亦过时）
- venv 修复：中断的 uv sync 曾把 torch dist-info 撕成半删除态；停服补完 `uv sync --frozen`（→ 锁定版 2.11.0+cu128），现已幂等

| 服务 | 端口 | 健康状态 |
|---|---|---|
| FastAPI backend | 8770 | healthy，vector ready / embedding available / BM25 ready |
| Nuxt web | 6789 | HTTP 200 |
| kb-mcp SSE | 8000 | `/sse` 握手正常 |

## 1. 全栈冒烟（dev_smoke.py，端口已对齐 8770）

**21/21 PASS**。

## 2. 真实案例 E2E（最终轮 **16/16 PASS**）

真实 arXiv PDF（bert_pretraining.pdf）：MinerU 真实解析 26.4s → 65,653 字符 + 16 图 → save_parsed（A5）→ 自动索引 1.0s 可检索（122 chunks，A6-V）→ 检索/整理/回答全链路。演示库**保留**：`实机演示-E2E-20261117-211320`（kb_id d1ff56c4-…）。

| 检查 | 结果 | 证据 |
|---|---|---|
| kb_create（MCP） | PASS | kb_id d1ff56c4 |
| MinerU 真实解析 | PASS | 26.4s / 65,653 chars / 16 images |
| kb_doc_save_parsed（A5） | PASS | …211320/bert_pretraining.md |
| A6-V 自动索引可检索 | PASS | wait=1.0s |
| 英文 gold rank1 | PASS | score 0.712 |
| 中文跨语言 rank1 | PASS | 同文档 |
| kb_search_stats | PASS | chunk_count=122 |
| 目录可见性 | PASS | kb_list 含演示库 |
| two-stage（BM25+向量+图谱） | PASS | total_results=5 |
| kb_doc_update_tags | PASS | 工具成功 |
| get_by_tag 读回 | PASS | count=1（tag=bert） |
| kb_doc_update_meta 改名 | PASS | 工具成功 |
| 改名内联卫生 | PASS | **1.1s** 新标签可检索（缓存旁路查询） |
| force reindex 完成 | PASS | task done |
| reindex 后标签/排名稳定 | PASS | top1=新名，wait=1.0s |
| 回答层 KB 增强回答（claude） | PASS | 172.2s / 6 工具；MLM+NSP 引用库内文档 |
| create 路径延迟微测 | PASS | 0.7s 可检索（一次性小库） |

## 3. 三项"缺陷发现"的复核结论（全部撤销，附实证）

复核方法：直查 chroma 元数据与磁盘 YAML → 追溯 web 路由/服务源码 → 受控重命名周期实验。

1. **"MCP 改名缺卫生" — 撤销**。`update.patch.ts` 的 run-4 卫生完整生效：本轮实测 `index_hygiene` 显示旧向量清理成功、图节点删除、**新标签 0.6–1.1s 即可检索**，force reindex 后稳定。此前 E2E 的"旧标签"来自后端**约 30s 滑动检索缓存**：同名查询反复轮询会不断刷新滑动 TTL（永不过期），是测量伪影而非数据损坏——静默 35s 后查询即返回新标签；直查 chroma 证实 122 chunks 元数据始终正确。与 run4 已识别的"30s 检索缓存测量伪影"同类。
2. **"标签注册表缺口" — 撤销**。测试用标签 `demo` 命中平台的垃圾标签过滤器（`\b(test|demo|debug|scratch|tmp)\b`，K3 修复）而被按设计丢弃（YAML 实写 `tags:[bert,nlp]`）；`get_by_tag('bert') count=1` 证明写→读链路正常。
3. **"kb_tags_list 跨库泄漏" — 撤销**。该 MCP 工具签名无 kb_id 参数，文档即"列出系统全部注册标签"（全局注册表 `.tags.json`），属按设计行为；此前"泄漏"系向全局工具误传 kb_id。

**最终系统判定：无未解决的严重 bug；三服务在干净端口全绿常驻。**

## 4. 实机演示入口

- Web UI：http://127.0.0.1:6789 （浏览 `实机演示-E2E-20261117-211320`）
- Chat：http://127.0.0.1:6789/claude-chat （kbEnhanced + 选演示库）
- API：http://127.0.0.1:8770/api/v1/… （Bearer = .env MCP_AUTH_TOKEN）；MCP SSE：http://127.0.0.1:8000/sse

## 5. 诚实边界与运维备忘

- 回答层为单问题单引擎演示，非统计评测；未改动既有实验数据。
- 运维 SOP：拉新 master 后 `uv run` 会自动按锁重同步 venv——必须在**服务停止窗口**执行，否则 DLL 锁导致中断式损坏（本次成因）；修复链=杀全链+孤儿 → `UV_LINK_MODE=copy uv sync --frozen`。
- 测量方法论：检索缓存约 30s 滑动 TTL；对改名/重索引后的验证必须用**唯一查询串**或等待静默期，连续轮询会使滑动缓存永不过期。
