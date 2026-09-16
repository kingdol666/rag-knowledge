# MinerU 双模式引擎（远程 API / 本地部署）

> Referenced by knowledgebase-init Phase 6b（模式选择）与 Phase 5（模型增量下载）。
> 后端实现：`backend/app/utils/mineru_engine.py`（门面）+ `mineru_remote.py`（远程客户端）
> + `mineru_manager.py`（本地子进程管理）。

## 配置驱动（backend/config.yml）

```yaml
mineru:
  enabled: true
  mode: "remote"            # remote(默认,远程优先) | local(强制本地)
  remote:
    base_url: ""            # mineru-api 兼容端点，如 http://127.0.0.1:8764
    token: "${MINERU_API_TOKEN:-}"   # Bearer token 只从 .env 读取
    timeout: 1800           # 单任务轮询总超时(秒)
  local:
    host: "127.0.0.1"
    start_on_boot: false    # backend 启动时是否预热本地引擎
    startup_timeout: 60
    model_source: "modelscope"
```

路由规则（热生效：改配置后 `POST /api/v1/config/reload`）：

| mode | 行为 |
|------|------|
| `remote` | 探活 `{base_url}/health` → 可用走远程；**未配置或不可达自动回退本地**（懒启动本地子进程） |
| `local` | 始终本地子进程，不触碰远程端点 |

> 兼容性：旧版扁平配置（`mineru.host/start_on_boot/startup_timeout/model_source`）仍被读取，
> 等价于 `local:` 子段；旧配置无 `mode` 键时按 `remote` + 空 base_url 处理 → 行为等同本地，平滑过渡。

## Phase 6b — 模式选择向导（用户交互）

**已配置检测**：`backend/config.yml` 存在 `mineru.mode` 且（mode=local 或 remote.base_url 非空）→
跳过提问，仅验证连通性。否则必问一次：

```
MinerU 解析引擎模式？
1) 远程 API（默认/推荐）— 本机零负载；需要 API 地址（+可选 token）
2) 本地部署 — 完全离线；需安装 mineru + 下载模型（数 GB）
```

### 选 1) 远程 API

1. **收集参数**（逐项询问）：
   - `base_url`（必填）：如 `http://192.168.1.10:8764`（自建 mineru-api / 容器）。
     校验：必须 http/https。
   - `token`（可选）：网关开启鉴权时才需要。**只写入 `.env` 的 `MINERU_API_TOKEN=<值>`**，
     绝不写入 config.yml、源码、示例或日志。
2. **写入配置**（backend/config.yml，用 yaml 库非字符串替换）：
   ```yaml
   mineru:
     mode: "remote"
     remote:
       base_url: "<用户提供的地址>"
   ```
   `.env` 追加/更新 `MINERU_API_TOKEN`（仅当用户提供了 token）。
3. **立即验证可用性**（不过验证不算配置完成）：
   ```bash
   curl -s -m 5 "<base_url>/health"        # 期望 200 {"status":"healthy",...}
   ```
   - 失败 → 提示：地址/端口/防火墙；给出选项「重试 / 改用本地部署」。
     （即使放弃验证也允许保存配置——运行时远程不可用会自动回退本地，但必须明确告知用户这一点。）
4. **通过后端状态双重确认**（后端已启动时）：
   ```bash
   curl -s "http://localhost:<BACKEND_PORT>/api/v1/mineru/status"
   # 期望: mode:"remote", effective_mode:"remote", remote.available:true
   ```

### 选 2) 本地部署

**本地安装流程（增量原则，只补缺失项）**：

1. **mineru 可执行文件检查**：
   ```bash
   ls backend/.venv/Scripts/mineru-api.exe    # Windows
   ls backend/.venv/bin/mineru-api            # Linux/macOS
   ```
   缺失 → `cd backend && uv sync --python 3.12`（mineru 在 pyproject 依赖中）。
2. **模型缓存检查/下载**（约 2GB，MinerU2.5-… 于 `$MODELSCOPE_CACHE`）：
   ```bash
   ragctl mineru-model          # 通过 mineru-models-download 拉取并写 ~/.mineru.json
   ```
   已缓存（目录含 model.safetensors 且 >1GB）→ 跳过。
3. **启动验证**（懒启动也行，这里显式验证一次）：
   ```bash
   curl -s "http://localhost:<BACKEND_PORT>/api/v1/mineru/status"
   # 期望: local.installed:true；POST /api/v1/mineru/restart 后 local.running:true
   ```
   首次启动含模型冷加载（GPU 上约 1-3 分钟），`local.startup_timeout` 默认 60s 不够时可调大。

### 收尾（两种模式共用）

- 报告生效模式：`/api/v1/mineru/status` 的 `mode` / `effective_mode` / `remote.available` / `local.installed`。
- 提示切换方式：改 `mineru.mode` + `POST /api/v1/config/reload` 热生效，无需重启后端。

## 运维速查

| 操作 | 命令/端点 |
|------|-----------|
| 查看双模式状态 | `GET /api/v1/mineru/status`（含 mode/effective_mode/last_mode） |
| 强制重新探活远程 | `POST /api/v1/mineru/probe`（需 token） |
| 重启本地引擎 | `POST /api/v1/mineru/restart`（需 token） |
| 热切换模式 | 改 config.yml → `POST /api/v1/config/reload` |
| 本地日志 | `backend/logs/mineru-api.log` |
| 自建远程端点（测试/内网） | `backend/.venv/Scripts/mineru-api.exe --host 127.0.0.1 --port 8764` |
