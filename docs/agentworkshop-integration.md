# AgentWorkShop 集成说明(rag-bridge 插件消费契约)

> 本项目作为 [AgentWorkShop](https://github.com/kingdol666/AgentWorkShop) 的**知识持久化与检索插件**后端。
> AgentWorkShop 侧插件:`.AgentWorkShop/plugins/rag-bridge/`(以及 diag-bridge 的报告自动入库)。
> 本文记录 2026-09-07 三系统集成时钉死的端口与端点契约,供两边任一方升级时对照。

## 端口约定(重要)

- 后端 FastAPI:**8770**(不再是默认 8765——该端口在本部署机被无关进程占用;`config.yml` 的 `server.dev.backend_port` 与 `.env` 的 `BACKEND_PORT` 已同步改为 8770)
- Web (Nuxt,TreeFileSystem 文档写盘):**6789**
- 启动:`cd backend && BACKEND_PORT=8770 APP_MODE=prod uv run python main.py`;web:`cd web && BACKEND_PORT=8770 npx nuxt dev --port 6789`

## 被 AgentWorkShop 插件消费的端点

| 用途 | 端点 | 关键约定 |
|---|---|---|
| 健康检查 | `GET :8770/api/v1/health` | `{"status":"healthy"}` |
| 图谱可用性 | `GET :8770/api/v1/graph/health` | `health.available` |
| 检索(主入口) | `POST :8770/api/v1/search/two-stage` | `{query, kb_id?, stage2_top_k?}`;**断言 `body.success`** |
| 文档写盘 | `POST :6789/api/kb/documents/create` | `{kbId, name, content, description?}` → 返回文档 path,作下一步 doc_path |
| 向量索引 | `POST :8770/api/v1/search/index-document` | `{kb_id, doc_path, content, tags}`(content 直传) |
| 结构化经验 | `POST :8770/api/v1/experience/{kb_id}` | `{title, category, problem, solution, key_lessons?, tags?}`;category 枚举见 `experience_models.py` |
| 经验库初始化 | `POST :8770/api/v1/experience/{kb_id}/init` | 幂等 |
| 跨库经验检索 | `POST :8770/api/v1/experience/global-search` | `{query, top_k?}`,零 LLM |
| 图谱关联 | `POST :8770/api/v1/graph/agent-relation` | `{doc_path, target_doc_path, relation_type, reasoning}` |

## 约定的知识库分区

- 库名 **`aw-industrial`**(由插件 ensureKB 幂等创建):存放 AgentWorkShop 诊断报告(`diagnostics/`)与经验(`experience`)。
- 诊断报告入库 tags 约定:`[<产线>, "诊断", "source:diag-bridge"]`;Agent 人工沉淀的经验由 `kb_store` 工具写入,与自动入库按 source 区分,不双写。

## 已知限制

- 限流:per-IP 滑动窗口 600 req/60s(heavy 60),插件侧已做 429 退避;web UI 与插件共享 127.0.0.1 配额。
- 认证:当前 `server.auth.enabled: false`;生产启用后需将 `KB_AUTH_TOKEN` 同步给插件(kv `kb.token`)。
