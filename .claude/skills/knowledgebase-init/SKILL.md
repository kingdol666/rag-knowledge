---
name: knowledgebase-init
description: >
  Interactive installation wizard for the RAG Knowledge Platform. Supports two
  install methods: (A) plugin install — auto-detects project in ~/.claude/plugins/cache/;
  (B) skills copy — if project not found, asks user for path and git clones if needed.
  Then guides through: prerequisite checks, dependency install, 10-point interactive
  config (mode, ports, storage, auth, MinerU, Neo4j, model source…), ragctl global
  registration, optional MCP global registration (~/.claude.json → mcpServers, user
  consent required), service startup, full-chain validation. Triggered by:
  /knowledgebase-init, init KB, setup knowledge base, install rag knowledge, deploy KB,
  start KB, bootstrap, getting started, 初始化知识库, 安装知识库, 部署知识库, 知识库启动,
  kb init, knowledgebase setup wizard, 知识库安装向导, 配置知识库, 引导安装知识库.
---

# Knowledgebase Init — 全平台交互式部署向导

**执行者：此技能由主 Agent 直接执行（不委托 Archival）**
- init 是用户交互式安装向导，需要实时问答和确认
- 所有 Bash 命令（git pull、ragctl setup、ragctl up 等）由主 Agent 直接执行
- 仅在安装完成后，如需验证 KB 功能，才委托 Archival agent

## 核心原则

- 🔍 **自动定位优先** — 先扫插件缓存 + CWD + git 根；找不到再问用户（含 clone 选项）
- 📦 **两种安装方式** — 插件安装（项目已在缓存）或 skills 复制（需 clone），init 都能处理
- 🔄 **全平台兼容** — Windows / Linux / macOS 三平台统一流程
- 💬 **逐项询问** — 每个关键决策点由用户明确回答后才执行
- 🚫 **零擅自决策** — 涉及路径、端口、密码、功能开关的配置，必须有用户确认
- ✅ **每步验证** — 完成一个阶段立即验证，失败即时反馈
- 📌 **MCP 全局安装需用户同意** — 插件安装已提供全局 MCP；仅用户明确选 Y 才写 `~/.claude.json` → `mcpServers`

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
  Bash: command -v docker (Docker, 可选 — Neo4j 需要)
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

## 两种安装方式（均支持）

本 init skill 同时支持两种安装方式，Phase 2 会自动识别：

| 方式 | 项目代码位置 | skills 位置 | 检测路径 |
|------|-------------|-------------|----------|
| **A. 插件安装** | `~/.claude/plugins/cache/rag-knowledge/rag-knowledge/<version>/` | 随插件一起加载 | Phase 2 方法 1（插件缓存） |
| **B. Skills 复制** | 不存在，需要 clone | `~/.claude/skills/knowledgebase-*/`（用户手动复制） | Phase 2 方法 2/3 → 可能触发 clone |

**方式 A（插件安装）**：用户通过 `/plugin install rag-knowledge@rag-knowledge` 安装，Claude Code 自动 clone 项目到插件缓存目录，skills + MCP 都随插件加载。init 只需定位 + 配置 + 启动。

**方式 B（Skills 复制）**：用户只把 `.claude/skills/knowledgebase-*/` 复制到 `~/.claude/skills/`，项目代码不在磁盘。init 需要先 clone 项目到用户指定路径，再配置 + 启动。适合不想装插件、只想用 skill 引导的用户。

**两种方式最终都会**：
1. 定位/clone 项目代码到 `<RAG_ROOT>`
2. 安装依赖 + 配置 `.env` + `config.yml`
3. 全局注册 `ragctl`（`ragctl install`）
4. **询问**是否全局注册 MCP（`~/.claude.json` → `mcpServers`，需用户同意）
5. 启动服务 + 全链路验证

---

## Phase 2 — 项目定位与 Clone ⭐

**目标**：确定 `<RAG_ROOT>`（项目根目录，含 config.yml + ragctl + backend/）。
按优先级依次尝试 4 种方法，找到即停；全未命中则询问用户（含 clone 选项）。

### 签名验证（所有方法共用）

