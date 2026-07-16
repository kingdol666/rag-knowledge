---
name: knowledgebase-init
description: >
  知识库系统全链路交互式安装部署向导。
  当用户输入 /knowledgebase-init 或提到"初始化知识库"、"安装知识库"、"部署知识库"、
  "setup knowledge base"、"install rag knowledge" 时触发。
  交互式引导用户完成全套部署，每个关键配置都询问用户后再设定。
  Triggered by: /knowledgebase-init, 初始化知识库, 安装知识库, 部署知识库, 知识库启动,
  setup knowledge base, install rag knowledge, deploy KB, start knowledge base,
  kb init, knowledgebase setup wizard, 知识库安装向导, 配置知识库, 引导安装知识库.
---

# Knowledgebase Init — 全平台交互式部署向导

**执行者：此技能由 Archival agent 执行** — 必须委托 `Agent(subagent_type="archival", ...)` 执行。

## 核心原则

- 🔄 **全平台兼容** — Windows / Linux / macOS 三平台统一流程
- 💬 **交互式配置** — 每个关键参数都先询问用户，用户回答后再配置
- 🚫 **不擅自决定** — 涉及端口、路径、密码等配置，必须用户确认
- ✅ **每步验证** — 完成一个阶段立即验证，失败即时反馈

## 工作流程

### Phase 0 — 平台检测

首先确定用户的操作系统（Bash: `uname -s` 或 `echo %OS%`），后续所有命令自动适配。

### Phase 1 — 环境预检

```
Bash: 检测以下命令是否可用:
  uv --version
  node --version
  git --version
```

输出检测结果表格。如果有缺失，**精准给出安装命令**：

| 系统 | 缺失 uv | 缺失 node |
|------|---------|-----------|
| Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `curl -fsSL https://deb.nodesource.com/setup_20.x \| sudo -E bash - && sudo apt-get install -y nodejs` |
| macOS | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `brew install node` |
| Windows | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` | https://nodejs.org/ 下载安装包 |

所有核心依赖满足后才进入下一步。

### Phase 2 — 项目确认

```
【询问用户】
项目要安装在哪个目录？
默认: ~/rag-knowledge (即 /home/用户名/rag-knowledge 或 C:\Users\用户名\rag-knowledge)

1. 直接回车 → 使用默认路径
2. 输入自定义路径

用户回答后，记录 RAG_ROOT 变量。
```

```
Bash: 检查 RAG_ROOT 是否已存在
如果已存在:
  【询问用户】
  项目目录已存在: RAG_ROOT
  1. 更新 (git pull) → 保留现有配置
  2. 重新安装 → 删除目录后重新 clone
  3. 跳过 → 保持现状

如果不存在:
  Bash: git clone --recursive https://github.com/kingdol666/rag-knowledge.git <RAG_ROOT>
```

### Phase 3 — 依赖安装

```
【告知用户】
接下来将安装所有依赖，包括:
  - Backend (Python): FastAPI, torch, transformers, mineru (~3GB)
  - Web (Node.js): Nuxt 3, Ant Design Vue (~500MB)
  - kb-mcp (Python): FastMCP, httpx (~100MB)
  - BGE-M3 嵌入模型 (~2.2GB)

总计约 6GB 磁盘空间，安装时间取决于网络速度。

是否继续？[Y/n]
```

用户确认后执行：
```
Bash: cd <RAG_ROOT> && node command/ragctl.js setup
```

等待安装完成。如果超时或失败，给出具体错误信息和解决方案。

### Phase 4 — 交互式配置

**逐个询问用户，不批量跳过：**

```
【询问 1】运行模式
  1. dev  — 开发模式 (backend:8765, web:6789, 热重载, 控制台日志)
  2. prod — 生产模式 (backend:8001, web:3000, 无热重载, 后台运行)
  请选择 [1/2，默认: dev]:

【询问 2】是否需要知识图谱功能？
  知识图谱需要 Docker + Neo4j 容器（额外约 500MB 磁盘）
  1. Y — 启动 Neo4j（推荐，支持图谱检索和文档关联）
  2. n — 跳过（图谱功能将不可用）
  请选择 [Y/n]:

