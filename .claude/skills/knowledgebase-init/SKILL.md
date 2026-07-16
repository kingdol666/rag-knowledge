---
name: knowledgebase-init
description: >
  知识库系统全链路安装部署向导。
  当用户输入 /knowledgebase-init 或提到"初始化知识库"、"安装知识库"、"部署知识库"、
  "setup knowledge base"、"install rag knowledge" 时触发。
  自动完成：GitHub 拉取项目 → 安装依赖 → 下载模型 → 配置环境 → 注册 ragctl 全局指令 → 启动服务。
  Triggered by: /knowledgebase-init, 初始化知识库, 安装知识库, 部署知识库, 知识库启动,
  setup knowledge base, install rag knowledge, deploy KB, start knowledge base,
  kb init, knowledgebase setup wizard, 知识库安装向导, 配置知识库, 引导安装知识库.
---

# Knowledgebase Init — 全链路一键安装部署向导

**执行者：此技能由 Archival agent 执行** — 必须委托 `Agent(subagent_type="archival", ...)` 执行。

## 概述

此 Skill 负责将 RAG Knowledge Platform 从零到全功能运行，共 6 个阶段：

1. ✅ **预检** → 检查环境（uv/node/git/docker）并给出安装指令
2. 📥 **拉取** → git clone 项目到 `~/rag-knowledge`
3. 🔧 **安装** → `ragctl setup` 一键安装全部依赖 + BGE 模型
4. ⚙️ **配置** → 交互式创建 .env + 询问 Neo4j 是否需要
5. 🔗 **注册 ragctl 全局指令** → Linux/macOS 创建 symlink，Windows 添加 PATH
6. 🚀 **启动验证** → `ragctl up` 启动所有服务 → 健康检查 → 最终验证

---

## Step 0 — 环境预检

在开始之前，先检查本地环境是否满足最低要求。

```
运行以下检查（使用 Bash 执行）：

for cmd in uv node git; do
  if command -v $cmd >/dev/null 2>&1; then
    echo "✓ $cmd: $( $cmd --version 2>&1 | head -1 )"
  else
    echo "✗ $cmd 未安装"
  fi
done

# Docker 为可选项
if command -v docker >/dev/null 2>&1; then
  echo "✓ docker (可选): $(docker --version 2>&1)"
else
  echo "○ docker 未安装 (图谱功能可选)"
fi
```

**如果 uv 缺失，引导用户安装：**
- **Linux/macOS:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows:** `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

**如果 node 缺失，引导用户安装：**
- https://nodejs.org/ (安装 LTS 18+ 版本)

**所有核心依赖满足后才进入 Step 1。**

---

## Step 1 — 拉取项目

```
RAG_ROOT="${HOME}/rag-knowledge"

if [ -d "$RAG_ROOT" ]; then
    echo "项目目录已存在: $RAG_ROOT"
    echo "正在更新..."
    cd "$RAG_ROOT" && git pull --recurse-submodules
else
    echo "正在从 GitHub 拉取项目..."
    git clone --recursive https://github.com/kingdol666/rag-knowledge.git "$RAG_ROOT"
    cd "$RAG_ROOT"
fi

# 确保子模块完整
git submodule update --init --recursive
```

---

## Step 2 — 一键安装

```
cd "$RAG_ROOT"

# 如果 ragctl CLI 依赖未安装，先安装
if [ ! -d "command/node_modules" ]; then
    (cd command && npm install --silent)
fi

# 执行一键部署（自动安装 uv/python/依赖/模型）
node command/ragctl.js setup
```

**ragctl setup 会自动完成：**
- 安装 uv（如果缺失）
- 安装 Python 3.12（通过 uv）
- `git submodule update --init --recursive`
- `uv sync` (backend 依赖: FastAPI + torch + transformers + mineru)
- `uv sync` (kb-mcp 依赖: FastMCP + httpx)
- `npm install` (web 依赖: Nuxt 3 + Ant Design Vue)
- 下载 BGE-M3 嵌入模型 (~2.2GB)
- 创建 `.env` 文件

---

## Step 3 — 配置

```
cd "$RAG_ROOT"

# 如果 .env 已存在，跳过
if [ -f ".env" ]; then
    echo "✓ .env 已存在"
else
    cat > .env << 'EOF'
APP_MODE=dev
BACKEND_PORT=8765
WEB_PORT=6789
PYTHONUTF8=1
EOF
    echo "✓ .env 已创建（默认值）"
fi
```

**询问用户：是否需要知识图谱功能？**

```
知识图谱需要 Neo4j (Docker)，是否需要？[Y/n]

如果需要: docker compose up -d neo4j
如果不需要: 图谱功能将在没有 Neo4j 情况下降级运行
```

---

## Step 4 — 注册 ragctl 全局指令 ⭐

将 `ragctl` 注册为系统全局可用的 CLI 命令，使任何终端窗口都能直接使用。

**Linux / macOS：**
```bash
RAG_ROOT="${HOME}/rag-knowledge"
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"

# 创建 ragctl symlink
ln -sf "$RAG_ROOT/ragctl" "$BIN_DIR/ragctl"
chmod +x "$BIN_DIR/ragctl"

echo "✓ ragctl 已注册到 $BIN_DIR/ragctl"