一个有效的 `<RAG_ROOT>` 必须同时包含：
- `config.yml`（单一配置源）
- `ragctl` 或 `ragctl.bat`（CLI 入口）
- `backend/` 目录

```
verify_signature(d):
  return exists(d/config.yml) AND (exists(d/ragctl) OR exists(d/ragctl.bat)) AND exists(d/backend)
```

### 方法 1 — 插件缓存扫描（方式 A：插件安装的首要路径）

Claude Code 把插件 clone 到 `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`。

```
Linux/macOS:
  for cache_root in "$HOME/.claude/plugins/cache"; do
    [ -d "$cache_root" ] || continue
    # 扫描所有 rag-knowledge 命中（可能有多个版本，取最新）
    find "$cache_root" -maxdepth 4 -name "config.yml" -path "*rag-knowledge*" 2>/dev/null | while read f; do
      d=$(dirname "$f")
      verify_signature "$d" && echo "$d"
    done | sort -V | tail -1   # 取版本号最大的
  done

PowerShell (Windows):
  $cacheRoot = "$env:USERPROFILE\.claude\plugins\cache"
  if (Test-Path $cacheRoot) {
    Get-ChildItem -Path $cacheRoot -Recurse -Filter "config.yml" -Depth 4 -ErrorAction SilentlyContinue |
      Where-Object {
        $d = $_.DirectoryName
        $_.FullName -match "rag-knowledge" -and
        ((Test-Path "$d\ragctl") -or (Test-Path "$d\ragctl.bat")) -and (Test-Path "$d\backend")
      } | Sort-Object FullName -Descending | Select-Object -First 1 | ForEach-Object { Write-Output $_.DirectoryName }
  }
```

### 方法 2 — Git 仓库根目录（CWD 在项目内）

```
Bash: git rev-parse --show-toplevel 2>/dev/null
→ 验证签名 → 命中
```

### 方法 3 — 从 CWD 向上查找签名（5 层）

```
Bash (Linux/macOS):
  d=$(pwd); for i in 1 2 3 4 5; do
    verify_signature "$d" && echo "$d" && break
    d=$(dirname "$d")
  done

PowerShell (Windows):
  $d = Get-Location; foreach ($i in 1..5) {
    if ((Test-Path "$d\config.yml") -and ((Test-Path "$d\ragctl") -or (Test-Path "$d\ragctl.bat")) -and (Test-Path "$d\backend")) { Write-Output $d; break }
    $d = Split-Path $d -Parent
  }
```

### 方法 4 — 询问用户（含 clone 选项）

若方法 1/2/3 均未找到（典型场景：方式 B skills 复制，项目代码尚未 clone）：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ❓ 未自动检测到 RAG Knowledge 项目代码

  已尝试：插件缓存、CWD git 根、CWD 向上 5 层

  项目代码（backend/web/kb-mcp 等）需要放在哪里？

  请输入目标路径（三种情况自动处理）：
    • 路径已存在且是本项目 → 直接使用
    • 路径不存在           → 自动 git clone 到此路径
    • 路径已存在但非本项目 → 询问是否 clone 到子目录

  示例输入：
    Linux/macOS: ~/rag-knowledge  或  /data/projects/rag-knowledge
    Windows:     D:\projects\rag-knowledge

  > 
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**用户输入路径 `<P>` 后的三种处理**：

**情况 4a — `<P>` 存在且签名验证通过** → `RAG_ROOT = <P>`（用户已有项目）

**情况 4b — `<P>` 不存在** → 自动 clone：
```
Bash: mkdir -p "<P>" && git clone https://github.com/kingdol666/rag-knowledge.git "<P>"
验证: verify_signature("<P>") → 通过则 RAG_ROOT = <P>
失败 → 显示错误，回到方法 4 重新询问
```

**中国区 clone 加速**（若直连 GitHub 失败/慢）：
```
# 方案 1：ghproxy 镜像（无需配置，直接替换 URL）
git clone https://ghproxy.com/https://github.com/kingdol666/rag-knowledge.git "<P>"

# 方案 2：用户已有代理（如 Clash 7890）
HTTPS_PROXY=http://127.0.0.1:7890 git clone https://github.com/kingdol666/rag-knowledge.git "<P>"

# 方案 3：Gitee 镜像（若有）
git clone https://gitee.com/<user>/rag-knowledge.git "<P>"
```

