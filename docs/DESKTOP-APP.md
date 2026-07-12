# RAG Knowledge Desktop（Tauri 桌面控制台）

把 RAG Knowledge Platform 包装成桌面应用的 Tauri 控制台。一个窗口管所有服务：一键启动 / 状态检测 / 日志查看 / 修复 / ragctl 指令。

## 架构

```
Tauri App (Rust 主进程，src-tauri/)
├── WebView 加载 src-tauri/frontend/index.html（控制面板 SPA，vanilla HTML/JS）
└── Rust 命令（src-tauri/src/commands.rs）:
    ├── start_service(backend|web|neo4j|all)   → spawn uv run / node / docker
    ├── stop_service(...)                       → taskkill PID（记录的或端口查的）
    ├── check_status()                          → HTTP health + TCP probe
    ├── detect_features()                       → 读 config.yml（向量/图谱/MinerU/认证）
    ├── repair_service(neo4j|backend_deps|web_deps)
    ├── read_log_tail(backend|web|mineru)       → 读日志文件尾
    ├── open_web_ui()                           → 系统浏览器打开 localhost:6789
    └── run_ragctl(args)                        → 执行 node command/ragctl.js <args>
```

桌面 app **不替代** backend / web，而是**管控它们**：
- backend (FastAPI) 仍由 `uv run python main.py` 启动（Tauri spawn）
- web (Nuxt) 仍由 `node start.mjs` 启动（Tauri spawn）
- 「打开 Web UI」按钮用系统浏览器打开 Nuxt 前端（完整 KB 业务功能）
- Tauri 窗口本身是控制面板（启动/检测/日志/修复/ragctl 终端）

## 开发

前置：Rust + tauri-cli（`cargo install tauri-cli --version "^2"`）+ uv + Node。

```bash
cd src-tauri
cargo tauri dev        # 编译 + 开窗口（首次 ~1-2 分钟编译）
```

窗口出现后：
- 顶部「▶ 一键启动」= 启动 backend → 等就绪 → 启动 web
- 服务卡片显示 Backend / Web / Neo4j / MinerU 实时状态（每 6s 自动刷新）
- 「控制台」tab 看 backend/web/mineru 日志（每 3.5s 自动刷新）
- 「ragctl 指令」tab 输入 ragctl 子命令执行（status / health / doctor / start / logs / kb list / mcp tools）

## 打包

```bash
cd src-tauri
cargo tauri build      # 产出 src-tauri/target/release/bundle/nsis/*.exe（NSIS 安装器）
```

Windows 产出 NSIS 安装器（`RAG Knowledge_1.0.0_x64-setup.exe`）。打包需 MSVC build tools + WebView2（Win11 预装）。

## 项目根定位

桌面 app 通过以下顺序定位项目根（backend/web/config.yml 所在）：
1. 环境变量 `RAG_PROJECT_ROOT`（打包后用户设定）
2. fallback：编译时 `CARGO_MANIFEST_DIR` 的父目录（dev 模式 = 仓库根）

**打包发布时**，需把 backend/web/config.yml 等随包分发，并让用户通过 `RAG_PROJECT_ROOT` 指向。（MVP 阶段以 dev 模式为主，后续阶段 C 做完整的内嵌分发 — 见 `docs/PRODUCTION-PLAN.md`。）

## 文件清单

```
src-tauri/
├── Cargo.toml              # Rust 依赖：tauri 2 / reqwest / tokio / serde_yaml
├── build.rs                # tauri-build
├── tauri.conf.json         # 窗口/bundle/withGlobalTauri 配置
├── capabilities/default.json  # 权限（仅 core:default）
├── icons/                  # cargo tauri icon 生成的全套图标
├── frontend/index.html     # 控制面板 UI（深色主题）
└── src/
    ├── main.rs             # Tauri Builder + 命令注册
    └── commands.rs         # 全部命令实现
```

## 当前限制（MVP）

- 项目根依赖 dev 路径或 RAG_PROJECT_ROOT（阶段 C 做内嵌）
- 不含 Claude Code 终端集成（后续）
- 不含 Python/依赖下载界面（阶段 A 做 `ragctl init` 后，桌面 app 调用它）
- Neo4j 需 Docker（桌面 app 能 docker compose up，但 Docker 本身要用户装）
