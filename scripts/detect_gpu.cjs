#!/usr/bin/env node
/**
 * detect_gpu.js — Cross-platform GPU detection for RAG Knowledge Platform
 * ════════════════════════════════════════════════════════════════════════
 * Used by the knowledgebase-init skill (Phase 0) to determine which PyTorch
 * wheel variant to install: cu130 (NVIDIA CUDA) / cpu / mps (Apple Silicon).
 *
 * Output: JSON to stdout with:
 *   {
 *     "platform": "win32" | "linux" | "darwin",
 *     "arch": "x64" | "arm64" | ...,
 *     "gpu_vendor": "nvidia" | "amd-rocm" | "apple-mps" | "intel-cpu" | "none",
 *     "gpu_name": "NVIDIA GeForce RTX 4070 Ti SUPER" | null,
 *     "vram_mb": 16376 | null,
 *     "cuda_driver_version": "13.2" | null,
 *     "torch_variant": "cuda" | "cpu-forced" | "mps" | "rocm" | "cpu",
 *     "torch_wheel": "+cu130" | "+cpu" | "PyPI-default",
 *     "description": "human-readable summary"
 *   }
 *
 * Exit code 0 = detection succeeded; 1 = detection failed (fallback to cpu).
 *
 * Usage:
 *   node scripts/detect_gpu.js              → pretty-printed JSON
 *   node scripts/detect_gpu.js --quiet      → JSON only (no banner)
 */
'use strict';

const { execSync } = require('child_process');
const os = require('os');

const QUIET = process.argv.includes('--quiet') || process.argv.includes('-q');
const VERIFY_TORCH = process.argv.includes('--verify-torch') || process.argv.includes('--check-torch');

function log(msg) {
  if (!QUIET) process.stderr.write(msg + '\n');
}

function tryExec(cmd, timeoutMs = 8000) {
  try {
    return execSync(cmd, {
      encoding: 'utf8',
      timeout: timeoutMs,
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
      shell: os.platform() === 'win32',
    }).trim();
  } catch {
    return null;
  }
}

// ── Platform ──────────────────────────────────────────────────────────
const platform = os.platform(); // win32 | linux | darwin
const arch = os.arch();         // x64 | arm64 | ia32

function detectNvidia() {
  // nvidia-smi exists on Windows + Linux (NVIDIA driver installed).
  // On macOS it rarely exists (deprecated CUDA support).
  const out = tryExec('nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader', 8000);
  if (!out) return null;
  const firstLine = out.split('\n')[0].trim();
  if (!firstLine || firstLine.toLowerCase().includes('no devices')) return null;
  // Parse: "NVIDIA GeForce RTX 4070 Ti SUPER, 16376 MiB, 596.36"
  const parts = firstLine.split(',').map(s => s.trim());
  const name = parts[0] || null;
  const vramRaw = parts[1] || '';
  const vramMatch = vramRaw.match(/(\d+)\s*MiB/i);
  const vramMb = vramMatch ? parseInt(vramMatch[1], 10) : null;
  const driverVersion = parts[2] || null;
  // CUDA version from full nvidia-smi output
  const fullOut = tryExec('nvidia-smi', 5000);
  let cudaVersion = null;
  if (fullOut) {
    const m = fullOut.match(/CUDA Version:\s*([\d.]+)/);
    if (m) cudaVersion = m[1];
  }
  return { name, vramMb, driverVersion, cudaVersion };
}

function detectAmdRocm() {
  // rocm-smi only on Linux with AMD GPU + ROCm installed.
  if (platform !== 'linux') return null;
  const out = tryExec('rocm-smi --showproductname', 5000);
  if (!out) return null;
  if (out.includes('No devices') || out.includes('command not found')) return null;
  const lines = out.split('\n').filter(l => l.includes('Card series') || l.includes('GPU'));
  const name = lines[0] ? lines[0].replace(/^.*:\s*/, '').trim() : 'AMD GPU (ROCm)';
  return { name, vramMb: null, driverVersion: null, cudaVersion: null };
}

function detectAppleSilicon() {
  if (platform !== 'darwin') return null;
  const brand = tryExec('sysctl -n machdep.cpu.brand_string', 3000);
  if (!brand) return null;
  if (brand.includes('Apple')) {
    // Apple Silicon (M1/M2/M3/M4) — MPS available
    return { name: brand.trim(), vramMb: null, driverVersion: null, cudaVersion: null, isApple: true };
  }
  if (brand.includes('Intel')) {
    return { name: brand.trim(), vramMb: null, driverVersion: null, cudaVersion: null, isApple: false };
  }
  return null;
}