> clone 失败时向用户展示这三种加速方案并询问选哪个，不要静默重试。

**情况 4c — `<P>` 存在但签名不通过**（空目录或非本项目）：
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚠ 路径已存在但不是 RAG Knowledge 项目: <P>

  1. Clone 到 <P>/rag-knowledge 子目录
  2. 重新输入其他路径
  3. 取消安装
  请选择 [1/2/3]:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
选 1 → `git clone ... "<P>/rag-knowledge"` → `RAG_ROOT = <P>/rag-knowledge`
选 2 → 回到方法 4 重新询问
选 3 → 终止

### 检测结果确认（无论哪个方法命中）

找到 `<RAG_ROOT>` 后，**必须**让用户确认：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ 已定位 RAG Knowledge Platform 项目

  📁 路径:   <RAG_ROOT>
  🏷️ 版本:   <cat <RAG_ROOT>/VERSION>
  🔗 来源:   <方法 1 插件缓存 / 2 git 根 / 3 CWD 上溯 / 4 用户指定 / 4b git clone>
  📦 结构:   config.yml ✅  ragctl ✅  backend/ ✅  web/ ✅  kb-mcp/ ✅

  是否使用此位置继续安装？[Y/n]:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

用户 `n` → 回到方法 4 让用户手动输入。

### 可选：更新项目代码（仅对已存在的 RAG_ROOT，非新 clone）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔄 代码更新检查

  是否在安装前拉取最新代码？(git pull --ff-only)
  1. Y — 拉取最新（推荐，脏工作区会自动跳过）
  2. n — 使用当前版本
  请选择 [Y/n，默认: Y]:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

> 新 clone（情况 4b/4c-1）跳过此步骤——已是最新代码。

用户选 Y：
```
Bash: cd "<RAG_ROOT>" && git pull --ff-only
```
脏工作区或冲突 → 跳过 pull，提示用户手动处理，**不执行 `git reset --hard`**。

---

## Phase 3 — 依赖安装确认

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📦 依赖安装确认
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

即将安装以下内容:
  • Backend (Python): FastAPI + torch + transformers + mineru (~3.0 GB)
  • Web (Node.js): Nuxt 3 + Ant Design Vue (~500 MB)
  • kb-mcp (Python): FastMCP + httpx (~100 MB)
  • command/: js-yaml 等 CLI 依赖 (~10 MB)
  • BGE-M3 嵌入模型: 向量搜索核心 (~2.2 GB)
  总计: ~6 GB 磁盘空间 | 安装时间约 10-30 分钟（取决于网速）

是否继续？[Y/n]:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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

## Phase 4 — 交互式配置（10 个关键决策点）

**每个配置逐项询问，绝不批量跳过。**

### 配置 1: 运行模式
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚙️ 配置 1/10: 运行模式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. dev  — 开发模式 (backend:8765, web:6789)
           热重载 ✅ · 控制台日志 ✅ · 适合开发调试
  2. prod — 生产模式 (backend:8001, web:3000)
           热重载 ❌ · 后台静默运行 · 适合部署使用

  请选择 [1/2，默认: 1]:
```

### 配置 2: Backend 端口
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚙️ 配置 2/10: Backend API 端口
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  当前默认: <MODE_DEFAULT_BACKEND_PORT>

  1. 保持默认 (<MODE_DEFAULT_BACKEND_PORT>)
  2. 自定义端口
  请选择 [1/2，默认: 1]:

  （如选 2）请输入端口号 [1024-65535]:
  >
```

### 配置 3: Web 前端端口
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚙️ 配置 3/10: Web 前端端口
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  当前默认: <MODE_DEFAULT_WEB_PORT>

  1. 保持默认 (<MODE_DEFAULT_WEB_PORT>)
  2. 自定义端口
  请选择 [1/2]:
