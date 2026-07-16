---
name: knowledgebase-init
description: >
  知识库系统全链路交互式安装部署向导。
  当用户输入 /knowledgebase-init 或提到"初始化知识库"、"安装知识库"、"部署知识库"、
  "setup knowledge base"、"install rag knowledge" 时触发。
  交互式引导用户完成全套部署，每个关键配置都询问用户后再设定。
  包含：项目路径选择（绝对/相对）· 知识库存储路径 · 后台访问控制 · MinerU OCR 开关 ·
  Neo4j 图谱开关 · 端口配置 · 镜像加速 · 自动更新。
  Triggered by: /knowledgebase-init, 初始化知识库, 安装知识库, 部署知识库, 知识库启动,
  setup knowledge base, install rag knowledge, deploy KB, start knowledge base,
  kb init, knowledgebase setup wizard, 知识库安装向导, 配置知识库, 引导安装知识库.
---

# Knowledgebase Init — 全平台生产级交互式部署向导

**执行者：此技能由 Archival agent 执行** — 必须委托 `Agent(subagent_type="archival", ...)` 执行。

## 核心原则

- 🔄 **全平台兼容** — Windows / Linux / macOS 三平台统一流程
- 💬 **逐项询问** — 共 12 个关键决策点，每个都由用户明确回答后才执行
- 🚫 **零擅自决策** — 涉及路径、端口、密码、功能开关的配置，必须有用户确认
- ✅ **每步验证** — 完成一个阶段立即验证，失败即时反馈
- 📁 **路径灵活** — 支持绝对路径和相对路径，用户完全自由选择

---

## Phase 0 — 平台检测

首先确定操作系统：

```
Bash: uname -s  (Linux/macOS) 或 echo %OS% (Windows)

记录变量: OS_TYPE = "linux" | "darwin" | "windows"
```

---

## Phase 1 — 环境预检

```
检测以下命令是否可用:
  Bash: command -v uv    (Python 包管理器)
  Bash: command -v node   (Node.js 18+)
  Bash: command -v git    (Git)
  Bash: command -v docker (Docker, 可选)
  Bash: command -v curl   (HTTP 客户端)
```

输出结果表格，每项标注 ✅/❌。

**缺失时给出精准安装命令：**

| 系统 | uv | node | git |
|------|-----|------|-----|
| Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `curl -fsSL https://deb.nodesource.com/setup_20.x \| sudo -E bash - && sudo apt install -y nodejs` | `sudo apt install -y git` |
| macOS | 同上 | `brew install node` | `brew install git` |
| Windows | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` | https://nodejs.org/ 下载 LTS 安装包 | https://git-scm.com/ 下载安装包 |

**所有核心依赖 ✅ 后才进入 Phase 2。**

---

## Phase 2 — 项目路径选择 ⭐

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📁 配置 1/12: 项目安装路径
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RAG Knowledge Platform 的代码要安装在哪个目录？

你可以选择:
  A) 默认路径 — 用户主目录下的 rag-knowledge
     Linux/macOS: ~/rag-knowledge
     Windows:     C:\Users\<你的用户名>\rag-knowledge

  B) 自定义绝对路径 — 例如 /data/projects/rag-knowledge 或 D:\my-projects\rag-knowledge

  C) 相对路径 — 相对于你当前所在目录，例如 ./my-kb 或 ../kb-project

请输入你的选择 [A/B/C，默认: A]:
```

如果用户选择 A → `RAG_ROOT = ~/rag-knowledge`

如果用户选择 B → 提示输入完整绝对路径：
```
请输入完整的绝对路径:
> /home/alice/projects/my-rag-kb
```

如果用户选择 C → 提示输入相对路径：
```
请输入相对路径（相对于当前目录）:
> ./knowledge-base-system
```
→ 解析: `RAG_ROOT = $(pwd)/knowledge-base-system`

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ 项目将安装到: <RAG_ROOT>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 3 — 项目拉取