# 确保 ~/.local/bin 在 PATH 中
if ! echo "$PATH" | grep -q "$BIN_DIR"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc" 2>/dev/null
    echo "✓ ~/.local/bin 已添加到 PATH (bashrc + zshrc)"
fi
```

**Windows：**
```powershell
$RAG_ROOT = "$env:USERPROFILE\rag-knowledge"
$BIN_DIR = "$env:USERPROFILE\.local\bin"
New-Item -ItemType Directory -Force -Path $BIN_DIR | Out-Null

# 复制 ragctl.bat 和 ragctl.cmd 到 bin 目录
Copy-Item "$RAG_ROOT\ragctl.bat" "$BIN_DIR\ragctl.bat" -Force
Copy-Item "$RAG_ROOT\ragctl.cmd" "$BIN_DIR\ragctl.cmd" -Force

# 添加到用户 PATH（永久）
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BIN_DIR*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$BIN_DIR", "User")
    Write-Host "✓ $BIN_DIR 已添加到用户 PATH"
} else {
    Write-Host "✓ $BIN_DIR 已在 PATH 中"
}
```

**验证注册成功：**
```
ragctl --version   # 应该输出: ragctl 2.0.0
ragctl check       # 全面环境检查
```

---

## Step 5 — 启动服务

```
cd "$RAG_ROOT"

# 一键启动所有服务
ragctl up

# 或手动启动
node command/ragctl.js up
```

**等待服务就绪后验证：**

```
# 检查每个服务
echo "=== Backend ===" && curl -s http://localhost:8765/api/v1/health
echo "=== Frontend ===" && curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:6789/
echo "=== Neo4j ===" && curl -s -o /dev/null -w "bolt available" telnet://localhost:7687 2>&1 | head -1
echo "=== MinerU ===" && curl -s http://localhost:8765/api/v1/mineru/status

# 运行全量状态检查
ragctl status
```

---

## Step 6 — 最终验证

使用 MCP 工具进行端到端验证：

```
1. mcp__kb-mcp__backend_status()         → 验证后端 + MinerU 正常
2. mcp__kb-mcp__kb_list()                → 验证知识库列表可获取
3. mcp__kb-mcp__kb_graph_health()        → 验证 Neo4j 图谱连接
4. mcp__kb-mcp__kb_search(query="test", top_k=3)  → 验证搜索功能
```

输出安装完成报告：

```
═══════════════════════════════════════════════════════
  ✅ RAG Knowledge Platform 安装成功！

  📊 服务状态:
     Backend:  http://localhost:8765 (healthy)
     Web UI:   http://localhost:6789 (在线)
     Neo4j:    bolt://localhost:7687 (可用)
     MinerU:   OCR 引擎就绪

  🔧 全局指令:
     ragctl status    查看状态
     ragctl logs      查看日志
     ragctl down      停止服务
     ragctl check     环境检查

  📖 打开 Web UI: http://localhost:6789
  🤖 打开 Claude Chat: http://localhost:6789/claude-chat

  🎉 13 个 skills + 74 个 MCP 工具已就绪！
═══════════════════════════════════════════════════════
```

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 跳过预检直接 clone | 可能重复安装或环境不满足 | 先检查 backend_status + uv/node/git |
| 不解释就直接执行命令 | 用户可能想自定义路径/端口 | 每个步骤先告知用户再执行 |
| clone 后不更新子模块 | backend/web 目录为空 | `git submodule update --init --recursive` |
| 安装完成后不验证 | 可能安装失败但用户不知道 | 每个阶段后验证关键输出 |
| 忘记注册 ragctl 全局指令 | 用户每次都要 cd 到项目目录 | Step 4 必须执行 |
| 覆盖已有 .env 不提醒 | 用户自定义配置丢失 | .env 存在时跳过，告知用户 |
| 不询问就启动 Docker | 用户可能不需要图谱 | 先询问用户是否需要 Neo4j |

## 工具速查

- `mcp__kb-mcp__backend_status()` — 后端+MinerU 状态
- `mcp__kb-mcp__kb_list()` — 知识库列表
- `mcp__kb-mcp__kb_graph_health()` — Neo4j 图谱健康
- `mcp__kb-mcp__kb_search(query, top_k)` — 搜索验证
- `Bash: cd ~/rag-knowledge && node command/ragctl.js <command>` — ragctl CLI
- `Bash: curl ...` — 健康检查

## Auto-Start 机制

插件的 `hooks/hooks.json` 已注册 SessionStart 钩子。

每次新对话开始时，hook 自动执行：
1. 检查 `~/rag-knowledge` 是否存在
2. 检查 `localhost:8765/api/v1/health` 是否响应
3. 三种情况：
   - ✅ 项目存在 + 后端运行 → `[rag-knowledge] Backend healthy`
   - ⚠️ 项目存在 + 后端未运行 → `[rag-knowledge] 服务未运行。输入 /knowledgebase-init 启动服务。`
   - 📥 项目不存在 → `[rag-knowledge] 项目未安装。输入 /knowledgebase-init 自动拉取并部署。`

这个自动检测确保用户安装插件后，**不需要手动配置任何东西**——系统会自动感知状态并引导用户完成部署。
