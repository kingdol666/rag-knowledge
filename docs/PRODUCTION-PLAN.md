# RAG Knowledge Platform — 生产化路线图

> 目标：把项目从「能跑的开发原型」升级为「可落地、可分发、任何用户开箱即用、优雅启动」的生产级产品。
>
> 编制日期：2026-07-12　·　基准 commit：`ae6146f`（ragctl 6-bug 修复）+ 本轮 dev/prod 终端可见性改动

---

## 0. 现状基线（已具备 ✅）

| 能力 | 实现位置 | 状态 |
|------|---------|------|
| 统一 CLI | `command/ragctl.js`（start/stop/status/restart/config/health/doctor/logs/install/test/mcp/kb） | ✅ |
| dev/prod 终端可见性 | `spawnService` + `spawnInTerminal`（dev 开窗/prod 静默） | ✅ 本轮 |
| 跨平台三平台 | pyproject marker + scripts/ + prctl + MPS + CI matrix | ✅ |
| 安全地基（阶段0） | 原子写 + 路径安全 + 并发锁 + 认证（默认关） | ✅ |
| 单一配置源 | `config.yml` + `.env` 覆盖 | ✅ |
| MCP 工具层 | 73 工具（KB CRUD / 检索 / 图谱 / 经验） | ✅ |
| 一键脚本 | `start.sh` / `start.bat`（开窗） | ✅ |
| 健康检查 | `ragctl health` / `ragctl doctor` | ✅ |

**本轮已完成（待提交）**：
1. 修复 `test_protocol.py`（cwd + APP_MODE）→ 73 工具全通过
2. 修复 `test_server.py`（APP_MODE）→ 8/17 通过（剩余为脚本逻辑过时，归入 D1）
3. `ragctl.js` dev 模式开终端窗口 / prod 模式后台静默

---

## 1. 差距分析（距离「完美可落地」还缺什么）

| 维度 | 当前 | 目标 | 优先级 |
|------|------|------|--------|
| **一键全栈启动** | 需手动 `start backend` + `start web` + `start neo4j` | `ragctl up` 一键拉起 + 就绪探测 | P0 |
| **就绪探测** | 端口探测（粗） | 健康 endpoint 轮询 + 依赖就绪链 | P0 |
| **进程可靠性** | detached 后无管理 | PID 文件 + 防重复 + 崩溃重启 | P0 |
| **实时日志** | `ragctl logs` 读文件尾 | `ragctl logs -f` 多服务实时流 | P0 |
| **首次运行体验** | 直接 `ragctl start`，配置全靠手改 | `ragctl init` 交互向导 | P0 |
| **生产部署** | 仅 dev 模式 | systemd / Windows 服务 / Docker | P1 |
| **数据安全** | 无备份 | `ragctl backup` / `restore` | P1 |
| **分发形态** | 源码 + submodule | 桌面安装包（Tauri） | P2 |
| **测试现代化** | test_server.py 逻辑过时 | 重写 + 端到端套件 | P2 |
| **运维可观测** | 无 | 指标 dashboard | P3 |

---

## 2. 分阶段路线图

### 阶段 A — 优雅启动（P0，预计 1-2 周）

> **目标**：`ragctl up` 一条命令，从零到全部服务就绪可用；失败有明确诊断。

#### A1. `ragctl up` / `ragctl down` 全栈编排
- **目标**：`up` = 按依赖顺序拉起 Neo4j → Backend → Web（+ 可选 MinerU 随 backend 自启）；`down` = 反序优雅停止。
- **改动**：`command/ragctl.js` 新增 `cmdUp(mode)` / `cmdDown()`，内部按依赖图调用现有 `startBackend/startWeb/startNeo4j`，失败任一则回滚已启动的。
- **依赖顺序**：`Neo4j (7687) → Backend (8765, 含 MinerU 子进程) → Web (6789)`；MCP 由 Claude Code 自管，不纳入 `up`。
- **验收**：`ragctl up` → 20-40s 内 4 服务全 RUNNING（`ragctl status` 确认）；`ragctl down` → 全部 STOPPED 且端口释放。

#### A2. 就绪探测（替代纯端口探测）
- **目标**：端口监听 ≠ 服务就绪。改用健康 endpoint 轮询。
- **改动**：`startBackend` 的"等端口"循环改为调 `/api/v1/health` 期望 `{"status":"healthy"}`；`startWeb` 调 `/api/config/frontend` 期 200；Neo4j 调 bolt 探测或 `/api/v1/mineru/status` 间接。
- **验收**：backend 启动后 `ragctl up` 在 uvicorn 真正就绪（而非仅 bind 端口）才报 OK。

