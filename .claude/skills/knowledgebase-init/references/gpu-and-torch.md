# GPU Detection & PyTorch Installation

> Referenced by knowledgebase-init Phase 0 (detection), Phase 4a (install), Phase 11c (verify).

## Detection Script

```bash
node scripts/detect_gpu.cjs                    # pretty output
node scripts/detect_gpu.cjs --quiet            # JSON only
node scripts/detect_gpu.cjs --verify-torch     # detect + verify installed torch match
```

JSON output fields: `platform_label`, `arch`, `gpu_vendor` (nvidia|amd-rocm|apple-mps|intel-cpu|none), `gpu_name`, `vram_mb`, `cuda_driver_version`, `torch_variant`, `torch_wheel`, `torch_match` (ok|mismatch|no-venv|error, verify mode only).

## Inline Detection (when project code not yet cloned)

```
NVIDIA (all platforms):  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
AMD ROCm (Linux only):   rocm-smi --showproductname | head -3
Apple Silicon (macOS):   sysctl -n machdep.cpu.brand_string  → contains "Apple" = MPS
```

## Torch Variant Decision

| GPU | `torch_variant` | Wheel | Rationale |
|-----|-----------------|-------|-----------|
| NVIDIA (Win/Linux x64) | `cuda` | `+cu130` | GPU acceleration |
| NVIDIA (other platforms) | `cpu` | PyPI default | cu130 only supports Win/Linux x64 |
| AMD ROCm (Linux x64) | `rocm` | PyPI default + ROCm runtime | |
| Apple Silicon (macOS) | `mps` | PyPI default | MPS acceleration |
| No GPU (Win/Linux x64) | `cpu-forced` | `+cpu` | Saves ~2GB vs default cu130 |
| No GPU (other platforms) | `cpu` | PyPI default | Already CPU |

## Installation Commands

### Standard (cuda / mps / rocm / cpu)

```bash
cd backend && uv sync --python 3.12
```

Marker in `pyproject.toml` auto-selects: Win/Linux x64 → cu130, others → PyPI.

### cpu-forced (No GPU on Win/Linux x64)

Marker would install wasteful cu130 (~2.5GB). Force CPU wheel instead:

```bash
cd backend
uv venv --python 3.12
uv pip install torch==2.12.1 torchvision==0.27.1 --index-url https://download.pytorch.org/whl/cpu
uv sync --python 3.12   # torch already installed, fills in the rest
```

> If `uv sync` reinstalls cu130 torch over CPU, re-run the `uv pip install --index-url ... --reinstall` line.

## Verification

```bash
node scripts/detect_gpu.cjs --verify-torch
```

Check `torch_match` field:

| Value | Meaning | Action |
|-------|---------|--------|
| `ok` | GPU and torch aligned | Proceed |
| `mismatch` | Misaligned | Reinstall per below |
| `no-venv` | backend/.venv missing | Run Phase 4b first |
| `error` | torch not installed | Run Phase 4b first |

### Mismatch Repair

```bash
# Has GPU but torch lacks CUDA:
cd backend && uv pip install torch==2.12.1 torchvision==0.27.1 --index-url https://download.pytorch.org/whl/cu130 --reinstall

# No GPU but torch is CUDA:
cd backend && uv pip install torch==2.12.1 torchvision==0.27.1 --index-url https://download.pytorch.org/whl/cpu --reinstall
```

## Manual Verification (fallback if script unavailable)

```bash
echo 'import torch; print("torch:",torch.__version__,"cuda:",torch.cuda.is_available(),"mps:",torch.backends.mps.is_available() if hasattr(torch.backends,"mps") else False)' > /tmp/check_torch.py
backend/.venv/Scripts/python.exe /tmp/check_torch.py   # Windows
backend/.venv/bin/python /tmp/check_torch.py            # Linux/macOS
```