【询问 3】是否需要修改默认端口？
  当前: backend=8765, web=6789 (dev 模式)
  1. 保持默认
  2. 自定义端口
  请选择 [1/2]:

如果选择自定义:
  后端端口? [默认 8765]:
  前端端口? [默认 6789]:

【询问 4】是否需要配置 HuggingFace 镜像加速？
  国内用户推荐 hf-mirror.com 加速模型下载
  1. Y — 使用国内镜像
  2. n — 直连 HuggingFace
  请选择 [Y/n]:
```

根据用户回答写入 .env：
```bash
cat > <RAG_ROOT>/.env << EOF
APP_MODE=<用户选择的模式>
BACKEND_PORT=<用户选择的端口>
WEB_PORT=<用户选择的端口>
PYTHONUTF8=1
$( [ "$USE_MIRROR" = "Y" ] && echo "HF_ENDPOINT=https://hf-mirror.com" )
EOF
```

### Phase 5 — Neo4j 启动（如果用户选择需要）

```
Bash: cd <RAG_ROOT> && docker compose up -d neo4j

Bash: 轮询检查 127.0.0.1:7687 直到可用（最多等待 60 秒）
```

### Phase 6 — ragctl 全局注册

**跨平台自动注册：**

| 平台 | 命令 |
|------|------|
| Linux/macOS | `ln -sf <RAG_ROOT>/ragctl ~/.local/bin/ragctl && chmod +x ~/.local/bin/ragctl` |
| Windows | `copy <RAG_ROOT>\ragctl.bat %USERPROFILE%\.local\bin\ragctl.bat` |

```
Bash: 验证 ragctl 可用性
ragctl --version
```

如果未生效，提示用户重启终端或执行 `export PATH="$HOME/.local/bin:$PATH"`。

### Phase 7 — 启动服务

```
Bash: cd <RAG_ROOT> && ragctl up
```

等待服务就绪（后端约 30 秒，前端约 20 秒），每 2 秒输出进度。

**启动后验证：**
```
Bash:
  curl -s http://localhost:<BACKEND_PORT>/api/v1/health
  curl -s -o /dev/null -w "%{http_code}" http://localhost:<WEB_PORT>/
  curl -s http://localhost:<BACKEND_PORT>/api/v1/mineru/status
```

### Phase 8 — MCP 最终验证

```
使用 MCP 工具进行端到端验证:
  mcp__kb-mcp__backend_status()
  mcp__kb-mcp__kb_list()
  mcp__kb-mcp__kb_graph_health()
  mcp__kb-mcp__kb_search(query="test", top_k=3)
```

### Phase 9 — 安装完成报告

```
══════════════════════════════════════════════════════════
  ✅ RAG Knowledge Platform 安装完成！

  📊 服务状态:
     Backend:  http://localhost:8765 ✅ healthy
     Web UI:   http://localhost:6789 ✅ online
     Neo4j:    bolt://localhost:7687 ✅ available
     MinerU:   OCR ready ✅

  🔧 全局指令 (任意终端可用):
     ragctl status    查看服务状态
     ragctl logs      查看实时日志
     ragctl down      停止服务
     ragctl check     环境检查

  🌐 打开 Web UI: http://localhost:6789
  🤖 打开 Claude Chat: http://localhost:6789/claude-chat

  🎉 13 skills + 74 MCP tools 已就绪！
══════════════════════════════════════════════════════════
```

## ⚠️ NEVER

| ❌ | ✅ |
|----|----|
| 不问用户就覆盖已有配置 | .env 存在时先展示当前值，询问是否修改 |
| 跳过预检直接安装 | Phase 1 必须所有核心依赖通过 |
| 不检测平台就用 Linux 命令 | Phase 0 先确定平台，后续全部适配 |
| 用户选了 n 还强行装 Neo4j | Phase 5 仅在用户明确选 Y 时执行 |
| 安装失败继续下一步 | 每个 Phase 失败立即停止并报告错误 |
| 不问端口就写死端口 | Phase 4 询问用户是否自定义 |
