// == CLAUDE.md ==
// RAG Knowledge Backend — 项目开发规范与指南
// 此文件由 Claude Code 读取，用于理解项目架构和开发约定。
// 每次启动开发会话时自动加载到上下文。

# RAG Knowledge Backend

## 🏗 项目架构

```
backend/
├── app/
│   ├── main.py              # FastAPI 应用入口，注册路由和中间件
│   ├── config.py            # 配置管理器（从 config.yml + 环境变量读取）
│   ├── api/
│   │   ├── __init__.py
│   │   ├── compat.py        # 兼容性导出
│   │   └── routes/
│   │       ├── __init__.py  # 路由注册中心
│   │       ├── health.py    # GET /api/v1/health
│   │       ├── parse.py     # POST /api/v1/parse/file/vt 等
│   │       └── deepagent.py # /api/deepagent/* 智能体端点
│   ├── agent/               # DeepAgent 智能体系统
│   │   ├── deepagent.py     # 兼容性外观
│   │   ├── deepagent_runtime/ # 运行时（服务、模型工厂、构件管理）
│   │   └── deepagent_support/ # 支持工具（沙箱、工具注册）
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # 所有 Pydantic 响应模型
│   └── utils/
│       ├── __init__.py
│       └── paths.py         # 项目路径常量
├── config.yml               # 配置（端口、CORS、LLM、DeepAgent）
├── main.py                  # uvicorn 启动入口
├── pyproject.toml            # 依赖管理和构建配置
├── CLAUDE.md                # ← 你在这里
└── .env.example             # 环境变量模板
```

## 🔗 注册的 API 路由

前端通过 Nuxt 服务器代理调用的后端端点：

| 端点 | 方法 | 用途 | 文件 |
|------|------|------|------|
| `/api/v1/health` | GET | 健康检查 | `routes/health.py` |
| `/api/v1/parse/file/vt` | POST | PDF 上传解析（桩） | `routes/parse.py` |
| `/api/v1/batch/parse/file/vt` | POST | 批量 PDF 解析（桩） | `routes/parse.py` |
| `/api/v1/batch/parse/file/vt/stream` | POST | SSE 流式解析（桩） | `routes/parse.py` |
| `/api/deepagent/` | GET | DeepAgent 信息 | `routes/deepagent.py` |
| `/api/deepagent/artifacts` | GET/POST | 构件管理 | `routes/deepagent.py` |
| `/api/deepagent/artifacts/by-name/{name}/execute` | POST | 按名称执行构件 | `routes/deepagent.py` |
| `/api/deepagent/artifacts/{id}/execute` | POST | 按 ID 执行构件 | `routes/deepagent.py` |
| `/api/deepagent/execute` | POST | 直接执行 DeepAgent | `routes/deepagent.py` |

## 🚀 启动命令

```bash
# Dev 模式（端口 8765，自动重载）
cd backend
APP_MODE=dev uv run python main.py

# Prod 模式（端口 8001，无自动重载）
APP_MODE=prod uv run python main.py

# 指定端口（覆盖 config.yml）
BACKEND_PORT=9000 APP_MODE=dev uv run python main.py
```

## 🧪 测试

```bash
cd backend
uv run pytest tests/

# 健康检查
curl http://localhost:8765/api/v1/health
```

## 📐 开发约定