// ── Main detection ────────────────────────────────────────────────────
function detect() {
  const nvidia = detectNvidia();
  const amd = detectAmdRocm();
  const apple = detectAppleSilicon();

  let gpuVendor = 'none';
  let gpuName = null;
  let vramMb = null;
  let cudaDriver = null;

  if (nvidia && nvidia.name) {
    gpuVendor = 'nvidia';
    gpuName = nvidia.name;
    vramMb = nvidia.vramMb;
    cudaDriver = nvidia.cudaVersion;
  } else if (amd && amd.name) {
    gpuVendor = 'amd-rocm';
    gpuName = amd.name;
  } else if (apple) {
    gpuVendor = apple.isApple ? 'apple-mps' : 'intel-cpu';
    gpuName = apple.name;
  } else {
    gpuVendor = 'none';
  }

  // ── Determine torch_variant + torch_wheel ──────────────────────────
  // PyTorch cu130 index only serves Win + Linux x86_64 wheels.
  // macOS and Linux aarch64 use PyPI default (CPU or MPS).
  const isX86_64 = (arch === 'x64' || arch === 'ia32');
  const supportsCu130Index = (platform === 'win32' || platform === 'linux') && isX86_64;

  let torchVariant;
  let torchWheel;

  if (gpuVendor === 'nvidia') {
    if (supportsCu130Index) {
      torchVariant = 'cuda';
      torchWheel = '+cu130';
    } else {
      // NVIDIA on macOS or Linux aarch64 — no cu130 wheel, use PyPI default
      torchVariant = 'cpu';
      torchWheel = 'PyPI-default';
    }
  } else if (gpuVendor === 'amd-rocm') {
    // ROCm: PyPI wheel works with ROCm runtime (Linux x86_64)
    torchVariant = 'rocm';
    torchWheel = 'PyPI-default';
  } else if (gpuVendor === 'apple-mps') {
    torchVariant = 'mps';
    torchWheel = 'PyPI-default';
  } else if (gpuVendor === 'none' && supportsCu130Index) {
    // ⭐ No GPU but Win/Linux x86_64 → marker would install cu130 (wasteful).
    // Force CPU wheel to save ~2GB and faster load.
    torchVariant = 'cpu-forced';
    torchWheel = '+cpu';
  } else {
    // No GPU on macOS or Linux aarch64 → PyPI default is already CPU
    torchVariant = 'cpu';
    torchWheel = 'PyPI-default';
  }

  const descriptions = {
    cuda: `NVIDIA GPU detected — will install CUDA-accelerated PyTorch (+cu130)`,
    'cpu-forced': `No GPU on Win/Linux x86_64 — will force CPU PyTorch (+cpu, saves ~2GB)`,
    mps: `Apple Silicon detected — PyTorch MPS acceleration available (PyPI wheel)`,
    rocm: `AMD GPU with ROCm detected — PyPI wheel + ROCm runtime`,
    cpu: `CPU-only platform — PyTorch CPU mode (PyPI wheel)`,
  };

  return {
    platform,
    platform_label: platform === 'win32' ? 'windows' : platform === 'darwin' ? 'macos' : 'linux',
    arch,
    gpu_vendor: gpuVendor,
    gpu_name: gpuName,
    vram_mb: vramMb,
    cuda_driver_version: cudaDriver,
    torch_variant: torchVariant,
    torch_wheel: torchWheel,
    supports_cu130_index: supportsCu130Index,
    description: descriptions[torchVariant] || 'Unknown GPU configuration',
  };
}

// ── Torch verification ────────────────────────────────────────────────
// Checks if the installed torch in backend/.venv matches the detected GPU.
// Writes a temp .py file (avoids shell quoting issues with python -c on Windows).
const path = require('path');