```

### 配置 4: 知识库存储路径 ⭐
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📁 配置 4/10: 知识库存储路径
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

### 配置 5: 访问控制
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔒 配置 5/10: 后台访问控制
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

### 配置 6: MinerU OCR
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📄 配置 6/10: PDF 解析引擎 (MinerU OCR)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  MinerU 是 PDF/文档解析引擎，首次解析 PDF 时自动下载模型 (~2-5GB)。

  1. Y — 启用（推荐，支持 PDF/Word/PPT 解析）
  2. n — 禁用（仅支持 Markdown/TXT 格式）
  请选择 [Y/n，默认: Y]:
```

### 配置 7: Neo4j 知识图谱
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🕸️ 配置 7/10: 知识图谱 (Neo4j)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  知识图谱可以在文档之间建立关联，支持跨 KB 桥梁文档发现和
  图谱可视化。需要 Docker 运行 Neo4j 容器（~500MB 额外磁盘）。

  你是否需要知识图谱功能？

  A) 是 — 需要 Docker，自动启动 Neo4j 容器
  B) 否 — 跳过（图谱功能不可用，其他功能正常）
  请选择 [A/B，默认: A]:
```

### 配置 8: Neo4j 密码
```
（仅当配置 7 选择 A 时）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔐 配置 8/10: Neo4j 数据库密码
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  请设置 Neo4j 数据库密码:
  1. 使用默认: password
  2. 自定义密码
  请选择 [1/2，默认: 1]:

  （如选 2）请输入密码（至少 8 位）:
  > ************
```

### 配置 9: 模型下载源（BGE-M3 + MinerU）⭐
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🚀 配置 9/10: 模型下载源
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  BGE-M3 嵌入模型 (~2.2GB) 和 MinerU OCR 模型 (~2-5GB) 需要下载。
  选择下载源（写入 config.yml: embedding.model_source）:

  1. modelscope  — ModelScope (modelscope.cn)
                   ⭐ 中国区推荐：阿里云 CDN，国内下载最快、最稳
  2. hf-mirror   — HuggingFace Mirror (hf-mirror.com)
                   国内可用，速度次于 ModelScope
  3. huggingface — HuggingFace (huggingface.co)
                   海外用户 / 已翻墙用户

  请选择 [1/2/3，默认: 1]:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**关键说明**：
- 选 `modelscope`（默认）→ `config.yml` 写入 `embedding.model_source: modelscope`
  下载时优先走 `https://modelscope.cn/BAAI/bge-m3/resolve/master/`，失败自动 fallback 到 hf-mirror → huggingface
- 选 `hf-mirror` → 走 `https://hf-mirror.com/`，fallback 到 huggingface.co
- 选 `huggingface` → 直连 huggingface.co（海外）

下载逻辑（`backend/app/utils/download_model.py`）：
- 每个文件按优先级尝试多个源，单文件失败自动切换到下一个源
- 关闭系统 HTTPS_PROXY（避免 Clash 7890 劫持 modelscope/hf-mirror 的 HTTPS）
- 支持断点续传 + 大文件进度显示

### 配置 10: 自动更新
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔄 配置 10/10: 自动更新
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  每次启动时是否自动检查并拉取项目更新？
  （等价于 ragctl update；对比根目录 VERSION 与 GitHub latest release）

  1. Y — 启用（推荐：启动时 ragctl update --check，有新版本再提示确认拉取）
  2. n — 禁用（手动: ragctl update / 说「更新知识库」触发 knowledgebase-update）
  请选择 [Y/n，默认: Y]:
```

> 实际拉取统一走 `ragctl update`（或 MCP `kb_project_update` / skill `knowledgebase-update`），
> 不会在未确认时 `git reset --hard`。脏工作区默认拒绝自动 pull。

### 配置确认汇总
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📋 配置确认 — 请检查以下设置:

  项目路径:     <RAG_ROOT>  (auto-detected)
  运行模式:     <dev/prod>
  Backend 端口: <BACKEND_PORT>
  Web 端口:     <WEB_PORT>
  存储路径:     <STORAGE_PATH>
  访问控制:     <auth: yes/no>
  MinerU OCR:   <enabled/disabled>
  Neo4j 图谱:   <enabled/disabled>
  模型下载源:   <modelscope|hf-mirror|huggingface>
  自动更新:     <yes/no>

  确认以上配置？[Y/n/修改某项编号]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 5 — 写入配置

根据用户所有回答，**同时更新两个文件**：

### 5a. 更新 `config.yml`（`embedding.model_source`）

根据配置 9 的选择，用 `node`/`python` 修改 `<RAG_ROOT>/config.yml`：

```yaml
embedding:
  model_name: "BAAI/bge-m3"
  model_source: "<modelscope|hf-mirror|huggingface>"  # ← 用户选择
  cache_dir: "./models_cache"
  ...