### 模块分层
- **routes/** — 仅定义路由和请求/响应处理。业务逻辑放在独立函数中。
- **services/** — 业务逻辑层（如 `mineru_service.py`），被路由调用，依赖注入 manager/外部资源
- **agent/** — 所有智能体逻辑。不与路由混在一起。
- **models/** — 只放 Pydantic schema，不放业务逻辑。
- **utils/** — 工具函数（路径解析等）。

### 添加新路由
1. 在 `app/api/routes/` 下创建 `xxx.py`
2. 在 `app/api/routes/__init__.py` 中注册
3. 在 `app/main.py` 的 `include_router` 中添加

### 配置管理
- 所有配置从 `config.yml` 读取（通过 `Config` 类的 `@property` 暴露）
- 不要硬编码端口、URL 等
- 不要直接读取 `.env` 文件（Config 类可扩展为支持）

### API 响应规范
- 成功：返回标准 Pydantic model（`response_model`）
- 错误：返回 `JSONResponse(status_code=4xx/5xx, content={...})`
- 不要使用 `raise HTTPException` 除非是中间件层

### 依赖管理
- 使用 `uv sync` 安装依赖，不要手动 `pip install`
- 新增依赖时用 `uv add <package>` 自动更新 lock 文件
- `pyproject.toml` 是唯一依赖声明源

### 代码风格
- 类型注解必须完整（所有函数参数和返回值）
- 日志用 `logger = logging.getLogger(__name__)` 模块级实例
- 异常不要静默吞掉, 至少 `logger.warning` 记录
- 路径运算统一用 `pathlib.Path`

## 🔄 Git 工作流

- 主分支：`master`
- 功能分支：`feat/xxx`
- Bug 修复：`fix/xxx`
- 提交信息使用 conventional commits 风格

## ⚡ Claude Code 能力

本项目配置已优化 Claude Code 自主开发能力：
- 自动读取 `CLAUDE.md` 了解项目规范
- 模块化结构避免大文件（每个路由文件 < 100 行）
- 清晰的命名空间便于理解上下文
- 统一的 schema 层减少重复
- 配置驱动避免硬编码

## 🧠 持久化记忆系统（MCP Memory）

本项目使用 **MCP Memory 知识图谱** 作为持久化记忆系统，用于跨会话保持项目上下文。

### 记忆存储规范

1. **每次新对话启动时**，必须通过 `mcp__memory__search_nodes()` 或 `mcp__memory__read_graph()` 加载项目记忆，了解已有上下文后再开始工作

2. **需要记住的内容**（写入知识图谱实体）：
   - 项目架构决策和原因（例如：为什么选择某个方案）
   - 模块间关系和依赖
   - 用户偏好和开发约定
   - 当前工作上下文和进度
   - 已发现的问题和修复方案

3. **不需要记住的内容**（代码库中已有的）：
   - 代码级细节（函数签名、类定义、导入路径）— 这些已在 CLAUDE.md 和代码中
   - 临时调试信息
   - git 历史中已记录的变更

4. **记忆操作指南**：
   ```python
   # 创建实体（项目/模块/关键概念）
   mcp__memory__create_entities([
     {"name": "...", "entityType": "module|concept|decision", "observations": [...]}
   ])

   # 创建关系
   mcp__memory__create_relations([
     {"from": "...", "relationType": "depends on|calls|configures|contains", "to": "..."}
   ])

   # 添加观察（追加到已有实体）
   mcp__memory__add_observations([
     {"entityName": "...", "contents": ["..."]}
   ])

   # 检索记忆
   mcp__memory__search_nodes(query="MinerU parse")
   mcp__memory__open_nodes(names=["Backend (FastAPI Python)"])
   ```

5. **每次修改重要架构/流程后**，更新对应的记忆实体观察

6. **文件级记忆**：`C:\Users\87287\.claude\projects\d--codes-ClaudeGPT-rag-project-rag-knowledge\memory\` 目录下的 `.md` 文件作为补充持久化存储（大段文本内容），与 MCP Memory 同步维护。

### 记忆实体命名约定

| 实体类型 | 命名规范 | 示例 |
|----------|---------|------|
| `project` | 项目全称 | `RAG Knowledge Platform` |
| `subproject` | 子项目名+技术栈 | `Backend (FastAPI Python)` |
| `module` | 模块功能名 | `MinerU Integration` |
| `concept` | 概念名 | `Data Flow` |
| `decision` | 描述决策 | `Why add MineruParseService` |

### 跨会话加载流程

```
启动新会话
  └→ 读取 CLAUDE.md（本项目文件）
  └→ mcp__memory__search_nodes(query="RAG Knowledge")
  └→ 加载相关实体观察
  └→ 如有已知的工作上下文，恢复进度
  └→ 开始当前任务
```
