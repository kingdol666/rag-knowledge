# Incremental Dependencies & Models

> Referenced by knowledgebase-init Phase 3 (core deps), Phase 4 (project deps), Phase 5 (models).
> **Core principle**: only install/download what audit (Phase 1) marked missing.

## Core Dependencies (Phase 3)

| Dep | Check | Install if missing |
|-----|-------|--------------------|
| uv | `command -v uv` / `where uv` | Linux/macOS: `curl -LsSf https://astral.sh/uv/install.sh \| sh` · Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| Node.js ≥18 | `node --version` | Linux: nodesource setup_20.x · macOS: `brew install node` · Windows: nodejs.org |
| Python 3.12 | (uv manages) | `uv python install 3.12` |
| Git | `git --version` | Warn only (install link) |
| Docker | `docker --version` | Warn only (Neo4j needs it, rest works) |

After uv install, ensure on PATH same session: `export PATH="$HOME/.local/bin:$PATH"` (Linux/macOS) or PowerShell `$env:PATH += ";$env:USERPROFILE\.local\bin"`.

## Project Dependencies (Phase 4)

For torch/GPU strategy, see [gpu-and-torch.md](gpu-and-torch.md).

| Component | Install if missing | Incremental note |
|-----------|-------------------|------------------|
| Backend (.venv) | `cd backend && uv sync --python 3.12` | cpu-forced: see gpu-and-torch.md §cpu-forced first |
| Web (node_modules) | `cd web && npm install` | Existing → incremental `npm install` (no reinstall) |
| kb-mcp (.venv) | `cd kb-mcp && uv sync` | |
| CLI (node_modules) | `cd command && npm install` | |

### Backend failure causes

- Network/proxy blocks PyTorch index → set `HTTPS_PROXY` or switch network
- Disk full (need ~3GB) → free space
- No Python 3.12 → `uv python install 3.12`

## Models (Phase 5)

### BGE-M3 (~2.2GB) — download only if cache invalid

**Cache validity check** (download前必做):

```bash
# Valid = snapshots/ exists, non-empty, has pytorch_model.bin > 1GB
SNAP="models_cache/hub/models--BAAI--bge-m3/snapshots"
# Linux/macOS
[ -d "$SNAP" ] && find "$SNAP" -name "pytorch_model.bin" -size +1G 2>/dev/null | grep -q . && echo CACHED || echo MISSING
```

- CACHED → skip download
- MISSING → `ragctl model --source <modelscope|hf-mirror|huggingface>`

### MinerU (~5-7GB) — download only if not configured

**Check**: `~/.mineru.json` has `models-dir` pointing to non-empty dir. Or via backend API:

```bash
curl -s http://localhost:<BACKEND_PORT>/api/v1/mineru/status
# {"available": true} → skip; {"available": false} → download
```

- Ready → skip
- Missing → `ragctl mineru-model`

> `ragctl model` calls `download_model.py` (multi-source fallback + resumable). `ragctl mineru-model` calls `mineru.cli.models_download`. Both show progress.

### Model source mapping (config.yml `embedding.model_source`)

| User choice | config.yml | .env HF_ENDPOINT |
|-------------|-----------|-------------------|
| modelscope (default, China) | `modelscope` | `https://hf-mirror.com` |
| hf-mirror | `hf-mirror` | `https://hf-mirror.com` |
| huggingface (overseas) | `huggingface` | `https://huggingface.co` |
