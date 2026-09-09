# Web 层 HTTP API 速查（外部集成用）

> 生成日期：2026-09-09（P2-2 补充）。web `:6789`（Nuxt server routes）。
> backend `:8770` 的解析/检索/经验/图谱/人格 API 自带 OpenAPI：`http://localhost:8770/openapi.json`。
> web 层不生成 OpenAPI，本文覆盖外部集成最常用的 KB 核心操作。
> 端口与存储路径见 `config.yml`（单一配置源）。

## 通用约定

- **字段命名**：camelCase 为准（`kbId` / `docPath`）。自 2026-09-09 起写入类接口同时接受
  snake_case 别名（`kb_id` / `doc_path` 等，自动归一化，camelCase 优先）——
  与 kb-mcp 工具层参数名一致。
- KB 标识 `kbId` 可传 UUID 或库的相对路径名（如 `"高分子双向拉伸文献库"`）。
- **同名知识库被拒绝**（409）：重名会导致向量索引归属错乱，创建时请使用唯一名称。
- 无认证（内网部署）；限流 600 请求 / 60 秒。对外开放请前置网关加鉴权。

## KB 与文档（`/api/kb/*`）

| 方法 | 路径 | 说明 | 关键字段 |
|---|---|---|---|
| GET | `/api/kb/catalog` | 知识库目录（含文档计数） | — |
| POST | `/api/kb/create` | 创建知识库 | `name`, `description?`, `parentId?` |
| PUT | `/api/kb/update` | 更新库元信息 | `kbId`, `name?`, `description?` |
| DELETE | `/api/kb/delete` | 删除知识库 | `kbId` |
| GET | `/api/kb/documents` | 库内文档列表 | `?kbId=` |
| GET | `/api/kb/document` | 单文档详情 | `?kbId=&docPath=` |
| POST | `/api/kb/documents/create` | 新建 Markdown 文档 | `kbId`, `name`, `content`, `description?` |
| PUT | `/api/kb/documents/content` | 更新文档正文（自动重索引） | `kbId`, `docPath`, `content` |
| PATCH | `/api/kb/documents/update` | 更新文档元信息 | `kbId`, `docPath`, `name?`, `description?` |
| PATCH | `/api/kb/documents/tags` | 更新文档标签 | `kbId`, `docPath`, `tags[]` |
| POST | `/api/kb/documents/move` | 移动文档到目标库 | `docPath`, `targetKbId` |
| DELETE | `/api/kb/documents/delete` | 删除文档 | `kbId`, `docPath` |
| POST | `/api/kb/documents/batch-delete` | 批量删除 | `kbId`, `docPaths[]` |
| GET | `/api/kb/documents/by-tag` | 按标签查文档 | `?tag=&kbId?=` |
| GET | `/api/kb/search` | 跨库关键词检索 | `?query=&top_k=` |
| GET | `/api/kb/tags` | 全局标签清单 | — |

## 文件树（`/api/filesystem/*`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/filesystem` | 完整文件树 |
| POST | `/api/filesystem/nodes` | 创建节点（文件夹/文件） |
| PATCH | `/api/filesystem/nodes/{id}` | 更新节点 |
| DELETE | `/api/filesystem/nodes/{id}` | 删除节点 |
| POST | `/api/filesystem/upload` | 上传原始文件 |

## 其他命名空间（web 层亦代理/实现）

- `/api/parse/*` — PDF 解析触发与产物入库（`file-vt`、`save-parsed-files`）
- `/api/experience/{kbId}/*` — 经验库（index/init/search/summary/CRUD/apply/review）
- `/api/graph/*` — 知识图谱（search/stats/build-kb/neighbors/paths 等）
- `/api/soul/*` — 人格系统（init/list/status/ask/qdcvr-ask/learn/train-rl/review/evaluate/…）
- `/api/preview/*`、`/api/config/*`、`/api/system/*`、`/api/health/*` — 预览 / 配置 / 运维

## 快速自检

```bash
# 建库 → 写文档 → 读回（snake_case 字段演示，camelCase 等价）
curl -X POST localhost:6789/api/kb/create           -H 'Content-Type: application/json' -d '{"name":"示例库"}'
curl -X POST localhost:6789/api/kb/documents/create -H 'Content-Type: application/json' \
     -d '{"kb_id":"示例库","name":"doc1.md","content":"# 你好"}'
```
