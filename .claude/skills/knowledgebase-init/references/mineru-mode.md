# MinerU Dual-Mode Engine (Remote API / Local Deployment)

> Referenced by knowledgebase-init Phase 6b (mode selection) and Phase 5 (incremental model download).
> Backend implementation: `backend/app/utils/mineru_engine.py` (facade) + `mineru_remote.py` (remote client)
> + `mineru_manager.py` (local subprocess management).

## Configuration-Driven (backend/config.yml)

```yaml
mineru:
  enabled: true
  mode: "remote"            # remote (default, remote-first) | local (force local)
  remote:
    base_url: ""            # mineru-api-compatible endpoint, e.g. http://127.0.0.1:8764
    token: "${MINERU_API_TOKEN:-}"   # Bearer token is read only from .env
    timeout: 1800           # total polling timeout per task (seconds)
  local:
    host: "127.0.0.1"
    start_on_boot: false    # whether to warm up the local engine at backend startup
    startup_timeout: 60
    model_source: "modelscope"
```

Routing rules (hot-applied: after editing the config, `POST /api/v1/config/reload`):

| mode | Behavior |
|------|------|
| `remote` | Probe `{base_url}/health` → if available, use remote; **if unconfigured or unreachable, automatically fall back to local** (lazily starts the local subprocess) |
| `local` | Always the local subprocess; never touches the remote endpoint |

> Compatibility: the old flat config (`mineru.host/start_on_boot/startup_timeout/model_source`) is still read and is
> equivalent to the `local:` sub-section; when the old config has no `mode` key it is treated as `remote` + empty
> base_url → behavior equals local, for a smooth transition.

## Phase 6b — Mode Selection Wizard (user interaction)

**Already-configured detection**: `backend/config.yml` contains `mineru.mode` AND (mode=local OR remote.base_url non-empty) →
skip the question and only verify connectivity. Otherwise ask once, mandatory:

```
MinerU parsing engine mode?
1) Remote API (default/recommended) — zero local load; requires an API address (+ optional token)
2) Local deployment — fully offline; requires installing mineru + downloading models (several GB)
```

### Choose 1) Remote API

1. **Collect parameters** (item by item):
   - `base_url` (required): e.g. `http://192.168.1.10:8764` (self-hosted mineru-api / container).
     Validation: must be http/https.
   - `token` (optional): only needed when the gateway has auth enabled. **Write it ONLY into `.env` as
     `MINERU_API_TOKEN=<value>`**, never into config.yml, source code, examples, or logs.
2. **Write the config** (backend/config.yml, using a yaml library, not string replacement):
   ```yaml
   mineru:
     mode: "remote"
     remote:
       base_url: "<user-provided address>"
   ```
   Append/update `MINERU_API_TOKEN` in `.env` (only if the user provided a token).
3. **Verify availability immediately** (without verification the configuration does not count as complete):
   ```bash
   curl -s -m 5 "<base_url>/health"        # expect 200 {"status":"healthy",...}
   ```
   - On failure → prompt: address/port/firewall; offer the options "retry / switch to local deployment".
     (Even if verification is abandoned, saving the config is allowed — at runtime, remote unavailability
     automatically falls back to local, but the user must be explicitly told this.)
4. **Double-confirm via backend status** (when the backend is already running):
   ```bash
   curl -s "http://localhost:<BACKEND_PORT>/api/v1/mineru/status"
   # expect: mode:"remote", effective_mode:"remote", remote.available:true
   ```

### Choose 2) Local Deployment

**Local install procedure (incremental principle — fill in only what is missing)**:

1. **mineru executable check**:
   ```bash
   ls backend/.venv/Scripts/mineru-api.exe    # Windows
   ls backend/.venv/bin/mineru-api            # Linux/macOS
   ```
   Missing → `cd backend && uv sync --python 3.12` (mineru is in the pyproject dependencies).
2. **Model cache check/download** (~2GB, MinerU2.5-… under `$MODELSCOPE_CACHE`):
   ```bash
   ragctl mineru-model          # pulls via mineru-models-download and writes ~/.mineru.json
   ```
   Already cached (directory contains model.safetensors >1GB) → skip.
3. **Startup verification** (lazy start also works; here we explicitly verify once):
   ```bash
   curl -s "http://localhost:<BACKEND_PORT>/api/v1/mineru/status"
   # expect: local.installed:true; after POST /api/v1/mineru/restart, local.running:true
   ```
   First startup includes cold model loading (~1–3 minutes on GPU); increase `local.startup_timeout` (default 60s) if insufficient.

### Wrap-Up (shared by both modes)

- Report the effective mode: the `mode` / `effective_mode` / `remote.available` / `local.installed` fields of `/api/v1/mineru/status`.
- Explain how to switch: change `mineru.mode` + `POST /api/v1/config/reload` hot-applies, no backend restart needed.

## Ops Quick Reference

| Operation | Command/endpoint |
|------|-----------|
| View dual-mode status | `GET /api/v1/mineru/status` (includes mode/effective_mode/last_mode) |
| Force re-probe remote | `POST /api/v1/mineru/probe` (token required) |
| Restart local engine | `POST /api/v1/mineru/restart` (token required) |
| Hot-switch mode | Edit config.yml → `POST /api/v1/config/reload` |
| Local logs | `backend/logs/mineru-api.log` |
| Self-hosted remote endpoint (testing/intranet) | `backend/.venv/Scripts/mineru-api.exe --host 127.0.0.1 --port 8764` |