```

> ⚠️ 必须修改 `config.yml` 的 `embedding.model_source`，因为 `download_model.py` 读取的是这里，
> 不是 `.env`。保持 config.yml 其他字段不变（用 yaml 库读写，不要字符串替换）。

### 5b. 创建 `.env`

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

# === 模型下载 (主配置在 config.yml embedding.model_source) ===
# HF_ENDPOINT 作为 huggingface_hub 库的 fallback hint
HF_ENDPOINT=<根据配置 9: modelscope→https://hf-mirror.com / hf-mirror→https://hf-mirror.com / huggingface→https://huggingface.co>

# === Neo4j ===
NEO4J_PASSWORD=<用户设置的密码>

# === 更新 ===
RAG_AUTO_UPDATE=<true/false>
RAGEOF
```

**HF_ENDPOINT 映射表**（根据配置 9 的选择）：

| 配置 9 选择 | config.yml `embedding.model_source` | `.env HF_ENDPOINT` |
|---|---|---|
| `1. modelscope`（默认） | `modelscope` | `https://hf-mirror.com` |
| `2. hf-mirror` | `hf-mirror` | `https://hf-mirror.com` |
| `3. huggingface` | `huggingface` | `https://huggingface.co` |

---

## Phase 6 — 全局 ragctl 注册（任意终端可用）

目标：让用户在**任意终端**（不限于 Claude Code）都能用 `ragctl status / up / down` 管理服务。

`ragctl install` 会写一个**硬编码绝对路径**的 wrapper 到 `~/.local/bin/`（不是符号链接/拷贝——那些会因路径解析失败）。

```
Bash: cd "<RAG_ROOT>" && ragctl install
```

预期输出包含：`[✓] 已写入 <home>/.local/bin/ragctl(.cmd)` 且确认 `~/.local/bin` 在 PATH 中。
验证：`Bash: ragctl status`（在 <RAG_ROOT> 之外的任意目录运行也应成功）。

> 若 `~/.local/bin` 不在 PATH：Linux/macOS 提示 `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc`；Windows 提示 `setx PATH "%PATH%;%USERPROFILE%\.local\bin"` 后重开终端。

---

## Phase 7 — kb-mcp 全局 MCP 注册（可选，默认跳过）⭐

**重要：此阶段默认跳过，仅在用户明确要求时执行。**

### 为什么默认跳过

| 安装方式 | MCP 已可用的位置 | 是否需要全局注册 |
|----------|------------------|------------------|
| **插件安装**（`/plugin install`） | 任意目录（插件 `mcpServers` 字段已声明） | ❌ 不需要 |
| **项目本地安装**（git clone） | 仅项目目录内（`.mcp.json`） | ❌ 不需要（除非用户要在其他项目用） |
| **多项目共享** | — | ✅ 仅此场景需要 |

### 询问用户（根据安装方式智能推荐）

根据 Phase 2 的来源标签（方法 1 = 插件安装 / 方法 4b = clone）调整推荐：

**情况 A — 插件安装（Phase 2 方法 1 命中）**：
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🌐 kb-mcp 全局 MCP 注册（可选）

  检测到插件安装方式 — kb-mcp 已随插件全局可用（任意目录）。

  是否额外写入 ~/.claude.json → mcpServers？（通常不需要）
  1. n — 跳过（推荐，插件已覆盖全局）
  2. Y — 仍写入全局 ~/.claude.json
  请选择 [Y/n，默认: n]:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**情况 B — Skills 复制 / git clone（Phase 2 方法 4 命中）**：
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🌐 kb-mcp 全局 MCP 注册（可选）

  检测到 clone/手动安装方式 — kb-mcp 目前仅项目目录内可用（.mcp.json）。
  若你想在**其他项目**也使用这 76 个 MCP 工具，需要全局注册。

  是否写入 ~/.claude.json → mcpServers？
  1. Y — 注册全局（在任意目录/任意 Claude Code 会话可用）
  2. n — 仅项目内使用（跳过）
  请选择 [Y/n，默认: Y]:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**仅当用户明确选择 Y 时**执行：