function verifyTorch(gpuResult) {
  const result = { ...gpuResult, torch_installed: false, torch_match: null };
  const scriptDir = path.dirname(__filename);
  // PROJECT_ROOT = parent of scripts/
  const projectRoot = path.resolve(scriptDir, '..');
  const venvPython = gpuResult.platform === 'win32'
    ? path.join(projectRoot, 'backend', '.venv', 'Scripts', 'python.exe')
    : path.join(projectRoot, 'backend', '.venv', 'bin', 'python');

  const fs = require('fs');
  if (!fs.existsSync(venvPython)) {
    result.torch_match = 'no-venv';
    result.torch_message = 'backend/.venv not found — run ragctl deps first';
    return result;
  }

  // Write temp script to avoid quoting issues
  const tmpScript = path.join(require('os').tmpdir(), 'ragctl_torch_verify.py');
  const pyCode = [
    'import torch, json',
    'd = {',
    '  "version": torch.__version__,',
    '  "cuda": torch.cuda.is_available(),',
    '  "mps": torch.backends.mps.is_available() if hasattr(torch.backends, "mps") else False,',
    '  "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,',
    '}',
    'print(json.dumps(d))',
  ].join('\n');
  try {
    fs.writeFileSync(tmpScript, pyCode, 'utf8');
  } catch (e) {
    result.torch_match = 'error';
    result.torch_message = 'Cannot write temp script: ' + e.message;
    return result;
  }

  const out = tryExec('"' + venvPython + '" "' + tmpScript + '"', 20000);
  try { fs.unlinkSync(tmpScript); } catch {}

  if (!out) {
    result.torch_match = 'error';
    result.torch_message = 'Failed to run torch check (torch may not be installed)';
    return result;
  }

  let torchInfo;
  try {
    torchInfo = JSON.parse(out.split('\n').filter(l => l.trim().startsWith('{'))[0]);
  } catch {
    result.torch_match = 'error';
    result.torch_message = 'Cannot parse torch output: ' + out.slice(0, 200);
    return result;
  }

  result.torch_installed = true;
  result.torch_version = torchInfo.version;
  result.torch_cuda = torchInfo.cuda;
  result.torch_mps = torchInfo.mps;

  // Determine actual torch device capability
  const actualDevice = torchInfo.cuda ? 'cuda'
    : (torchInfo.mps ? 'mps' : 'cpu');

  // Expected variant (normalize cpu-forced → cpu for comparison)
  const expectedVariant = gpuResult.torch_variant.replace('-forced', '');

  // Match logic:
  // - cuda expected + cuda available → match
  // - mps expected + mps available → match
  // - cpu expected + no cuda/mps → match
  // - cuda expected but only cpu available → mismatch (need CUDA reinstall)
  // - cpu-forced expected but cuda available → mismatch (got CUDA, wanted CPU)
  if (expectedVariant === 'cuda' && actualDevice === 'cuda') {
    result.torch_match = 'ok';
    result.torch_message = `torch ${torchInfo.version} with CUDA — GPU acceleration active`;
  } else if (expectedVariant === 'mps' && actualDevice === 'mps') {
    result.torch_match = 'ok';
    result.torch_message = `torch ${torchInfo.version} with MPS — Apple Silicon acceleration active`;
  } else if ((expectedVariant === 'cpu' || expectedVariant === 'rocm') && actualDevice === 'cpu') {
    result.torch_match = 'ok';
    result.torch_message = `torch ${torchInfo.version} CPU mode — matches expected (no CUDA/MPS needed)`;
  } else if (expectedVariant === 'cuda' && actualDevice === 'cpu') {
    result.torch_match = 'mismatch';
    result.torch_message = `Expected CUDA but torch has no CUDA (${torchInfo.version}). Reinstall: uv pip install torch==2.12.1 --index-url https://download.pytorch.org/whl/cu130 --reinstall`;
  } else if (gpuResult.torch_variant === 'cpu-forced' && actualDevice === 'cuda') {
    result.torch_match = 'mismatch';
    result.torch_message = `No GPU but torch is CUDA (${torchInfo.version}). Reinstall CPU: uv pip install torch==2.12.1 --index-url https://download.pytorch.org/whl/cpu --reinstall`;
  } else {
    result.torch_match = 'ok';
    result.torch_message = `torch ${torchInfo.version} — ${actualDevice} mode`;
  }

  return result;
}

// ── Output ────────────────────────────────────────────────────────────
try {
  let result = detect();

  if (VERIFY_TORCH) {
    result = verifyTorch(result);
  }

  if (!QUIET) {
    log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    log('  🖥️  GPU Detection Result');
    log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    log(`  Platform:   ${result.platform_label} (${result.arch})`);
    log(`  GPU Vendor: ${result.gpu_vendor}`);
    log(`  GPU Name:   ${result.gpu_name || 'N/A'}`);
    log(`  VRAM:       ${result.vram_mb ? result.vram_mb + ' MB' : 'N/A'}`);
    log(`  CUDA:       ${result.cuda_driver_version || 'N/A'}`);
    log('');
    log(`  Torch:      ${result.torch_variant} (${result.torch_wheel})`);
    log(`  ${result.description}`);
    if (VERIFY_TORCH && result.torch_installed !== undefined) {
      log('');
      log(`  Torch verify: ${result.torch_match || 'skipped'}`);
      if (result.torch_version) {
        log(`    version:    ${result.torch_version}`);
        log(`    cuda:       ${result.torch_cuda}, mps: ${result.torch_mps}`);
      }
      if (result.torch_message) {
        log(`    ${result.torch_message}`);
      }
    }
    log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  }

  // JSON to stdout (always)
  console.log(JSON.stringify(result, null, 2));
  process.exit(0);
} catch (e) {
  // Fallback: CPU-only
  const fallback = {
    platform,
    platform_label: platform === 'win32' ? 'windows' : platform === 'darwin' ? 'macos' : 'linux',
    arch,
    gpu_vendor: 'none',
    gpu_name: null,
    vram_mb: null,
    cuda_driver_version: null,
    torch_variant: (platform === 'win32' || (platform === 'linux' && isX86_64)) ? 'cpu-forced' : 'cpu',
    torch_wheel: (platform === 'win32' || (platform === 'linux' && (arch === 'x64' || arch === 'ia32'))) ? '+cpu' : 'PyPI-default',
    supports_cu130_index: (platform === 'win32' || platform === 'linux') && (arch === 'x64' || arch === 'ia32'),
    description: `Detection failed (${e.message}) — falling back to CPU`,
    error: e.message,
  };
  console.log(JSON.stringify(fallback, null, 2));
  process.exit(1);
}