```
Bash: 检查 <RAG_ROOT> 是否已存在

如果存在:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ⚠️ 目录已存在: <RAG_ROOT>
    
    如何处理？
    1. 更新 (git pull --recurse-submodules) — 保留现有配置和数据
    2. 重新安装 — 删除后重新 clone（⚠️ 数据将丢失）
    3. 跳过 — 保持现状，不修改
    请选择 [1/2/3]:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

如果不存在:
  Bash: git clone --recursive https://github.com/kingdol666/rag-knowledge.git "<RAG_ROOT>"
  验证: ls <RAG_ROOT>/config.yml 存在
```

---

## Phase 4 — 依赖安装确认

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📦 配置 2/12: 依赖安装确认
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

即将安装以下内容:
  • Backend (Python): FastAPI + torch + transformers + mineru (~3.0 GB)
  • Web (Node.js): Nuxt 3 + Ant Design Vue (~500 MB)
  • kb-mcp (Python): FastMCP + httpx (~100 MB)
  • BGE-M3 嵌入模型: 向量搜索核心 (~2.2 GB)
  总计: ~6 GB 磁盘空间 | 安装时间约 10-30 分钟（取决于网速）

是否继续？[Y/n]:
```

用户确认后：
```
Bash: cd "<RAG_ROOT>" && node command/ragctl.js setup
```

等待完成。若超时或失败：
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ❌ 安装未完全成功。以下是错误信息:
  <具体错误>
  
  你可以:
  1. 检查网络连接后重试: cd <RAG_ROOT> && ragctl setup
  2. 手动逐步安装: ragctl deps → ragctl model
  3. 跳过继续（部分功能不可用）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 5 — 交互式配置（12 个关键决策点）

**每个配置逐项询问，绝不批量跳过。**

### 配置 3: 运行模式
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚙️ 配置 3/12: 运行模式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. dev  — 开发模式 (backend:8765, web:6789)
           热重载 ✅ · 控制台日志 ✅ · 适合开发调试
  2. prod — 生产模式 (backend:8001, web:3000)
           热重载 ❌ · 后台静默运行 · 适合部署使用

  请选择 [1/2，默认: 1]:
```

### 配置 4: Backend 端口
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚙️ 配置 4/12: Backend API 端口
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  当前默认: <MODE_DEFAULT_BACKEND_PORT>
  
  1. 保持默认 (<MODE_DEFAULT_BACKEND_PORT>)
  2. 自定义端口
  请选择 [1/2，默认: 1]:
  
  （如选 2）请输入端口号 [1024-65535]:
  > 
```

### 配置 5: Web 前端端口
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚙️ 配置 5/12: Web 前端端口
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  当前默认: <MODE_DEFAULT_WEB_PORT>
  
  1. 保持默认 (<MODE_DEFAULT_WEB_PORT>)
  2. 自定义端口
  请选择 [1/2]:
```

### 配置 6: 知识库存储路径 ⭐
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📁 配置 6/12: 知识库存储路径
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  知识库的文档、索引、图片等数据要存储在哪里？

  当前默认: <RAG_ROOT>/web/storage/tree-file-system

  你可以选择:
  A) 默认 — 存储在项目目录内（随项目移动）
  B) 自定义路径 — 存储在其他磁盘/目录

  请选择 [A/B，默认: A]:
  
  （如选 B）请输入存储路径:
  > /mnt/data/rag-storage  或  D:\RAG-Storage
```

### 配置 7: 访问控制
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔒 配置 7/12: 后台访问控制
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  是否需要为后端 API 设置访问密码？
  （启用后，所有 API 请求需要携带 X-API-Key header）
  
  1. n — 不需要（默认，适合本地开发）
  2. Y — 需要，设置密码
  请选择 [Y/n，默认: n]:
  
  （如选 Y）请输入 API Key（留空自动生成随机 32 位字符串）:
  > 
  → KB_AUTH_TOKEN=<用户输入或随机生成>
```