```
Bash: cd "<RAG_ROOT>/kb-mcp" && uv run python plugin_install.py install
```

预期输出：`[OK] kb-mcp installed [global (~/.claude.json → mcpServers)]` + `RAG_PROJECT_ROOT: <RAG_ROOT>`。

验证：
```
Bash: cd "<RAG_ROOT>/kb-mcp" && uv run python plugin_install.py status
```
应显示 `[OK] Global ~/.claude.json: installed (available everywhere)`。

> ⚠️ 全局注册后必须**重启 Claude Code**（或在新会话里 `/mcp` 重连）才能让全局 MCP 生效。

**用户选 n（默认）→ 直接跳到 Phase 8，不做任何全局 MCP 写入。**

---

## Phase 8 — Neo4j 启动（仅当配置 7 选 A）

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
  mcp__kb-mcp__kb_graph_health()  → 验证 Neo4j（如启用）
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
     Neo4j:    bolt://localhost:7687             ✅ available（如启用）
     MinerU:   OCR 引擎                          ✅ ready（如启用）

  📁 项目目录:    <RAG_ROOT>  (auto-detected)
  📁 知识库数据:  <STORAGE_PATH>

  🔧 全局终端指令 (任意目录可用):
     ragctl status   ·  ragctl up/down   ·  ragctl logs   ·  ragctl check
     ragctl version  ·  ragctl update    ·  ragctl desktop
     ragctl clean    ·  清理 MinerU 解析产物 + 缓存（ragctl clean --all）

  🌍 MCP 工具可用范围:
     <插件全局 / 项目本地 / 全局注册 — 根据安装方式>
     14 skills + 76 MCP tools 已就绪
     说「搜索知识库」即可使用；说「更新知识库」→ knowledgebase-update

  🌐 打开 Web UI: http://localhost:<WEB_PORT>
  🤖 打开 Claude Chat: http://localhost:<WEB_PORT>/claude-chat
═══════════════════════════════════════════════════════════
```

---

## ⚠️ NEVER — 绝对禁止

| ❌ | ✅ |
|----|----|
| 方法 1/2/3 未命中就直接放弃 | 依次尝试 1→2→3→4，方法 4 含 clone 选项 |
| 不验证签名就用一个路径 | 必须存在 `config.yml` + `ragctl` + `backend/` 三件套 |
| 用户路径不存在时直接报错退出 | 询问后自动 `git clone` 到该路径（情况 4b） |
| 路径已存在但非本项目时强行覆盖 | 询问：clone 到子目录 / 重新输入 / 取消（情况 4c） |
| 强制执行 `git pull` 或 `git reset --hard` | 拉取用 `--ff-only`，脏工作区跳过并提示 |
| 不问用户就覆盖已有 .env | 展示当前 .env 内容，询问是否修改每一项 |
| 跳过预检直接安装依赖 | Phase 1 所有核心依赖 ✅ 后继续 |
| 不检测平台就用 Linux 命令 | Phase 0 OS_TYPE 变量驱动后续所有命令 |
| 用户明确说 n 还强行装 | 配置 5/6/7 的每个 n 都必须尊重 |
| 安装失败（非零退出）继续下一步 | 每个 Phase 失败立即停止，给出 3 个选项 |
| 不验证写端口 | 端口范围检查 (1024-65535) + 是否被占用检查 |
| 不展示最终确认清单 | 所有决策点汇总展示，等用户最终确认 |
| **默认执行全局 MCP 注册** | **Phase 7 默认跳过；仅用户明确选 Y 才写 `~/.claude.json`** |
| **写 MCP 到 `~/.claude/.mcp.json`** | **全局 MCP 写 `~/.claude.json` → `mcpServers`（唯一正确路径）** |
| 用错误的 shell 语法 | 所有命令根据 OS_TYPE 自动适配（/ vs \\ 路径分隔符） |