#### A3. PID 文件 + 防重复 + 优雅停止
- **目标**：避免重复 `up` 启动多实例；`down` 优先 SIGTERM 给优雅期再 SIGKILL。
- **改动**：
  - `ragctl up` 启动后写 `<project>/.run/{service}.pid` + 端口；`up` 前检查 PID 文件，进程存活则跳过。
  - `stopBackend/stopWeb` 改为先 SIGTERM 等 5s，未退再 SIGKILL（当前直接 SIGKILL）。
  - `ragctl status` 读 PID 文件显示，进程不存在则清孤儿文件。
- **验收**：连续两次 `ragctl up` 不会起两份 backend；`ragctl down` 后 `.run/` 清空。

#### A4. `ragctl logs -f` 实时多服务流
- **目标**：`ragctl logs -f backend` 实时 tail；`ragctl logs -f all` 多服务聚合（带前缀 `[backend]`/`[web]`）。
- **改动**：用 `fs.watch` + 读取偏移量，或 `tail`/`Get-Content -Wait` 子进程；多服务时 Promise.all 并发 tail。
- **验收**：`ragctl logs -f backend` 启动后，curl 触发一个请求，日志实时滚动。

#### A5. `ragctl init` 首次运行向导
- **目标**：`git clone` 后第一条命令 `ragctl init`，交互式完成全部前置。
- **步骤**：
  1. `ragctl doctor` 检查依赖（uv/node/npm/docker），缺哪个提示装哪个。
  2. `git submodule update --init --recursive`。
  3. `ragctl install all`（uv sync + npm install）。
  4. 交互问：端口（默认 8765/6789）、存储路径（默认 ./storage）、是否启用向量/图谱/MinerU（默认全开）、APP_MODE（默认 dev）→ 写 `.env`。
  5. 可选：`docker compose up -d neo4j`（启用图谱时）。
  6. 最后打印「下一步：`ragctl up`」。
- **改动**：`command/ragctl.js` 新增 `cmdInit()`，用 readline 做交互；幂等（已 init 过则跳过对应步骤）。
- **验收**：全新 clone 后 `ragctl init` → `ragctl up` → 浏览器打开即用，零手改配置。

**阶段 A 验收（整体）**：
```
git clone … && cd rag-knowledge
ragctl init      # 交互向导，装依赖、写配置
ragctl up        # 一键全栈，就绪探测通过
# 浏览器 http://localhost:6789 即可用
ragctl logs -f all   # 实时看日志
ragctl down      # 优雅停止
```

---

### 阶段 B — 生产部署（P1，预计 2-3 周）

> **目标**：支持 server / 云 / 容器三种生产部署形态，无人值守长期运行。

#### B1. systemd unit（Linux 服务器）
- 新增 `deploy/systemd/rag-backend.service` / `rag-web.service`（ExecStart 用 `uv run` / `npm start`，Restart=on-failure，After=network.target）。
- `ragctl` 加 `ragctl install systemd`（生成 + enable）。
- 验收：`systemctl status rag-backend` 正常；kill -9 后自动重启。

#### B2. Windows 服务 / 启动项
- 方案：用 `nssm`（Non-Sucking Service Manager）或 `node-windows` 把 backend/web 注册为 Windows 服务。
- `ragctl install service`（win）封装 nssm 调用。
- 验收：服务管理器可见；开机自启；崩溃重启。

#### B3. Docker + docker-compose 全栈
- 现有 `docker-compose.yml`（Neo4j）扩展为全栈：backend + web + neo4j + chromadb。
- backend 镜像多阶段构建（uv sync + 模型缓存层）；web 镜像 `nuxt build` 产物。
- GPU：compose 加 `deploy.resources.reservations.devices`（NVIDIA）；CPU 回退。
- `ragctl up --docker` 走 compose；`ragctl logs -f --docker` 走 `docker compose logs -f`。
- 验收：`docker compose up -d` 全栈起来；无 uv/node 的机器也能跑。

#### B4. 数据备份/恢复
- `ragctl backup` → 打包 `storage/` + `chroma_db/` + Neo4j dump（`cypher-shell` / `neo4j-admin dump`）→ 带 timestamp 的 tar.gz。
- `ragctl restore <file>` → 停服务 → 解包 → 起服务。
- 验收：备份后删数据 → restore → KB/向量/图谱全回来。

#### B5. 生产文档
- `docs/DEPLOY.md`：systemd / Windows 服务 / Docker 三种部署的逐步指南。
- `docs/OPS.md`：日志位置、端口、备份、故障排查（引用已有 memory 的坑）。
- `README.md` 加「生产快速开始」section。

**阶段 B 验收（整体）**：能在干净 Linux 服务器上 `ragctl install systemd && systemctl start rag-backend` 长期运行；或 `docker compose up -d` 一键容器化。