### 配置 8: MinerU OCR
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📄 配置 8/12: PDF 解析引擎 (MinerU OCR)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  MinerU 是 PDF/文档解析引擎，首次解析 PDF 时自动下载模型 (~2-5GB)。
  
  1. Y — 启用（推荐，支持 PDF/Word/PPT 解析）
  2. n — 禁用（仅支持 Markdown/TXT 格式）
  请选择 [Y/n，默认: Y]:
```

### 配置 9: Neo4j 知识图谱
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🕸️ 配置 9/12: 知识图谱 (Neo4j)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  知识图谱可以在文档之间建立关联，支持跨 KB 桥梁文档发现和
  图谱可视化。需要 Docker 运行 Neo4j 容器（~500MB 额外磁盘）。

  你是否需要知识图谱功能？
  
  A) 是 — 需要 Docker，自动启动 Neo4j 容器
  B) 否 — 跳过（图谱功能不可用，其他功能正常）
  请选择 [A/B，默认: A]:
```

### 配置 10: Neo4j 密码
```
（仅当配置 9 选择 A 时）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔐 配置 10/12: Neo4j 数据库密码
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  请设置 Neo4j 数据库密码:
  1. 使用默认: password
  2. 自定义密码
  请选择 [1/2，默认: 1]:
  
  （如选 2）请输入密码（至少 8 位）:
  > ************
```

### 配置 11: HuggingFace 镜像加速
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🚀 配置 11/12: HuggingFace 镜像加速
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  国内用户可以通过 hf-mirror.com 镜像加速模型下载（BGE-M3 ~2.2GB）。

  你需要配置镜像吗？
  1. Y — 使用 hf-mirror.com（国内推荐）
  2. n — 直连 HuggingFace（海外/已翻墙用户）
  3. 自定义镜像地址
  请选择 [1/2/3，默认: 1]:
  
  （如选 3）请输入镜像地址:
  > https://your-mirror.example.com
```

### 配置 12: 自动更新
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔄 配置 12/12: 自动更新
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  每次启动时是否自动检查并拉取项目更新？
  （git pull --recurse-submodules）
  
  1. Y — 启用（推荐）
  2. n — 禁用（手动 ragctl update）
  请选择 [Y/n，默认: Y]:
```

### 配置确认汇总
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📋 配置确认 — 请检查以下设置:

  项目路径:     <RAG_ROOT>
  运行模式:     <dev/prod>
  Backend 端口: <BACKEND_PORT>
  Web 端口:     <WEB_PORT>
  存储路径:     <STORAGE_PATH>
  访问控制:     <auth: yes/no>
  MinerU OCR:   <enabled/disabled>
  Neo4j 图谱:   <enabled/disabled>
  HF 镜像:      <mirror_url or "直连">
  自动更新:     <yes/no>

  确认以上配置？[Y/n/修改某项编号]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 6 — 写入配置

根据用户所有回答，创建 `.env` 文件：

```bash
cat > "<RAG_ROOT>/.env" << 'RAGEOF'
# RAG Knowledge Platform — Environment Variables
# Generated by /knowledgebase-init on $(date)

# === 核心配置 ===
APP_MODE=<用户选择的模式>
BACKEND_PORT=<用户选择的后端端口>
WEB_PORT=<用户选择的前端端口>
TREE_STORAGE_PATH=<用户选择的存储路径>
PYTHONUTF8=1

# === 访问控制 ===
KB_AUTH_TOKEN=<用户设置的 token 或留空>

# === 模型下载 ===
HF_ENDPOINT=<用户选择的镜像地址或留空>

# === Neo4j ===
NEO4J_PASSWORD=<用户设置的密码>

# === 更新 ===
RAG_AUTO_UPDATE=<true/false>
RAGEOF
```

---