---

### 阶段 C — 桌面软件化（P2，预计 3-4 周）

> **目标**：普通用户双击安装即用，无需装 uv/node/Python —「真正的软件」（用户原话）。

#### C1. Tauri 桌面壳
- 用 [Tauri](https://tauri.app/)（Rust + WebView，体积小）包装 web 前端。
- backend 作为 sidecar（Tauri 打包 `backend/.venv` 的 PyInstaller 产物 或 内嵌 python embeddable）。
- MinerU / chromadb / Neo4j：首启按需下载或用内嵌 SQLite 替代图谱（轻量模式）。
- 配置：装在用户目录（`%APPDATA%/RAGKnowledge/`），非代码目录。

#### C2. 安装器
- Windows：`.msi`（WiX）或 NSIS；macOS：`.dmg`；Linux：`.deb`/`.AppImage`。
- 首启向导（复用 A5 `ragctl init` 逻辑）。

#### C3. 自动更新
- Tauri updater + GitHub Releases 签名包；启动时检查更新。

#### C4. 系统托盘 + 开机自启
- 托盘图标显示服务状态（绿/红），右键菜单 Start/Stop/Open Web/Logs。
- 开机自启（注册表 / launchd / .desktop）。

**阶段 C 验收**：非技术用户下载安装包 → 双击 → 桌面 app 启动 → 看到 web UI → 能解析 PDF 入库，全程零命令行。

---

### 阶段 D — 完善度（P3，持续）

#### D1. 测试现代化
- 重写 `test_server.py`：用当前 MCP 工具签名（`kb_doc_read(kb_id, doc_path)` 配对）、`kb_update` 后追踪新 path、dedup/batch 断言更新。
- 新增端到端套件：`ragctl up` → 解析一个 fixture PDF → search → graph build → `ragctl down`（全链路）。
- CI 加 `ragctl up --mode prod` smoke（prod 路径回归）。

#### D2. 可观测性
- backend 暴露 `/api/v1/metrics`（Prometheus 格式：请求数、解析时长、向量查询数）。
- web 加简易 dashboard 页（服务状态 + 最近解析）。

#### D3. KB 导入导出
- `ragctl kb export <kb>` → tar（md + 元数据）；`import` → 入库 + 自动索引。
- 跨实例迁移知识库。

#### D4. 多用户 / RBAC
- 现有认证（阶段0）是单 token；扩为多用户 + 角色（admin/editor/viewer）。
- 每个 KB 可设归属与权限。

#### D5. HTTPS / TLS
- 生产 TLS：反向代理（Caddy/Nginx）自动证书；或 backend 直挂证书。
- `config.yml: server.tls` 开关。

---

## 3. 建议执行顺序与里程碑

| 里程碑 | 内容 | 预计 |
|--------|------|------|
| **M1 — 优雅启动** | 阶段 A 全部（up/down + 就绪 + PID + logs -f + init） | 1-2 周 |
| **M2 — 生产就绪** | 阶段 B1+B3+B5（systemd + Docker + 文档） | 2 周 |
| **M3 — 运维完备** | 阶段 B2+B4（Win 服务 + 备份） | 1 周 |
| **M4 — 桌面 MVP** | 阶段 C1+C2（Tauri 壳 + 安装器） | 3-4 周 |
| **M5 — 完善度** | 阶段 D 持续迭代 | 滚动 |

**关键决策点**（建议先与用户确认）：
1. **M4 桌面化是否做？** 这是「真正的软件」的核心，但工作量最大（3-4 周）。若只需 server 部署，可跳过直接 D 系列。
2. **图谱是否在桌面版保留 Neo4j？** Neo4j 依赖重；桌面版可降级为「无图谱」或换 SQLite 图存储。
3. **GPU/MinerU 在桌面版如何承载？** 桌面用户机器可能无 GPU；需 CPU 回退 + 模型按需下载策略。

---

## 4. 跨阶段的不变约束（每个阶段都要守住）

- **三平台一等支持**（[[cross-platform-support]]）：任何新功能 Win/Linux/macOS 都要过。
- **flag 默认保守可回滚**（[[kbms-enhancement-roadmap]]）：新行为用 config.yml flag 控制，关 flag 即旧行为。
- **单一配置源**：所有端口/路径/开关进 `config.yml` + `.env`，不硬编码。
- **诊断优于假设**：服务异常先用 `ragctl doctor` + `ragctl health`，复用已沉淀的 memory 坑表（MinerU 代理/管道、web 单点依赖、collection 不一致等）。
- **测试先行**：每个工作项落地前补对应的 ragctl 命令 smoke +（若改代码）pytest。