## Phase 7 — ragctl 全局注册

| 平台 | 操作 |
|------|------|
| Linux/macOS | `mkdir -p ~/.local/bin && ln -sf "<RAG_ROOT>/ragctl" ~/.local/bin/ragctl && chmod +x ~/.local/bin/ragctl` |
| Windows | `mkdir %USERPROFILE%\.local\bin 2>nul && copy /Y "<RAG_ROOT>\ragctl.bat" "%USERPROFILE%\.local\bin\ragctl.bat"` |

```
Bash: 验证 ragctl --version 可执行
```

---

## Phase 8 — Neo4j 启动

```
Bash: cd "<RAG_ROOT>" && docker compose up -d neo4j
Bash: 轮询 127.0.0.1:7687 直到可用（最多等待 60s）
```

---

## Phase 9 — 启动服务

```
Bash: cd "<RAG_ROOT>" && ragctl up
```

每 2s 输出一次等待状态：

```
[00:02] Backend   starting…
[00:05] Backend   ✓ ready (port <BACKEND_PORT>)
[00:08] Web       starting…
[00:12] Web       ✓ ready (port <WEB_PORT>)
```

---

## Phase 10 — 全链路验证

```
MCP Tools:
  mcp__kb-mcp__backend_status()   → 验证 backend + MinerU
  mcp__kb-mcp__kb_list()          → 验证 KB 列表
  mcp__kb-mcp__kb_graph_health()  → 验证 Neo4j
  mcp__kb-mcp__kb_search(query="test", top_k=3) → 验证搜索

Bash:
  curl -s http://localhost:<BACKEND_PORT>/api/v1/health
  curl -s -o /dev/null -w "%{http_code}" http://localhost:<WEB_PORT>/
```

---

## Phase 11 — 安装完成报告

```
═══════════════════════════════════════════════════════════
  ✅ RAG Knowledge Platform 安装完成！

  📊 服务状态:
     Backend:  http://localhost:<BACKEND_PORT>  ✅ healthy
     Web UI:   http://localhost:<WEB_PORT>      ✅ online
     Neo4j:    bolt://localhost:7687             ✅ available
     MinerU:   OCR 引擎                          ✅ ready

  📁 项目目录:    <RAG_ROOT>
  📁 知识库数据:  <STORAGE_PATH>

  🔧 全局指令 (任意终端可用):
     ragctl status   ·  ragctl up/down   ·  ragctl logs   ·  ragctl check

  🌐 打开 Web UI: http://localhost:<WEB_PORT>
  🤖 打开 Claude Chat: http://localhost:<WEB_PORT>/claude-chat

  🎉 13 skills + 74 MCP tools 已就绪！
═══════════════════════════════════════════════════════════
```

---

## ⚠️ NEVER — 绝对禁止

| ❌ | ✅ |
|----|----|
| 不问用户就覆盖已有 .env | 展示当前 .env 内容，询问是否修改每一项 |
| 跳过预检直接安装依赖 | Phase 1 所有核心依赖 ✅ 后继续 |
| 不检测平台就用 Linux 命令 | Phase 0 OS_TYPE 变量驱动后续所有命令 |
| 用户明确说 n 还强行装 | 配置 7/8/9 的每个 n 都必须尊重 |
| 安装失败（非零退出）继续下一步 | 每个 Phase 失败立即停止，给出 3 个选项 |
| 不验证写端口 | 端口范围检查 (1024-65535) + 是否被占用检查 |
| 不展示最终确认清单 | 12 个决策点全部汇总展示，等用户最终确认 |
| 跳过 ragctl 注册 | Phase 7 必须执行，并验证注册成功 |
| 不问存储路径默认写死 | 配置 6 必须询问，支持绝对/相对/默认三种方式 |
| 用错误的 shell 语法 | 所有命令根据 OS_TYPE 自动适配（/ vs \\ 路径分隔符） |
