#!/usr/bin/env node

/**
 * ragctl — RAG Knowledge Platform CLI
 * ====================================
 *
 * 最强大的一键式部署工具。所有服务在 dev/prod 下均为静默启动（无终端窗口），
 * 日志统一落盘到 {backend,web}/logs/desktop-stdout.log（与 Tauri 桌面控制台共享）。
 *
 * Commands:
 *   setup    One-click full setup (uv + deps + models + .env)
 *   check    Comprehensive health check — what's missing, how to fix
 *   deps     Install all dependencies with real-time progress
 *   model    Download BGE embedding model (--source modelscope|hf-mirror|huggingface)
 *   up       Start all services (silent — no terminal windows)
 *   down     Stop all services
 *   start    Start a specific service (backend|web|neo4j|all)
 *   stop     Stop a specific service (backend|web|neo4j|all)
 *   restart  Restart a specific service (backend|web|neo4j|all)
 *   status   Show service status
 *   logs     View/tail service logs (backend|web|mineru) [--tail] [--lines N]
 *   version  Show local + remote version (VERSION file + git SHA)
 *   update   Check GitHub for newer release and pull if available
 *   install  Register ragctl globally
 *   desktop  Launch Tauri desktop console
 *   clean    Clean caches and MinerU parse artifacts (--mineru/--logs/--pycache/--model/--all)
 */

'use strict';

const { spawn, exec, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
const net = require('net');
const http = require('http');
const https = require('https');
// Zero-dependency YAML subset — ragctl must run on a fresh clone with NO
// node_modules (js-yaml previously hard-crashed every command on empty
// systems, including the install command itself).
const yaml = require('./mini-yaml.js');
const readline = require('readline');

// ── Project Paths ──────────────────────────────────────────────────────
const PROJECT_ROOT = path.resolve(__dirname, '..');
const BACKEND_DIR = path.join(PROJECT_ROOT, 'backend');
const WEB_DIR = path.join(PROJECT_ROOT, 'web');
const MCP_DIR = path.join(PROJECT_ROOT, 'kb-mcp');
const CONFIG_YML = path.join(PROJECT_ROOT, 'config.yml');
const BACKEND_CONFIG_YML = path.join(BACKEND_DIR, 'config.yml');
const ENV_FILE = path.join(PROJECT_ROOT, '.env');
const RUN_DIR = path.join(PROJECT_ROOT, '.run');
const VERSION_FILE = path.join(PROJECT_ROOT, 'VERSION');
const REQUIRED_PYTHON = '3.12';
const MIN_NODE_MAJOR = 18; // Nuxt 3 + modern CLI; 22 preferred, 18+ accepted
// Canonical remote identity for update checks (override via env if forked)
const GITHUB_OWNER = process.env.RAG_GITHUB_OWNER || 'kingdol666';
const GITHUB_REPO = process.env.RAG_GITHUB_REPO || 'rag-knowledge';
const GITHUB_DEFAULT_BRANCH = process.env.RAG_GITHUB_BRANCH || 'master';

const IS_WIN = os.platform() === 'win32';

// ── Version helpers (single source of truth: root VERSION file) ──────────
function readLocalVersion() {
  try {
    const raw = fs.readFileSync(VERSION_FILE, 'utf8').trim();
    if (raw) return raw.replace(/^v/i, '');
  } catch {}
  // Fallback: command/package.json
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, 'command', 'package.json'), 'utf8'));
    if (pkg.version) return String(pkg.version).replace(/^v/i, '');
  } catch {}
  return '0.0.0';
}

function getLocalGitInfo() {
  const info = { sha: null, branch: null, dirty: false, isGit: false };
  try {
    execSync('git rev-parse --is-inside-work-tree', {
      cwd: PROJECT_ROOT, stdio: 'ignore', timeout: 5000, windowsHide: true,
    });
    info.isGit = true;
  } catch {
    return info;
  }
  try {
    info.sha = execSync('git rev-parse --short HEAD', {
      cwd: PROJECT_ROOT, encoding: 'utf8', timeout: 5000, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true,
    }).trim();
  } catch {}
  try {
    info.branch = execSync('git rev-parse --abbrev-ref HEAD', {
      cwd: PROJECT_ROOT, encoding: 'utf8', timeout: 5000, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true,
    }).trim();
  } catch {}
  try {
    const dirty = execSync('git status --porcelain', {
      cwd: PROJECT_ROOT, encoding: 'utf8', timeout: 8000, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true,
    }).trim();
    info.dirty = dirty.length > 0;
  } catch {}
  return info;
}

// Semver compare: returns -1 if a<b, 0 if equal, 1 if a>b. Non-semver falls back to string compare.
function compareSemver(a, b) {
  const parse = (v) => {
    const clean = String(v || '0').replace(/^v/i, '').split(/[-+]/)[0];
    const parts = clean.split('.').map((x) => {
      const n = parseInt(x, 10);
      return Number.isFinite(n) ? n : 0;
    });
    while (parts.length < 3) parts.push(0);
    return parts;
  };
  const pa = parse(a);
  const pb = parse(b);
  for (let i = 0; i < 3; i++) {
    if (pa[i] < pb[i]) return -1;
    if (pa[i] > pb[i]) return 1;
  }
  return 0;
}

function httpsGetJson(url, timeoutMs = 12000) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, {
      headers: {
        'User-Agent': `ragctl/${readLocalVersion()}`,
        Accept: 'application/vnd.github+json',
      },
      timeout: timeoutMs,
    }, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (c) => { body += c; });
      res.on('end', () => {
        if (res.statusCode && res.statusCode >= 400) {
          reject(new Error(`HTTP ${res.statusCode}: ${body.slice(0, 200)}`));
          return;
        }
        try { resolve(JSON.parse(body)); }
        catch (e) { reject(new Error(`Invalid JSON from ${url}: ${e.message}`)); }
      });
    });
    req.on('timeout', () => { req.destroy(new Error(`Timeout fetching ${url}`)); });
    req.on('error', reject);
  });
}

async function fetchRemoteVersionInfo() {
  // Prefer GitHub latest release tag; fall back to default-branch VERSION file content.
  const result = {
    remoteVersion: null,
    remoteTag: null,
    remoteSha: null,
    remoteUrl: `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}`,
    source: null, // 'release' | 'branch-version' | 'branch-sha'
    error: null,
  };
  try {
    const release = await httpsGetJson(
      `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest`,
    );
    if (release && release.tag_name) {
      result.remoteTag = release.tag_name;
      result.remoteVersion = String(release.tag_name).replace(/^v/i, '');
      result.remoteSha = (release.target_commitish && release.target_commitish.length === 40)
        ? release.target_commitish.slice(0, 7)
        : null;
      result.remoteUrl = release.html_url || result.remoteUrl;
      result.source = 'release';
      return result;
    }
  } catch (e) {
    // No releases (or network/API error) — try branch VERSION content next.
    result.error = `release lookup: ${e.message}`;
  }

  try {
    // Raw VERSION from default branch
    const rawUrl = `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/${GITHUB_DEFAULT_BRANCH}/VERSION`;
    const body = await new Promise((resolve, reject) => {
      const req = https.get(rawUrl, {
        headers: { 'User-Agent': `ragctl/${readLocalVersion()}` },
        timeout: 12000,
      }, (res) => {
        let data = '';
        res.setEncoding('utf8');
        res.on('data', (c) => { data += c; });
        res.on('end', () => {
          if (res.statusCode && res.statusCode >= 400) {
            reject(new Error(`HTTP ${res.statusCode}`));
            return;
          }
          resolve(data);
        });
      });
      req.on('timeout', () => req.destroy(new Error('Timeout')));
      req.on('error', reject);
    });
    const ver = String(body || '').trim().replace(/^v/i, '');
    if (ver) {
      result.remoteVersion = ver;
      result.source = 'branch-version';
    }
  } catch (e) {
    result.error = (result.error ? result.error + '; ' : '') + `branch VERSION: ${e.message}`;
  }

  // Always try to get tip SHA of default branch for SHA-level freshness
  try {
    const ref = await httpsGetJson(
      `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/commits/${GITHUB_DEFAULT_BRANCH}`,
    );
    if (ref && ref.sha) {
      result.remoteSha = String(ref.sha).slice(0, 7);
      if (!result.source) result.source = 'branch-sha';
    }
  } catch (e) {
    result.error = (result.error ? result.error + '; ' : '') + `branch SHA: ${e.message}`;
  }

  return result;
}

function runGit(args, opts = {}) {
  const { silent = true, allowFail = false, timeout = 120000 } = opts;
  // spawnSync for proper argv (no shell quoting bugs on Windows)
  const { spawnSync } = require('child_process');
  const res = spawnSync('git', args, {
    cwd: PROJECT_ROOT,
    encoding: 'utf8',
    timeout,
    windowsHide: true,
    // inherit stderr so user sees progress; capture stdout
    stdio: silent ? ['ignore', 'pipe', 'pipe'] : ['ignore', 'pipe', 'inherit'],
  });
  if (res.error) {
    if (allowFail) return { code: 1, stdout: '', stderr: String(res.error.message || res.error) };
    throw res.error;
  }
  const code = res.status == null ? 1 : res.status;
  if (code !== 0 && !allowFail) {
    const err = new Error(`git ${args.join(' ')} failed (exit ${code})`);
    err.status = code;
    err.stdout = res.stdout || '';
    err.stderr = res.stderr || '';
    throw err;
  }
  return { code, stdout: res.stdout || '', stderr: res.stderr || '' };
}

/**
 * Compare local HEAD vs a remote tip SHA.
 * Returns: 'behind' | 'ahead' | 'equal' | 'diverged' | 'unknown'
 * Uses git merge-base ancestry when possible (works offline after fetch).
 */
function compareGitTips(localSha, remoteSha) {
  if (!localSha || !remoteSha) return 'unknown';
  const loc = String(localSha).slice(0, 7);
  const rem = String(remoteSha).slice(0, 7);
  if (loc === rem) return 'equal';
  // Try full SHAs via git rev-parse / merge-base
  try {
    const fullLocal = runGit(['rev-parse', 'HEAD'], { allowFail: true }).stdout.trim();
    // Resolve remote sha if short
    let fullRemote = remoteSha;
    const resolved = runGit(['rev-parse', '--verify', remoteSha], { allowFail: true });
    if (resolved.code === 0 && resolved.stdout.trim()) fullRemote = resolved.stdout.trim();
    // If remote short sha isn't in local object db yet, try origin/branch
    if (resolved.code !== 0) {
      const originRef = runGit(['rev-parse', `origin/${GITHUB_DEFAULT_BRANCH}`], { allowFail: true });
      if (originRef.code === 0) fullRemote = originRef.stdout.trim();
    }
    if (fullLocal && fullRemote && fullLocal === fullRemote) return 'equal';
    const aIsAncOfB = runGit(['merge-base', '--is-ancestor', fullLocal, fullRemote], { allowFail: true });
    const bIsAncOfA = runGit(['merge-base', '--is-ancestor', fullRemote, fullLocal], { allowFail: true });
    if (aIsAncOfB.code === 0) return 'behind';   // local ancestor of remote → need pull
    if (bIsAncOfA.code === 0) return 'ahead';    // remote ancestor of local → local has unpushed commits
    // Both not ancestors → diverged (or objects missing)
    if (aIsAncOfB.code === 1 && bIsAncOfA.code === 1) return 'diverged';
  } catch {}
  // Fallback: unequal short shas without ancestry info
  return loc === rem ? 'equal' : 'unknown';
}

/**
 * Best-effort: refresh origin refs (network) then return origin/<branch> short SHA.
 * Non-fatal on network failure — falls back to existing origin/* ref.
 */
function fetchOriginTip(branch = GITHUB_DEFAULT_BRANCH) {
  runGit(['fetch', 'origin', branch, '--prune'], { allowFail: true, timeout: 60000 });
  const r = runGit(['rev-parse', '--short', `origin/${branch}`], { allowFail: true });
  if (r.code === 0 && r.stdout.trim()) return r.stdout.trim();
  return null;
}

// ── Log paths (single source of truth — MUST match src-tauri watch_log paths) ──
// Both ragctl and Tauri write/read the same files so the desktop log viewer works
// regardless of which launcher started the service. Truncated on each start.
const LOG_PATHS = {
  backend: path.join(BACKEND_DIR, 'logs', 'desktop-stdout.log'),
  web:     path.join(WEB_DIR, 'logs', 'desktop-stdout.log'),
  mineru:  path.join(BACKEND_DIR, 'logs', 'mineru-api.log'),
};
function getLogPath(service) { return LOG_PATHS[service]; }

// ── Runtime PID bookkeeping (.run/*.pid) ────────────────────────────────
// Used by status/stop to avoid relying solely on port scans (which can false-
// positive when unrelated processes bind the same port).
function ensureRunDir() {
  try { fs.mkdirSync(RUN_DIR, { recursive: true }); } catch {}
}
function pidFile(service, mode) {
  return path.join(RUN_DIR, `${service}-${mode || getAppMode()}.pid`);
}
function writePid(service, mode, pid, port) {
  ensureRunDir();
  const payload = { pid, port, mode, startedAt: new Date().toISOString() };
  try { fs.writeFileSync(pidFile(service, mode), JSON.stringify(payload), 'utf8'); } catch {}
}
function readPid(service, mode) {
  try {
    const raw = fs.readFileSync(pidFile(service, mode), 'utf8');
    return JSON.parse(raw);
  } catch { return null; }
}
function clearPid(service, mode) {
  try { fs.unlinkSync(pidFile(service, mode)); } catch {}
}
function isPidAlive(pid) {
  if (!pid || !Number.isFinite(pid)) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    // On Windows, process.kill(pid, 0) can throw for access/ESRCH.
    // Fall through to a tasklist probe.
  }
  if (!IS_WIN) return false;
  try {
    const out = execSync(`tasklist /FI "PID eq ${pid}" /NH`, {
      encoding: 'utf8', timeout: 5000, stdio: 'pipe', windowsHide: true,
    });
    return out.includes(String(pid));
  } catch { return false; }
}

// ── ANSI Colors ────────────────────────────────────────────────────────
const C = {
  RESET: '\x1b[0m', BOLD: '\x1b[1m',
  RED: '\x1b[91m', GREEN: '\x1b[92m', YELLOW: '\x1b[93m',
  CYAN: '\x1b[96m', GRAY: '\x1b[90m', MAGENTA: '\x1b[95m',
};

function _c(color, text) { return `${color}${text}${C.RESET}`; }
function info(msg) { console.log(`  ${_c(C.CYAN, '[INFO]')} ${msg}`); }
function ok(msg) { console.log(`  ${_c(C.GREEN, '[✓]')} ${msg}`); }
function warn(msg) { console.log(`  ${_c(C.YELLOW, '[!]')} ${msg}`); }
function err(msg) { console.error(`  ${_c(C.RED, '[✗]')} ${msg}`); }
function step(msg) { console.log(`\n  ${_c(C.BOLD, _c(C.CYAN, '▶'))} ${_c(C.BOLD, msg)}`); }

function header(title) {
  const bar = '='.repeat(60);
  console.log('\n' + _c(C.BOLD, _c(C.CYAN, bar)));
  console.log(_c(C.BOLD, _c(C.CYAN, '  ' + title)));
  console.log(_c(C.BOLD, _c(C.CYAN, bar)) + '\n');
}

// ── Config Readers ─────────────────────────────────────────────────────
function readYaml(filePath) {
  if (!fs.existsSync(filePath)) return {};
  try { return yaml.load(fs.readFileSync(filePath, 'utf8')) || {}; }
  catch { return {}; }
}

function readEnv(filePath) {
  const result = {};
  if (!fs.existsSync(filePath)) return result;
  for (const line of fs.readFileSync(filePath, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const idx = trimmed.indexOf('=');
    if (idx > 0) result[trimmed.slice(0, idx).trim()] = trimmed.slice(idx + 1).trim();
  }
  return result;
}

function writeEnv(env) {
  const lines = [
    '# ============================================',
    '# RAG Knowledge Platform - Environment Variables',
    '# ============================================',
    '# Env vars override config.yml values.',
    '# ============================================',
    '',
  ];
  for (const [k, v] of Object.entries(env)) {
    if (v === '') lines.push(`# ${k}=`);
    else lines.push(`${k}=${v}`);
  }
  lines.push('');
  fs.writeFileSync(ENV_FILE, lines.join('\n'), 'utf8');
}

function getAppMode() {
  // Project-wide precedence: process.env > .env > default 'dev'.
  // The previous .env-only read made `APP_MODE=prod ragctl up` launch dev,
  // diverging from the backend (config.py) and Tauri (commands.rs) which both
  // honor process.env first.
  const envMode = process.env.APP_MODE;
  if (envMode === 'prod' || envMode === 'dev') return envMode;
  const env = readEnv(ENV_FILE);
  return env.APP_MODE || 'dev';
}

// ── Port / Process Helpers ────────────────────────────────────────────
function portInUse(port) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(1000);
    socket.once('connect', () => { socket.destroy(); resolve(true); });
    socket.once('timeout', () => { socket.destroy(); resolve(false); });
    socket.once('error', () => { resolve(false); });
    socket.connect(port, '127.0.0.1');
  });
}

function findPidOnPort(port) {
  try {
    if (IS_WIN) {
      const output = execSync(`netstat -ano | findstr :${port} | findstr LISTENING`, { encoding: 'utf8', timeout: 10000, stdio: 'pipe', windowsHide: true });
      const parts = output.trim().split(/\s+/);
      if (parts.length > 0) return parseInt(parts[parts.length - 1]);
    } else {
      const output = execSync(`lsof -ti:${port} 2>/dev/null || ss -tlnp | grep ':${port}'`, { encoding: 'utf8', timeout: 10000, stdio: ['pipe','pipe','pipe'] });
      const pid = output.trim().split('\n')[0];
      if (pid) return parseInt(pid);
    }
  } catch {}
  return null;
}

function killPid(pid, force = false) {
  try {
    if (IS_WIN) {
      execSync(`taskkill /PID ${pid} /T${force ? ' /F' : ''}`, { timeout: 10000, stdio: 'pipe', windowsHide: true });
    } else {
      process.kill(pid, force ? 'SIGKILL' : 'SIGTERM');
    }
    return true;
  } catch { return false; }
}

function commandExists(cmd) {
  try {
    execSync(IS_WIN ? `where ${cmd}` : `command -v ${cmd}`, { stdio: 'ignore', timeout: 3000, shell: IS_WIN });
    return true;
  } catch { return false; }
}

// Locate the uv binary across versions: modern uv (0.4+) installs to
// ~/.local/bin on every OS; older installs used ~/.cargo/bin. Returns the full
// path to the binary if found, else "uv" / "uv.exe" (lets PATH resolve it).
function findUvDir() {
  const bin = IS_WIN ? 'uv.exe' : 'uv';
  for (const rel of ['.local', '.cargo']) {
    const dir = path.join(os.homedir(), rel, 'bin');
    if (fs.existsSync(path.join(dir, bin))) return dir;
  }
  return null;
}
function findUvBin() {
  const dir = findUvDir();
  if (dir) return path.join(dir, IS_WIN ? 'uv.exe' : 'uv');
  return IS_WIN ? 'uv.exe' : 'uv';   // fallback: let CreateProcess/PATH resolve
}

// Ensure uv is callable in THIS process before any spawn('uv', ...). Fresh
// terminals opened right after `ragctl setup` (which setx's PATH) may not yet
// have uv resolvable, and modern uv lives in ~/.local/bin which some shells
// don't source by default. Safe to call repeatedly.
function ensureUvOnPath() {
  if (commandExists('uv')) return true;
  const dir = findUvDir();
  if (dir) {
    process.env.PATH = `${dir}${path.delimiter}${process.env.PATH}`;
    return commandExists('uv');
  }
  return false;
}

// Persist a directory onto the user PATH without the classic Windows `setx
// PATH "%PATH%;..."` trap (setx truncates at 1024 chars and expands %PATH%
// incorrectly when nested inside cmd.exe). Prefer PowerShell [Environment]
// for user-scope updates; on POSIX just print an export hint.
function appendUserPath(dir) {
  if (!dir) return false;
  try {
    if (IS_WIN) {
      const ps = `
$dir = '${dir.replace(/'/g, "''")}';
$cur = [Environment]::GetEnvironmentVariable('Path', 'User');
if (-not $cur) { $cur = '' }
$parts = $cur -split ';' | Where-Object { $_ -and $_.Trim() -ne '' }
if ($parts -contains $dir) { exit 0 }
$new = if ($cur) { "$cur;$dir" } else { $dir }
[Environment]::SetEnvironmentVariable('Path', $new, 'User')
`;
      execSync(`powershell -NoProfile -ExecutionPolicy Bypass -Command ${JSON.stringify(ps)}`, {
        stdio: 'ignore', timeout: 10000, windowsHide: true,
      });
      process.env.PATH = `${dir}${path.delimiter}${process.env.PATH || ''}`;
      return true;
    }
    // POSIX: cannot safely rewrite shell rc from here; caller should hint.
    process.env.PATH = `${dir}${path.delimiter}${process.env.PATH || ''}`;
    return false;
  } catch {
    return false;
  }
}

function nodeMajor() {
  const m = String(process.versions.node || '').match(/^(\d+)/);
  return m ? parseInt(m[1], 10) : 0;
}

function hasPython312() {
  // Prefer uv-managed pin (backend/.python-version or pyproject requires-python).
  // Also accept a system python3.12 if present — uv will still manage the venv.
  if (commandExists('python3.12') || commandExists('py')) {
    try {
      if (commandExists('python3.12')) {
        const v = execSync('python3.12 --version', { encoding: 'utf8', timeout: 5000, stdio: ['pipe','pipe','pipe'] }).trim();
        if (/3\.12\./.test(v)) return true;
      }
    } catch {}
  }
  // uv can download CPython 3.12 on demand when network is available — treat
  // "uv present" as sufficient for setup; actual pin is enforced by uv sync.
  return commandExists('uv') || !!findUvDir();
}

async function waitForHttpOk(url, { timeoutSec = 45, intervalMs = 1000, expectBodyIncludes = null } = {}) {
  const deadline = Date.now() + timeoutSec * 1000;
  let last = { code: 0, body: '' };
  while (Date.now() < deadline) {
    last = await httpGet(url, Math.min(intervalMs + 500, 5000));
    if (last.code === 200) {
      if (!expectBodyIncludes || (last.body && last.body.includes(expectBodyIncludes))) {
        return { ok: true, ...last };
      }
    }
    await sleep(intervalMs);
  }
  return { ok: false, ...last };
}

function preflightReady({ requireModel = false } = {}) {
  // Lightweight gate used by `up`/`start` so a fresh clone fails fast with an
  // actionable message instead of spawning half-broken services.
  const problems = [];
  if (!fs.existsSync(path.join(BACKEND_DIR, 'app', 'main.py'))) {
    problems.push('backend missing — run: ragctl setup');
  }
  if (!fs.existsSync(path.join(WEB_DIR, 'package.json'))) {
    problems.push('web missing — run: ragctl setup');
  }
  if (!fs.existsSync(ENV_FILE)) {
    problems.push('.env missing — run: ragctl setup  (or copy .env.example → .env)');
  }
  if (!fs.existsSync(path.join(BACKEND_DIR, '.venv'))) {
    problems.push('backend deps not installed — run: ragctl setup  (or ragctl deps)');
  }
  if (!fs.existsSync(path.join(WEB_DIR, 'node_modules'))) {
    problems.push('web deps not installed — run: ragctl setup  (or ragctl deps)');
  }
  if (!fs.existsSync(path.join(MCP_DIR, '.venv'))) {
    problems.push('kb-mcp deps not installed — run: ragctl setup  (or ragctl deps)');
  }
  if (!ensureUvOnPath()) {
    problems.push('uv not found on PATH — run: ragctl setup');
  }
  if (nodeMajor() < MIN_NODE_MAJOR) {
    problems.push(`Node.js ${process.version} is too old (need >= ${MIN_NODE_MAJOR}). Install from https://nodejs.org/`);
  }
  if (requireModel) {
    const modelDir = path.join(PROJECT_ROOT, 'models_cache', 'hub', 'models--BAAI--bge-m3');
    const hfDir = path.join(os.homedir(), '.cache', 'huggingface', 'hub', 'models--BAAI--bge-m3');
    const present = [modelDir, hfDir].some(d => fs.existsSync(d));
    if (!present) problems.push('BGE-M3 model not cached — run: ragctl model  (optional; first index will auto-download)');
  }
  return problems;
}

// ── spawnAsync — run command with real-time stdout/stderr, return exit code ──
function spawnAsync(command, args = [], opts = {}) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd: opts.cwd || PROJECT_ROOT,
      env: { ...process.env, ...(opts.env || {}) },
      stdio: opts.silent ? 'pipe' : 'inherit',
      shell: IS_WIN && !opts.noShell,
    });
    let stdout = '', stderr = '';
    if (opts.silent) {
      child.stdout.on('data', d => stdout += d);
      child.stderr.on('data', d => stderr += d);
    }
    child.on('close', code => resolve({ code: code || 0, stdout, stderr }));
    child.on('error', e => resolve({ code: 1, stdout, stderr: e.message }));
  });
}

// ── downloadFile — download a URL to a local path with progress ──
function downloadFile(url, destPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(destPath);
    const protocol = url.startsWith('https') ? https : http;
    const req = protocol.get(url, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        file.close();
        fs.unlinkSync(destPath);
        return downloadFile(res.headers.location, destPath).then(resolve).catch(reject);
      }
      if (res.statusCode !== 200) {
        file.close();
        fs.unlinkSync(destPath);
        return reject(new Error(`HTTP ${res.statusCode}`));
      }
      const total = parseInt(res.headers['content-length'] || '0');
      let downloaded = 0;
      res.on('data', chunk => {
        downloaded += chunk.length;
        if (total > 0) {
          const pct = Math.round((downloaded / total) * 100);
          const bar = '█'.repeat(Math.floor(pct / 2)) + '░'.repeat(50 - Math.floor(pct / 2));
          process.stdout.write(`\r  [${bar}] ${pct}% (${(downloaded / 1024 / 1024).toFixed(1)} MB / ${(total / 1024 / 1024).toFixed(1)} MB)`);
        }
      });
      res.pipe(file);
      file.on('finish', () => { file.close(); process.stdout.write('\n'); resolve(); });
    });
    req.on('error', (e) => { file.close(); try { fs.unlinkSync(destPath); } catch {} reject(e); });
    req.setTimeout(300000, () => { req.destroy(); file.close(); try { fs.unlinkSync(destPath); } catch {} reject(new Error('Download timeout')); });
  });
}

// ═══════════════════════════════════════════════════════════════════════
//  ⭐ NEW: check — Comprehensive pre-flight with solutions
// ═══════════════════════════════════════════════════════════════════════

async function cmdCheck() {
  header('RAG Knowledge Platform — 全面环境检查');
  const results = { pass: [], warn: [], fail: [], fix: [] };
  const fix = (name, solution) => ({ name, solution });

  function addResult(category, name, detail, solution) {
    const icon = category === 'pass' ? '✅' : category === 'warn' ? '⚠️' : '❌';
    console.log(`  ${icon} ${_c(C.BOLD, name)}`);
    if (detail) console.log(`     ${_c(C.GRAY, detail)}`);
    if (solution) console.log(`     ${_c(C.YELLOW, '👉 ' + solution)}`);
    results[category].push(name);
    if (solution && category !== 'pass') results.fix.push(fix(name, solution));
    console.log();
  }

  // 1. OS check
  console.log(`\n${_c(C.BOLD, '── 系统环境 ──')}\n`);
  console.log(`  平台: ${os.platform()} ${os.arch()} ${os.release()}`);
  console.log(`  主机: ${os.hostname()}`);
  console.log(`  Node : ${process.version}`);
  console.log(`  CWD  : ${PROJECT_ROOT}`);

  // 2. Prerequisites
  console.log(`\n${_c(C.BOLD, '── 核心依赖 ──')}\n`);

  // Ensure freshly-installed uv is visible in THIS process before probing.
  ensureUvOnPath();

  // uv check with version
  let uvVersion = '';
  try {
    uvVersion = execSync('uv --version', { encoding: 'utf8', timeout: 5000, stdio: ['pipe','pipe','pipe'] }).trim();
    addResult('pass', 'uv (Python 包管理器)', `已安装: ${uvVersion}`, null);
  } catch {
    addResult('fail', 'uv (Python 包管理器)', '未找到 uv', IS_WIN
      ? '运行: ragctl setup  或  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
      : '运行: ragctl setup  或  curl -LsSf https://astral.sh/uv/install.sh | sh');
  }

  // Node.js (accept >=18; recommend 22)
  const major = nodeMajor();
  if (major >= 22) {
    addResult('pass', 'Node.js', `${process.version} (推荐版本)`, null);
  } else if (major >= MIN_NODE_MAJOR) {
    addResult('warn', 'Node.js', `${process.version} (可用，推荐 ≥22)`, '升级: https://nodejs.org/');
  } else {
    addResult('fail', 'Node.js', `${process.version} 过旧 (需要 ≥${MIN_NODE_MAJOR})`, '安装/升级: https://nodejs.org/');
  }

  // Python 3.12 pin (backend requires ==3.12.*)
  if (hasPython312()) {
    addResult('pass', 'Python 3.12', 'uv 可管理 / 系统已具备', null);
  } else {
    addResult('warn', 'Python 3.12', '未检测到；uv sync 时会自动下载 CPython 3.12（需网络）',
      '离线环境请预装 Python 3.12 或预先准备 backend/.venv');
  }

  // npm
  try {
    const npmVer = execSync('npm --version', { encoding: 'utf8', timeout: 5000, stdio: ['pipe','pipe','pipe'] }).trim();
    addResult('pass', 'npm', `v${npmVer}`, null);
  } catch {
    addResult('fail', 'npm', '未找到 npm', '安装 Node.js 后 npm 自动包含');
  }

  // Git
  try {
    const gitVer = execSync('git --version', { encoding: 'utf8', timeout: 5000, stdio: ['pipe','pipe','pipe'] }).trim();
    addResult('pass', 'Git', gitVer, null);
  } catch {
    addResult('warn', 'Git', '未找到 Git（版本管理需要）', '安装: https://git-scm.com/downloads');
  }

  // Neo4j — local install (Docker-free) or legacy docker
  if (readGraphMode() === 'local') {
    const neoHome = path.join(BACKEND_DIR, '.neo4j');
    const hasDist = fs.existsSync(neoHome) &&
      fs.readdirSync(neoHome, { withFileTypes: true })
        .some(d => d.isDirectory() && d.name.startsWith('neo4j-community-'));
    const boltPort = readGraphBoltPort();
    if (await portInUse(boltPort)) {
      addResult('pass', 'Neo4j (local)', `运行中 :${boltPort}`, null);
    } else if (hasDist) {
      addResult('warn', 'Neo4j (local)', '已安装未运行', `启动: ragctl start neo4j`);
    } else {
      addResult('warn', 'Neo4j (local)', '未安装（图谱功能可选）', `安装+启动: ragctl start neo4j（自动下载到 backend/.neo4j）`);
    }
  } else {
    try {
      const dockerVer = execSync('docker --version', { encoding: 'utf8', timeout: 5000, stdio: ['pipe','pipe','pipe'] }).trim();
      addResult('pass', 'Docker', dockerVer, null);
    } catch {
      addResult('warn', 'Docker', '未找到（graph.mode=docker 时需要）', '安装 Docker Desktop: https://docker.com 或改用 graph.mode: local');
    }
  }

  // 3. Project files
  console.log(`\n${_c(C.BOLD, '── 项目文件 ──')}\n`);

  const fileChecks = [
    ['config.yml', CONFIG_YML, '主配置文件缺失'],
    ['backend/config.yml', BACKEND_CONFIG_YML, '后端配置文件缺失'],
    ['.env', ENV_FILE, '环境变量文件缺失（运行: ragctl setup）'],
    ['backend/app/main.py', path.join(BACKEND_DIR, 'app', 'main.py'), 'backend/ 缺失（运行: ragctl setup）'],
    ['web/package.json', path.join(WEB_DIR, 'package.json'), 'web/ 缺失（运行: ragctl setup）'],
    ['kb-mcp/server.py', path.join(MCP_DIR, 'server.py'), 'kb-mcp 目录缺失'],
    ['.env.example', path.join(PROJECT_ROOT, '.env.example'), '.env.example 模板缺失'],
  ];

  for (const [label, filePath, solution] of fileChecks) {
    if (fs.existsSync(filePath)) {
      const stat = fs.statSync(filePath);
      addResult('pass', label, `${(stat.size / 1024).toFixed(1)} KB`, null);
    } else {
      addResult('fail', label, '文件不存在', solution);
    }
  }

  // 4. Dependencies
  console.log(`\n${_c(C.BOLD, '── 依赖安装状态 ──')}\n`);

  // Backend
  if (fs.existsSync(path.join(BACKEND_DIR, '.venv'))) {
    addResult('pass', 'Backend (Python)', '依赖已安装 (uv sync)', null);
  } else {
    addResult('fail', 'Backend (Python)', '依赖未安装', '运行: ragctl deps');
  }

  // Web
  if (fs.existsSync(path.join(WEB_DIR, 'node_modules'))) {
    const pkgCount = fs.readdirSync(path.join(WEB_DIR, 'node_modules')).filter(f => !f.startsWith('.')).length;
    addResult('pass', 'Web (Nuxt 3)', `${pkgCount} packages`, null);
  } else {
    addResult('fail', 'Web (Nuxt 3)', '依赖未安装', '运行: ragctl deps');
  }

  // MCP
  if (fs.existsSync(path.join(MCP_DIR, '.venv'))) {
    addResult('pass', 'MCP Server (Python)', '依赖已安装 (uv sync)', null);
  } else {
    addResult('fail', 'MCP Server (Python)', '依赖未安装', '运行: ragctl deps');
  }

  // CLI
  if (fs.existsSync(path.join(PROJECT_ROOT, 'command', 'node_modules'))) {
    addResult('pass', 'CLI (js-yaml)', '依赖已安装', null);
  } else {
    addResult('warn', 'CLI (js-yaml)', '依赖未安装', '运行: cd command && npm install');
  }

  // 5. BGE Model (project models_cache first, then HF hub cache)
  console.log(`\n${_c(C.BOLD, '── AI 模型 ──')}\n`);
  const projectModelDir = path.join(PROJECT_ROOT, 'models_cache', 'hub', 'models--BAAI--bge-m3');
  const hfModelDir = path.join(os.homedir(), '.cache', 'huggingface', 'hub', 'models--BAAI--bge-m3');
  function modelStatus(dir) {
    if (!fs.existsSync(dir)) return '未下载';
    const snapshots = path.join(dir, 'snapshots');
    if (fs.existsSync(snapshots) && fs.readdirSync(snapshots).length > 0) return '已下载';
    return '未完成';
  }
  const projectStatus = modelStatus(projectModelDir);
  const hfStatus = modelStatus(hfModelDir);
  if (projectStatus === '已下载' || hfStatus === '已下载') {
    const where = projectStatus === '已下载' ? 'project models_cache/' : 'HF hub cache';
    addResult('pass', 'BGE-M3 嵌入模型', `已缓存 (${where})`, null);
  } else {
    addResult('warn', 'BGE-M3 嵌入模型', `${projectStatus}/${hfStatus}（首次向量索引时自动下载 ~2.2GB）`, '预下载: ragctl model');
  }

  // 6. Ports (show both dev and prod) — use health probes, not bare listening
  console.log(`\n${_c(C.BOLD, '── 端口状态 ──')}\n`);

  const portProbes = [
    [8765, 'Backend API (dev)', '/api/v1/health'],
    [6789, 'Web UI (dev)', '/api/kb/catalog'],
    [8001, 'Backend API (prod)', '/api/v1/health'],
    [3000, 'Web UI (prod)', '/api/kb/catalog'],
  ];
  // Neo4j ports are config-driven (graph.bolt_port / http_port) — honor
  // custom ports instead of hard-coded 7687/7474.
  const sharedPorts = [
    [readGraphBoltPort(), 'Neo4j Bolt', null],
    [readGraphHttpPort(), 'Neo4j HTTP', null],
  ];

  for (const [port, name, healthPath] of portProbes) {
    if (await portInUse(port)) {
      const pid = findPidOnPort(port);
      let health = '';
      if (healthPath) {
        const r = await httpGet(`http://127.0.0.1:${port}${healthPath}`, 2500);
        health = r.code === 200 ? 'healthy' : (r.code ? `HTTP ${r.code}` : 'no-response');
      }
      const pidInfo = pid ? ` (PID ${pid})` : '';
      const healthInfo = health ? ` [${health}]` : '';
      // Listening but unhealthy is a warning (zombie / wrong process)
      if (health && health !== 'healthy') {
        addResult('warn', `端口 ${port} (${name})`, `占用中但未就绪${pidInfo}${healthInfo}`,
          '可能是无关进程占用端口，或服务启动失败。排查: ragctl logs backend|web / ragctl down --force');
      } else {
        addResult('pass', `端口 ${port} (${name})`, `运行中${pidInfo}${healthInfo}`, null);
      }
    } else {
      addResult('warn', `端口 ${port} (${name})`, '未使用', '对应服务未启动');
    }
  }
  for (const [port, name] of sharedPorts) {
    if (await portInUse(port)) {
      const pid = findPidOnPort(port);
      const pidInfo = pid ? ` (PID ${pid})` : '';
      addResult('pass', `端口 ${port} (${name})`, `运行中${pidInfo}`, null);
    } else {
      addResult('warn', `端口 ${port} (${name})`, '未使用', '图谱功能可选；启动: ragctl start neo4j 或 docker compose up -d neo4j');
    }
  }

  // 7. Summary
  console.log(`\n${_c(C.BOLD, '── 总结 ──')}\n`);
  const total = Object.values(results).flat().length;
  console.log(`  ✅ 通过: ${results.pass.length}   ⚠️ 警告: ${results.warn.length}   ❌ 失败: ${results.fail.length}`);

  if (results.fail.length === 0 && results.warn.length === 0) {
    console.log(`\n  ${_c(C.GREEN, _c(C.BOLD, '🎉 一切就绪！运行 ragctl up 启动服务！'))}`);
    return 0;
  }

  if (results.fail.length > 0) {
    console.log(`\n  ${_c(C.RED, _c(C.BOLD, '需要修复以下问题才能继续：'))}`);
    console.log(`  ${_c(C.YELLOW, '运行 ragctl setup 一键修复所有问题')}`);
  }

  return results.fail.length > 0 ? 1 : 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  ⭐ NEW: setup — One-click full environment setup
// ═══════════════════════════════════════════════════════════════════════

async function cmdSetup() {
  header('RAG Knowledge Platform — 一键部署');
  console.log(`  ${_c(C.GRAY, '这将自动安装所有缺失的依赖、模型和配置。')}\n`);

  // 0. Node gate (hard fail — nothing else can proceed without a modern Node)
  const major = nodeMajor();
  if (major < MIN_NODE_MAJOR) {
    err(`Node.js ${process.version} 过旧（需要 ≥${MIN_NODE_MAJOR}，推荐 22）`);
    info('请先安装/升级 Node.js: https://nodejs.org/');
    return 1;
  }
  if (major < 22) {
    warn(`Node.js ${process.version} 可用但低于推荐版本 22 — 建议升级以避免 Nuxt 边缘兼容问题`);
  }

  // 1. Install uv if missing
  if (!commandExists('uv') && !findUvDir()) {
    step('安装 uv (Python 包管理器)...');
    if (IS_WIN) {
      info('下载 uv 安装脚本...');
      const installerPath = path.join(os.tmpdir(), 'uv-install.ps1');
      try {
        await downloadFile('https://astral.sh/uv/install.ps1', installerPath);
        info('执行安装...');
        const result = await spawnAsync('powershell', [
          '-ExecutionPolicy', 'Bypass', '-File', installerPath
        ], { silent: true });
        if (result.code === 0) {
          ok('uv 安装成功！');
          // Detect actual install dir (modern uv → ~/.local/bin; legacy → ~/.cargo/bin)
          const uvDir = findUvDir() || path.join(os.homedir(), '.local', 'bin');
          process.env.PATH = `${uvDir}${path.delimiter}${process.env.PATH}`;
          // Persist user PATH safely (no setx truncation)
          if (appendUserPath(uvDir)) {
            info(`uv 已写入用户 PATH: ${uvDir}`);
          } else {
            info(`uv 已安装到: ${uvDir}（当前会话已可用；新终端如找不到请手动加 PATH）`);
          }
        } else {
          err(`uv 安装失败 (exit ${result.code})`);
          if (result.stderr) console.log(`  ${_c(C.GRAY, result.stderr.slice(0, 400))}`);
          console.log(`  ${_c(C.YELLOW, '手动安装: https://docs.astral.sh/uv/getting-started/installation/')}`);
          return 1;
        }
      } catch (e) {
        err(`uv 下载失败: ${e.message}`);
        console.log(`  ${_c(C.YELLOW, '手动安装: https://docs.astral.sh/uv/getting-started/installation/')}`);
        return 1;
      }
    } else {
      // Linux/macOS
      const result = await spawnAsync('sh', [
        '-c', 'curl -LsSf https://astral.sh/uv/install.sh | sh'
      ], { silent: true, noShell: true });
      if (result.code === 0) {
        ok('uv 安装成功！');
        const uvDir = findUvDir() || path.join(os.homedir(), '.local', 'bin');
        process.env.PATH = `${uvDir}${path.delimiter}${process.env.PATH}`;
        info(`uv 已安装到: ${uvDir}`);
        info('若新终端找不到 uv: echo \'export PATH="$HOME/.local/bin:$PATH"\' >> ~/.bashrc && source ~/.bashrc');
      } else {
        err('uv 安装失败');
        if (result.stderr) console.log(`  ${_c(C.GRAY, result.stderr.slice(0, 400))}`);
        return 1;
      }
    }
    try { fs.unlinkSync(path.join(os.tmpdir(), 'uv-install.ps1')); } catch {}
  } else {
    ensureUvOnPath();
    let uvVer = '';
    try { uvVer = execSync('uv --version', { encoding: 'utf8', timeout: 5000, stdio: ['pipe','pipe','pipe'] }).trim(); } catch {}
    ok(`uv 已安装: ${uvVer}`);
  }

  // Make sure subsequent `uv sync` / `uv python` can resolve the binary.
  if (!ensureUvOnPath()) {
    err('uv 安装后仍无法在 PATH 中找到 — 请重开终端后重试 ragctl setup');
    return 1;
  }

  // 1b. Ensure CPython 3.12 is available for the backend pin (==3.12.*)
  step('确保 Python 3.12 可用（backend 硬性要求）...');
  try {
    const pyResult = await spawnAsync('uv', ['python', 'install', REQUIRED_PYTHON], { silent: true });
    if (pyResult.code === 0) ok(`Python ${REQUIRED_PYTHON} 已就绪（uv 管理）`);
    else warn(`uv python install ${REQUIRED_PYTHON} 返回 ${pyResult.code} — uv sync 时将重试`);
  } catch (e) {
    warn(`无法预装 Python ${REQUIRED_PYTHON}: ${e.message}`);
  }

  // 2. Verify project integrity (backend & web are part of the repo)
  step('验证项目完整性...');
  if (fs.existsSync(path.join(BACKEND_DIR, 'app', 'main.py')) && fs.existsSync(path.join(WEB_DIR, 'package.json'))) {
    ok('项目完整性验证通过');
  } else {
    err('项目文件不完整 — backend/ 或 web/ 缺失');
    info('请重新克隆仓库: git clone https://github.com/kingdol666/rag-knowledge.git');
    return 1;
  }

  // 3. .env
  step('配置环境变量...');
  if (!fs.existsSync(ENV_FILE)) {
    const examplePath = path.join(PROJECT_ROOT, '.env.example');
    if (fs.existsSync(examplePath)) {
      fs.copyFileSync(examplePath, ENV_FILE);
      ok('.env 已从 .env.example 创建');
    } else {
      writeEnv({ APP_MODE: 'dev', PYTHONUTF8: '1', PYTHONUNBUFFERED: '1' });
      ok('.env 已创建（默认值）');
    }
  } else {
    ok('.env 已存在');
  }

  // Ensure required storage dirs exist (fresh clone has none — .gitignore hides them)
  step('创建运行时目录...');
  for (const rel of [
    'storage/tree-file-system',
    'chroma_db',
    'models_cache',
    'backend/logs',
    'web/logs',
    '.run',
  ]) {
    const abs = path.join(PROJECT_ROOT, rel);
    if (!fs.existsSync(abs)) {
      fs.mkdirSync(abs, { recursive: true });
      info(`创建 ${rel}/`);
    }
  }
  ok('运行时目录就绪');

  // 4. Install dependencies with progress
  const depsCode = await cmdDeps();
  if (depsCode !== 0) {
    err('依赖安装失败 — 修复后重跑 ragctl setup / ragctl deps');
    return depsCode;
  }

  // 5. BGE Model (best-effort — network may be restricted)
  await cmdModel();

  // 5b. MinerU VLM model — pre-download so first parse is fast
  await cmdMineruModel();

  // 5c. Neo4j (local, Docker-free) — install distribution + JRE and start
  if (readGraphMode() === 'local') {
    console.log(`\n${_c(C.BOLD, '── Neo4j (local, Docker-free) ──')}\n`);
    await startNeo4j();
  }

  // 6. Optional: global ragctl registration (best-effort)
  try { await cmdInstall(); } catch {}

  // 7. Final check
  console.log();
  const checkCode = await cmdCheck();
  if (checkCode === 0) {
    console.log(`\n  ${_c(C.GREEN, _c(C.BOLD, '下一步: ragctl up'))}`);
  } else {
    console.log(`\n  ${_c(C.YELLOW, '环境仍有待修复项 — 见上方 check 输出')}`);
  }
  return checkCode;
}

// ═══════════════════════════════════════════════════════════════════════
//  ⭐ NEW: deps — Install all dependencies with real-time progress
// ═══════════════════════════════════════════════════════════════════════

async function cmdDeps() {
  step('安装所有依赖（实时进度）...');

  if (!ensureUvOnPath()) {
    err('uv 未找到 — 请先运行 ragctl setup 安装 uv');
    return 1;
  }
  const uvBin = findUvBin();

  // CLI deps
  const cliNodeModules = path.join(PROJECT_ROOT, 'command', 'node_modules');
  if (!fs.existsSync(cliNodeModules)) {
    info('安装 CLI 依赖 (js-yaml)...');
    const r = await spawnAsync('npm', ['install'], { cwd: path.join(PROJECT_ROOT, 'command'), silent: true });
    if (r.code === 0) ok('CLI 依赖安装完成');
    else { warn(`CLI 依赖安装警告 (exit ${r.code})`); }
  } else {
    ok('CLI 依赖已安装');
  }

  // Backend (uv sync with real-time output). Pin Python 3.12 explicitly so a
  // machine whose default python is 3.11/3.13 doesn't pick the wrong interpreter.
  info('安装 Backend (Python) 依赖...');
  console.log(`  ${_c(C.GRAY, '── uv sync backend (python ' + REQUIRED_PYTHON + ') ──')}`);
  // Prefer `uv sync --python 3.12`; fall back to plain sync if flag unsupported.
  let beResult = await spawnAsync(uvBin, ['sync', '--python', REQUIRED_PYTHON], { cwd: BACKEND_DIR, noShell: true });
  if (beResult.code !== 0) {
    warn(`uv sync --python ${REQUIRED_PYTHON} 失败，回退到默认 uv sync…`);
    beResult = await spawnAsync(uvBin, ['sync'], { cwd: BACKEND_DIR, noShell: true });
  }
  if (beResult.code === 0) ok('Backend 依赖安装完成');
  else {
    err('Backend 依赖安装失败');
    info('常见原因: 网络/代理拦截 PyTorch 索引、磁盘不足、无 Python 3.12');
    info('排查: cd backend && uv sync --python 3.12');
    return 1;
  }

  // Web (npm install with real-time output)
  if (!fs.existsSync(path.join(WEB_DIR, 'node_modules'))) {
    info('安装 Web (Nuxt 3) 依赖...');
    console.log(`  ${_c(C.GRAY, '── npm install web ──')}`);
    const webResult = await spawnAsync('npm', ['install'], { cwd: WEB_DIR });
    if (webResult.code === 0) ok('Web 依赖安装完成');
    else { err('Web 依赖安装失败'); return 1; }
  } else {
    ok('Web 依赖已安装（增量: npm install）');
    console.log(`  ${_c(C.GRAY, '── npm install web (incremental) ──')}`);
    const webInc = await spawnAsync('npm', ['install'], { cwd: WEB_DIR });
    if (webInc.code !== 0) warn(`Web 增量安装返回 ${webInc.code}（已有 node_modules，可忽略）`);
  }

  // MCP
  info('安装 MCP Server 依赖...');
  console.log(`  ${_c(C.GRAY, '── uv sync kb-mcp ──')}`);
  const mcpResult = await spawnAsync(uvBin, ['sync'], { cwd: MCP_DIR, noShell: true });
  if (mcpResult.code === 0) ok('MCP 依赖安装完成');
  else { err('MCP 依赖安装失败'); return 1; }

  console.log();
  ok(_c(C.BOLD, '所有依赖安装完成！'));
  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  ⭐ NEW: model — Pre-download BGE-M3 embedding model
// ═══════════════════════════════════════════════════════════════════════

async function cmdModel(args = []) {
  // --source modelscope|hf-mirror|huggingface overrides config.yml embedding.model_source
  const sourceIdx = args.indexOf('--source');
  const sourceOverride = sourceIdx >= 0 && args[sourceIdx + 1]
    ? args[sourceIdx + 1] : null;
  const sourceLabel = sourceOverride
    ? sourceOverride
    : 'config.yml embedding.model_source (默认 modelscope)';
  step(`BGE-M3 嵌入模型下载 (~2.2 GB) [源: ${sourceLabel}]...`);

  // Build download_model.py args
  const dlArgs = [];
  if (sourceOverride) {
    dlArgs.push('--source', sourceOverride);
  }

  // 1. Project-level models_cache (preferred — shared with backend download_model.py)
  const projectCache = path.join(PROJECT_ROOT, 'models_cache', 'hub', 'models--BAAI--bge-m3');
  const hfCache = path.join(os.homedir(), '.cache', 'huggingface', 'hub', 'models--BAAI--bge-m3');
  function hasSnapshots(dir) {
    try {
      const snapshots = path.join(dir, 'snapshots');
      return fs.existsSync(snapshots) && fs.readdirSync(snapshots).length > 0;
    } catch { return false; }
  }
  if (hasSnapshots(projectCache) || hasSnapshots(hfCache)) {
    ok('BGE-M3 模型已缓存（跳过下载）');
    return 0;
  }

  // 2. Quick check: is model already loadable via backend venv?
  const backendVenvPy = path.join(BACKEND_DIR, '.venv', IS_WIN ? 'Scripts' : 'bin', IS_WIN ? 'python.exe' : 'python');
  if (fs.existsSync(backendVenvPy)) {
    try {
      // Prefer the project's own downloader (handles modelscope / hf-mirror / proxy quirks)
      const downloader = path.join(BACKEND_DIR, 'app', 'utils', 'download_model.py');
      if (fs.existsSync(downloader)) {
        info('通过 backend download_model.py 下载（多源 fallback：modelscope → hf-mirror → huggingface）...');
        console.log(`  ${_c(C.GRAY, '── 下载中，请耐心等待（约 2.2GB）──')}`);
        const result = await spawnAsync(backendVenvPy, [downloader, ...dlArgs], {
          cwd: BACKEND_DIR,
          env: {
            ...process.env,
            HF_ENDPOINT: process.env.HF_ENDPOINT || 'https://hf-mirror.com',
            // Avoid corporate/local HTTPS_PROXY hijacking the mirror
            HTTPS_PROXY: '', HTTP_PROXY: '', https_proxy: '', http_proxy: '',
          },
        });
        if (result.code === 0 && (hasSnapshots(projectCache) || hasSnapshots(hfCache))) {
          ok('BGE-M3 模型下载完成！');
          return 0;
        }
      }

      // Fallback: sentence-transformers direct load
      info('回退：通过 sentence-transformers 触发下载...');
      const script = `
import os
os.environ.setdefault("HF_ENDPOINT", os.environ.get("HF_ENDPOINT", "https://hf-mirror.com"))
print("Loading sentence_transformers...")
from sentence_transformers import SentenceTransformer
print("Downloading BAAI/bge-m3 model to local cache...")
model = SentenceTransformer("BAAI/bge-m3")
print("Model loaded. Dimension:", model.get_sentence_embedding_dimension())
`;
      const scriptPath = path.join(os.tmpdir(), 'ragctl_bge_download.py');
      fs.writeFileSync(scriptPath, script, 'utf8');
      const result = await spawnAsync(backendVenvPy, [scriptPath], {
        cwd: BACKEND_DIR,
        env: {
          ...process.env,
          HF_ENDPOINT: process.env.HF_ENDPOINT || 'https://hf-mirror.com',
          HTTPS_PROXY: '', HTTP_PROXY: '', https_proxy: '', http_proxy: '',
        },
      });
      try { fs.unlinkSync(scriptPath); } catch {}
      if (result.code === 0) {
        ok('BGE-M3 模型下载完成！');
        return 0;
      }
      warn('模型下载未完全成功，首次索引时系统会自动重试');
    } catch (e) {
      warn(`模型下载异常: ${e.message}`);
    }
  } else {
    warn('Backend venv 未就绪，请先运行 ragctl deps 再下载模型');
  }

  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  ⭐ mineru-model — Pre-download MinerU VLM model for PDF parsing
// ═══════════════════════════════════════════════════════════════════════

async function cmdMineruModel(args = []) {
  step('MinerU Pipeline + VLM 模型预下载 (OCR/PDF解析引擎，~5-7 GB)...');

  const backendVenvPy = path.join(BACKEND_DIR, '.venv', IS_WIN ? 'Scripts' : 'bin', IS_WIN ? 'python.exe' : 'python');
  if (!fs.existsSync(backendVenvPy)) {
    warn('Backend venv 未就绪 — 请先运行 ragctl deps');
    return 1;
  }

  const backendCfg = readYaml(BACKEND_CONFIG_YML);
  const mineruCfg = (backendCfg && backendCfg.mineru) || {};
  const modelSource = mineruCfg.model_source || 'modelscope';
  const sourceLabels = {
    modelscope: 'ModelScope (modelscope.cn — 中国区推荐，阿里云 CDN)',
    huggingface: 'HuggingFace (huggingface.co — 海外)',
  };
  info('MinerU 模型源: ' + (sourceLabels[modelSource] || modelSource));

  // ⭐ Remove stale MinerU config so models-download does an actual download
  //    (mineru-models-download checks if models-dir is configured and skips
  //    the download if it is — stale pointer = 25K of config, no model file).
  const mineruConfigPath = path.join(os.homedir(), 'mineru.json');
  if (fs.existsSync(mineruConfigPath)) {
    info('删除旧 mineru.json 配置以确保强制下载...');
    try { fs.unlinkSync(mineruConfigPath); } catch {}
  }

  info('通过 mineru-models-download 下载并配置（自动更新 models-dir）...');
  console.log('  ' + _c(C.GRAY, '── mineru-models-download --model_type all --source ' + modelSource + ' ──'));
  console.log('  ' + _c(C.GRAY, '预计 ~5-7 GB（首次 5-15 分钟）'));

  const result = await spawnAsync(backendVenvPy, [
    '-m', 'mineru.cli.models_download',
    '--model_type', 'all',
    '--source', modelSource,
  ], {
    cwd: BACKEND_DIR,
    env: {
      ...process.env,
      MINERU_MODEL_SOURCE: modelSource,
      HTTPS_PROXY: '', HTTP_PROXY: '', https_proxy: '', http_proxy: '',
    },
  });

  if (result.code === 0) {
    ok('MinerU 所有模型已下载并配置完成');
  } else {
    warn('MinerU 模型下载未完全完成（非致命 — 首次 PDF 解析时会自动下载）');
  }
  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMANDS: start / stop / status / restart
// ═══════════════════════════════════════════════════════════════════════

function getServicePorts(modeOverride) {
  const cfg = readYaml(CONFIG_YML);
  const env = readEnv(ENV_FILE);
  const envMode = env.APP_MODE || 'dev';
  const mode = modeOverride || envMode;
  const server = cfg.server || {};
  const modeSection = server[mode] || {};
  // When user EXPLICITLY forces a DIFFERENT mode than .env pins (e.g. `--appmode prod`
  // while .env has APP_MODE=dev), use config.yml ports for that mode so .env's
  // port pins don't silently override the runtime mode choice. Note: parseFlags
  // always defaults flags.appmode to getAppMode() (reads .env APP_MODE), so when
  // the user doesn't pass --appmode, modeOverride === envMode → .env ports win.
  if (modeOverride && modeOverride !== envMode) {
    return {
      backend: parseInt(modeSection.backend_port || '8765'),
      web: parseInt(modeSection.frontend_port || '6789'),
      mode,
    };
  }
  // Default (no explicit mode switch): .env is the single source of truth
  // (env BACKEND_PORT/WEB_PORT win over config.yml defaults).
  return {
    backend: parseInt(env.BACKEND_PORT || modeSection.backend_port || '8765'),
    web: parseInt(env.WEB_PORT || env.FRONTEND_PORT || modeSection.frontend_port || '6789'),
    mode,
  };
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

function findPythonProcesses(keyword) {
  const name = IS_WIN ? 'python.exe' : 'python';
  const procs = [];
  try {
    if (IS_WIN) {
      const output = execSync(`wmic process where "name like '%python%'" get processid,commandline /format:csv`, { encoding: 'utf8', timeout: 10000, stdio: 'pipe', windowsHide: true });
      for (const line of output.split('\n')) {
        if (keyword && !line.toLowerCase().includes(keyword.toLowerCase())) continue;
        const match = line.match(/(\d+)/);
        if (match) procs.push({ pid: parseInt(match[1]), cmd: line });
      }
    } else {
      const output = execSync('ps aux', { encoding: 'utf8', timeout: 10000, stdio: ['pipe','pipe','pipe'] });
      for (const line of output.split('\n')) {
        if (line.includes(keyword)) {
          const parts = line.trim().split(/\s+/);
          if (parts.length >= 2) procs.push({ pid: parseInt(parts[1]), cmd: parts.slice(10).join(' ') });
        }
      }
    }
  } catch {}
  return procs;
}

function spawnInTerminal(title, commandLine, opts = {}) {
  // Kept for `ragctl console` (explicit "I want a live terminal") — NOT used by
  // normal `up`/`start`. Silent detached launch is the default for all services
  // so no terminal windows ever appear without the user asking for one.
  const env = { ...process.env, ...(opts.env || {}) };
  const cwd = opts.cwd || PROJECT_ROOT;

  if (IS_WIN) {
    spawn('cmd', ['/c', 'start', `"${title}"`, 'cmd', '/k', commandLine], {
      cwd, env, shell: false, windowsHide: false,
    }).unref();
    return true;
  }

  if (process.platform === 'darwin') {
    const esc = commandLine.replace(/"/g, '\\"');
    spawn('osascript', ['-e', `tell app "Terminal" to do script "cd \\"${cwd}\\" && ${esc}"`], {
      cwd, env, stdio: 'ignore', detached: true
    }).unref();
    return true;
  }

  const runners = [
    ['gnome-terminal', (t, c) => ['--title', t, '--', 'bash', '-lc', `${c}; exec bash`]],
    ['xterm', (t, c) => ['-T', t, '-e', 'bash', '-lc', c]],
  ];
  for (const [bin, argFn] of runners) {
    if (commandExists(bin)) {
      spawn(bin, argFn(title, commandLine), { cwd, env, stdio: 'ignore', detached: true }).unref();
      return true;
    }
  }
  return false;
}

/**
 * Silent service launcher — used for EVERY service in both dev and prod.
 *
 * No terminal window is ever opened. stdout+stderr are redirected to the same
 * log file Tauri's desktop log viewer tails, so logs flow into:
 *   • on-disk log file        →  {backend,web}/logs/desktop-stdout.log
 *   • Tauri desktop log UI    →  watch_log() reads those exact paths
 *   • `ragctl logs <svc>`     →  reads/tails those exact paths
 *
 * The binary is spawned DIRECTLY (no `shell: true`). Spawning `uv`/`node`
 * through a cmd.exe wrapper breaks fd inheritance on Windows and the log file
 * stays empty even though the service runs; spawning the binary directly
 * (matching Python's subprocess.Popen) makes the stdio fd inherit correctly.
 * `detached: true` + `.unref()` → survives ragctl exit; `windowsHide: true`
 * → no console window. `PYTHONUNBUFFERED` forces Python to flush in real time.
 */
function spawnService({ title, cwd, command, args, env, serviceName }) {
  const fullEnv = {
    ...process.env,
    PYTHONUNBUFFERED: '1',
    PYTHONUTF8: '1',
    ...(env || {}),
  };
  const logPath = getLogPath(serviceName);
  if (!logPath) throw new Error(`未知服务日志路径: ${serviceName}`);
  fs.mkdirSync(path.dirname(logPath), { recursive: true });

  // Resolve the actual binary so we can spawn WITHOUT a shell:
  //   uv   → full path via findUvDir (modern uv in ~/.local/bin)
  //   node → the very node.exe running this CLI (process.execPath)
  //   other→ append .exe on Windows (CreateProcess doesn't do PATHEXT)
  let bin = command;
  if (command === 'uv') bin = findUvBin();
  else if (command === 'node') bin = process.execPath;
  else if (IS_WIN && !path.extname(command)) bin = command + '.exe';

  // One fd shared by stdout+stderr — both streams land in the same file.
  const fd = fs.openSync(logPath, 'w');   // truncate on start (matches Tauri)

  // Platform-specific spawn: silence is mandatory, never flash a terminal.
  // ─
  // Two strategies, chosen per service:
  //
  //  • Backend (Python/uv → MinerU grandchildren):
  //      windowsHide:true ONLY → CREATE_NO_WINDOW → a *hidden* console that
  //      all grandchildren inherit, so no process ever AllocConsole()s a
  //      visible window. MUST NOT add detached:true here — libuv's
  //      DETACHED_PROCESS makes Windows IGNORE CREATE_NO_WINDOW (MSDN), and
  //      detached-then-grandchild was the original "backend pops a terminal"
  //      bug.
  //
  //  • Web (node → Nuxt → Vite):
  //      detached:true + windowsHide:true. Nuxt/Vite's dev server PROBES the
  //      console during bootstrap and HANGS forever under a hidden console
  //      (CREATE_NO_WINDOW) — it only completes startup under DETACHED_PROCESS
  //      (no console at all). Detached does NOT pop a window here because the
  //      web child tree (node/nuxt/vite) never calls AllocConsole.
  //
  //  Both use stdio ['pipe', fd, fd] with stdin closed immediately (EOF),
  //  which is the most compatible stdin shape across runtimes.
  //
  // POSIX: detached:true → start_new_session (child survives terminal close).
  const useDetached = !IS_WIN || serviceName === 'web';
  const spawnOpts = {
    cwd,
    env: fullEnv,
    stdio: ['pipe', fd, fd],
    windowsHide: true,
    shell: false,
  };
  if (useDetached) {
    spawnOpts.detached = true;
  }
  const child = spawn(bin, args, spawnOpts);
  // Close stdin immediately so the child sees EOF (prevents Nuxt/Vite hang).
  try { child.stdin.end(); } catch {}
  child.unref();
  return { pid: child.pid, logPath, bin };
}

function httpGet(url, timeout = 5000) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout }, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => resolve({ code: res.statusCode, body }));
    });
    req.on('error', e => resolve({ code: 0, body: e.message }));
    req.on('timeout', () => { req.destroy(); resolve({ code: 0, body: 'timeout' }); });
  });
}

async function startBackend(mode, portOverride = null, opts = {}) {
  const { backend: defaultPort } = getServicePorts(mode);
  const port = portOverride || defaultPort;
  const timeoutSec = opts.timeoutSec || 60;

  if (await portInUse(port)) {
    // Verify it's actually OUR healthy backend, not a zombie / unrelated process.
    const health = await httpGet(`http://127.0.0.1:${port}/api/v1/health`, 2500);
    if (health.code === 200 && (health.body || '').includes('healthy')) {
      warn(`Backend 已在端口 ${port} 运行 (mode=${mode}, healthy)`);
      return { ok: true, already: true, port };
    }
    err(`端口 ${port} 已被占用，但 /api/v1/health 未返回 healthy`);
    info(`排查: netstat/lsof 查 PID，或 ragctl down --appmode ${mode} --force`);
    info(`日志: ragctl logs backend`);
    return { ok: false, port, reason: 'port-occupied-unhealthy' };
  }

  info(`启动 Backend (端口 ${port}, mode=${mode}, 静默)...`);
  let spawned;
  try {
    spawned = spawnService({
      title: `RAG-Backend (${mode})`,
      cwd: BACKEND_DIR,
      command: 'uv',
      args: ['run', 'python', 'main.py'],
      env: { APP_MODE: mode, BACKEND_PORT: String(port) },
      serviceName: 'backend',
    });
  } catch (e) {
    err(`Backend 启动失败: ${e.message}`);
    return { ok: false, port, reason: 'spawn-failed' };
  }
  info(`Backend pid=${spawned.pid} · 日志: ${getLogPath('backend')}`);
  writePid('backend', mode, spawned.pid, port);

  // Wait for REAL readiness (health endpoint), not just bind.
  const probe = await waitForHttpOk(
    `http://127.0.0.1:${port}/api/v1/health`,
    { timeoutSec, intervalMs: 1000, expectBodyIncludes: 'healthy' },
  );
  if (probe.ok) {
    ok(`Backend 已就绪 (端口 ${port}) · ragctl logs backend 查看日志`);
    return { ok: true, port, pid: spawned.pid };
  }
  warn(`Backend 启动超时 (端口 ${port}, ${timeoutSec}s) — 排查: ragctl logs backend`);
  // Dump last few log lines for quick diagnosis
  try {
    const logPath = getLogPath('backend');
    if (fs.existsSync(logPath)) {
      const lines = fs.readFileSync(logPath, 'utf8').split('\n').slice(-15).join('\n');
      if (lines.trim()) console.log(`  ${_c(C.GRAY, lines)}`);
    }
  } catch {}
  return { ok: false, port, pid: spawned.pid, reason: 'timeout' };
}

async function stopBackend(port, mode = null) {
  let stopped = false;
  // Prefer PID file (precise) then fall back to port scan
  if (mode) {
    const rec = readPid('backend', mode);
    if (rec && rec.pid && isPidAlive(rec.pid)) {
      if (killPid(rec.pid, false)) {
        // Give graceful window then force
        await sleep(1500);
        if (isPidAlive(rec.pid)) killPid(rec.pid, true);
        stopped = true;
      }
    }
    clearPid('backend', mode);
  }
  const pid = findPidOnPort(port);
  if (pid) {
    // Graceful then force
    killPid(pid, false);
    await sleep(1500);
    if (isPidAlive(pid)) killPid(pid, true);
    stopped = true;
  }
  if (stopped) ok('Backend 已停止'); else warn(`未找到 Backend 进程 (端口 ${port})`);
  return stopped;
}

async function startWeb(mode, portOverride = null, opts = {}) {
  const { web: defaultPort, backend } = getServicePorts(mode);
  const port = portOverride || defaultPort;
  const timeoutSec = opts.timeoutSec || 45;

  if (await portInUse(port)) {
    const health = await httpGet(`http://127.0.0.1:${port}/api/kb/catalog`, 2500);
    if (health.code === 200) {
      warn(`Web 已在端口 ${port} 运行 (mode=${mode}, healthy)`);
      return { ok: true, already: true, port };
    }
    err(`端口 ${port} 已被占用，但 Web 健康检查未通过`);
    info(`可能是无关进程（常见: 其他 dev server / Docker 映射）。换端口: --port-web <N>`);
    return { ok: false, port, reason: 'port-occupied-unhealthy' };
  }

  info(`启动 Web 前端 (端口 ${port}, mode=${mode}, 静默)...`);
  let spawned;
  try {
    spawned = spawnService({
      title: `RAG-Web (${mode})`,
      cwd: WEB_DIR,
      command: 'node',
      args: ['start.mjs'],
      env: {
        APP_MODE: mode,
        WEB_PORT: String(port),
        FRONTEND_PORT: String(port),
        BACKEND_PORT: String(backend),
        BACKEND_URL: `http://localhost:${backend}`,
      },
      serviceName: 'web',
    });
  } catch (e) {
    err(`Web 启动失败: ${e.message}`);
    return { ok: false, port, reason: 'spawn-failed' };
  }
  info(`Web pid=${spawned.pid} · 日志: ${getLogPath('web')}`);
  writePid('web', mode, spawned.pid, port);

  // Prefer /api/kb/catalog (real Nuxt server route). Fall back to any 200 on /
  // for partial readiness while Nitro is still compiling in dev.
  let probe = await waitForHttpOk(
    `http://127.0.0.1:${port}/api/kb/catalog`,
    { timeoutSec, intervalMs: 1000 },
  );
  if (!probe.ok) {
    // Last chance: root responds at all
    probe = await waitForHttpOk(
      `http://127.0.0.1:${port}/`,
      { timeoutSec: 5, intervalMs: 1000 },
    );
  }
  if (probe.ok) {
    ok(`Web 已就绪 (端口 ${port}) · ragctl logs web 查看日志`);
    return { ok: true, port, pid: spawned.pid };
  }
  warn(`Web 启动超时 (端口 ${port}, ${timeoutSec}s) — 排查: ragctl logs web`);
  try {
    const logPath = getLogPath('web');
    if (fs.existsSync(logPath)) {
      const lines = fs.readFileSync(logPath, 'utf8').split('\n').slice(-15).join('\n');
      if (lines.trim()) console.log(`  ${_c(C.GRAY, lines)}`);
    }
  } catch {}
  return { ok: false, port, pid: spawned.pid, reason: 'timeout' };
}

async function stopWeb(port, mode = null) {
  let stopped = false;
  if (mode) {
    const rec = readPid('web', mode);
    if (rec && rec.pid && isPidAlive(rec.pid)) {
      killPid(rec.pid, false);
      await sleep(1500);
      if (isPidAlive(rec.pid)) killPid(rec.pid, true);
      stopped = true;
    }
    clearPid('web', mode);
  }
  const pid = findPidOnPort(port);
  if (pid) {
    killPid(pid, false);
    await sleep(1500);
    if (isPidAlive(pid)) killPid(pid, true);
    stopped = true;
  }
  if (stopped) ok('Web 已停止'); else warn('未找到 Web 进程');
  return stopped;
}

// ── Neo4j: local (Docker-free, backend/.neo4j) or docker (legacy) ────────
function readGraphMode() {
  try {
    const raw = fs.readFileSync(path.join(PROJECT_ROOT, 'config.yml'), 'utf-8');
    const m = raw.match(/^graph:\s*$([\s\S]*?)^[a-z_]+:/m);
    const block = m ? m[1] : '';
    const mode = block.match(/^\s*mode:\s*["']?([a-z]+)/m);
    if (mode) return mode[1] === 'docker' ? 'docker' : 'local';
    const uri = raw.match(/graph:\s*[\s\S]*?uri:\s*["']bolt:\/\/[^:]+:(\d+)/);
    return 'local'; // default
  } catch { return 'local'; }
}

function readGraphBoltPort() {
  try {
    const raw = fs.readFileSync(path.join(PROJECT_ROOT, 'config.yml'), 'utf-8');
    const p = raw.match(/bolt_port:\s*(\d+)/);
    return p ? parseInt(p[1], 10) : 7687;
  } catch { return 7687; }
}

function readGraphHttpPort() {
  try {
    const raw = fs.readFileSync(path.join(PROJECT_ROOT, 'config.yml'), 'utf-8');
    const p = raw.match(/http_port:\s*(\d+)/);
    return p ? parseInt(p[1], 10) : 7474;
  } catch { return 7474; }
}

function localNeo4jPython() {
  const venvPy = path.join(BACKEND_DIR, '.venv', IS_WIN ? 'Scripts' : 'bin', IS_WIN ? 'python.exe' : 'python');
  return fs.existsSync(venvPy) ? venvPy : 'python';
}

async function startNeo4j() {
  const mode = readGraphMode();
  const boltPort = readGraphBoltPort();

  if (mode === 'local') {
    // ── Local mode: spawn the Neo4j manager from the shared Python env ──
    if (await portInUse(boltPort)) {
      ok(`Neo4j (local) 已在运行 (bolt :${boltPort})`);
      return { ok: true };
    }
    const py = localNeo4jPython();
    const cli = path.join(BACKEND_DIR, 'app', 'utils', 'neo4j_cli.py');
    info(`Neo4j (local) 启动中 (bolt :${boltPort}, home backend/.neo4j) ...`);
    const r = await spawnAsync(py, [cli, 'start'], { cwd: PROJECT_ROOT, silent: true });
    if (r.code !== 0) {
      warn(`Neo4j (local) 启动失败 (exit ${r.code})`);
      if (r.stderr) console.log(`  ${_c(C.GRAY, r.stderr.slice(0, 400))}`);
      return { ok: false, reason: 'local-start-failed' };
    }
    for (let i = 0; i < 60; i++) {
      if (await portInUse(boltPort)) { ok(`Neo4j (local) 已启动 (bolt :${boltPort})`); return { ok: true }; }
      await sleep(1000);
    }
    warn('Neo4j (local) 已拉起但 bolt 端口尚未就绪（后台继续启动中）');
    return { ok: true, pending: true };
  }

  // ── Docker mode (legacy) ──
  const composeFile = path.join(PROJECT_ROOT, 'docker-compose.yml');
  if (!fs.existsSync(composeFile)) { warn('docker-compose.yml 未找到'); return { ok: false, reason: 'no-compose' }; }
  if (!commandExists('docker')) {
    warn('Docker 未找到 — 跳过 Neo4j（图谱功能不可用，其他功能不受影响）');
    return { ok: false, reason: 'no-docker' };
  }
  // Detect daemon not running (docker binary present but engine down)
  try {
    execSync('docker info', { stdio: 'ignore', timeout: 8000, windowsHide: true });
  } catch {
    warn('Docker 引擎未运行 — 跳过 Neo4j（请启动 Docker Desktop / dockerd）');
    return { ok: false, reason: 'docker-daemon-down' };
  }
  try {
    const r = await spawnAsync('docker', ['compose', 'up', '-d', 'neo4j'], { cwd: PROJECT_ROOT, silent: true });
    if (r.code !== 0) {
      warn(`Neo4j 启动失败 (exit ${r.code})`);
      if (r.stderr) console.log(`  ${_c(C.GRAY, r.stderr.slice(0, 300))}`);
      return { ok: false, reason: 'compose-failed' };
    }
    // Wait for bolt port
    for (let i = 0; i < 40; i++) {
      if (await portInUse(boltPort)) { ok('Neo4j 已启动'); return { ok: true }; }
      await sleep(1000);
    }
    warn('Neo4j 已拉起但 bolt 端口尚未就绪（后台继续启动中）');
    return { ok: true, pending: true };
  } catch (e) {
    warn(`Docker 调用异常 — 跳过 Neo4j: ${e.message}`);
    return { ok: false, reason: 'exception' };
  }
}

async function stopNeo4j() {
  const mode = readGraphMode();
  if (mode === 'local') {
    // Local mode: kill whatever listens on the bolt port (process tree).
    const boltPort = readGraphBoltPort();
    const pid = findPidOnPort(boltPort);
    if (pid) {
      try {
        killPid(parseInt(pid, 10), true);
        await sleep(2000);
      } catch (e) { /* ignore */ }
    }
    if (!(await portInUse(boltPort))) { ok('Neo4j (local) 已停止'); return true; }
    warn('Neo4j (local) 端口仍占用，请手动结束进程');
    return false;
  }
  if (!commandExists('docker')) return false;
  try {
    await spawnAsync('docker', ['compose', 'down'], { cwd: PROJECT_ROOT, silent: true });
    ok('Neo4j 已停止');
    return true;
  } catch { return false; }
}

// Parse `--mode dev|prod` from arg list, falling back to .env APP_MODE.
// ── Unified Flag Parser ─────────────────────────────────────────────────
// Parses --flag value and --flag (boolean) args into a structured object.
// Supports: --appmode dev|prod, --port-backend N, --port-web N, --host HOST,
//           --no-neo4j, --no-backend, --no-web, --only SVC, --force, --timeout N,
//           --skip-check, --lines N, --tail
function parseFlags(args) {
  const flags = {
    appmode: null,       // --appmode dev|prod
    portBackend: null,   // --port-backend N
    portWeb: null,       // --port-web N
    host: null,          // --host HOST
    noNeo4j: false,      // --no-neo4j
    noBackend: false,    // --no-backend
    noWeb: false,        // --no-web
    only: null,          // --only SERVICE
    force: false,        // --force
    timeout: null,       // --timeout N
    skipCheck: false,    // --skip-check
    lines: 80,           // --lines N
    tail: false,         // --tail / -f
    positional: [],      // non-flag args (service name, etc.)
  };

  const flagMap = {
    '--appmode':     'appmode',
    '--mode':        'appmode',     // --mode is alias for --appmode
    '-m':            'appmode',     // -m dev|prod shortcut
    '--port-backend':'portBackend',
    '--backend-port':'portBackend', // alias
    '--port-web':    'portWeb',
    '--web-port':    'portWeb',     // alias
    '--host':        'host',
    '--no-neo4j':    'noNeo4j',
    '--no-backend':  'noBackend',
    '--no-web':      'noWeb',
    '--only':        'only',
    '--force':       'force',
    '-f':            'force',       // -f shortcut
    '--timeout':     'timeout',
    '--skip-check':  'skipCheck',
    '--lines':       'lines',
    '-n':            'lines',       // -n N shortcut
    '--tail':        'tail',
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    const key = flagMap[arg];
    if (key === undefined) {
      // Not a recognized flag — collect as positional
      if (!arg.startsWith('-')) flags.positional.push(arg);
      continue;
    }
    // Boolean flags (no value argument)
    if (['noNeo4j', 'noBackend', 'noWeb', 'force', 'skipCheck', 'tail'].includes(key)) {
      flags[key] = true;
      continue;
    }
    // Value flags
    const val = args[i + 1];
    if (val && !val.startsWith('-')) {
      if (key === 'lines' || key === 'timeout' || key === 'portBackend' || key === 'portWeb') {
        flags[key] = parseInt(val) || flags[key];
      } else {
        flags[key] = val;
      }
      i++; // consume value
    }
  }

  // Resolve appmode: flag > .env > 'dev'
  if (!flags.appmode) flags.appmode = getAppMode();
  // Validate
  if (!['dev', 'prod'].includes(flags.appmode)) {
    flags.appmode = 'dev';
  }

  return flags;
}

// Resolve the first positional arg as service name.
function getService(flags) {
  return flags.positional[0] || null;
}

// ── Per-service start/stop/restart ──────────────────────────────────────
async function cmdStart(args) {
  const flags = parseFlags(args);
  const svc = getService(flags) || flags.only || 'all';
  const mode = flags.appmode;
  const ports = getServicePorts(mode);

  header(`启动服务 (mode=${mode}): ${svc}`);

  // Pre-flight: fail fast on fresh clones
  if (!flags.skipCheck) {
    const problems = preflightReady();
    if (problems.length) {
      err('环境未就绪，拒绝启动：');
      for (const p of problems) console.log(`  ${_c(C.YELLOW, '• ' + p)}`);
      info('一键修复: ragctl setup');
      return 1;
    }
  }

  // Handle --port-backend / --port-web overrides
  if (flags.portBackend) ports.backend = flags.portBackend;
  if (flags.portWeb) ports.web = flags.portWeb;

  const composeFile = path.join(PROJECT_ROOT, 'docker-compose.yml');
  const timeoutSec = flags.timeout || null;
  let failed = false;

  async function doStartBackend() {
    if (flags.noBackend) { warn('Backend 已跳过 (--no-backend)'); return true; }
    if (flags.force && await portInUse(ports.backend)) {
      info(`强制重启: 先停止端口 ${ports.backend} 上的 Backend...`);
      await stopBackend(ports.backend, mode);
      await sleep(1000);
    }
    const r = await startBackend(mode, flags.portBackend || null, { timeoutSec: timeoutSec || 60 });
    if (!r.ok) failed = true;
    return r.ok;
  }
  async function doStartWeb() {
    if (flags.noWeb) { warn('Web 已跳过 (--no-web)'); return true; }
    if (flags.force && await portInUse(ports.web)) {
      info(`强制重启: 先停止端口 ${ports.web} 上的 Web...`);
      await stopWeb(ports.web, mode);
      await sleep(1000);
    }
    const r = await startWeb(mode, flags.portWeb || null, { timeoutSec: timeoutSec || 45 });
    if (!r.ok) failed = true;
    return r.ok;
  }
  async function doStartNeo4j() {
    if (flags.noNeo4j) { warn('Neo4j 已跳过 (--no-neo4j)'); return true; }
    // Neo4j startup is config-driven: local mode = ragctl-managed install;
    // docker mode = compose. Port comes from config (graph.bolt_port).
    if (!(await portInUse(readGraphBoltPort()))) {
      await startNeo4j();
    } else {
      ok('Neo4j 已在运行');
    }
    return true; // Neo4j is optional — never fail the whole start for it
  }

  switch (svc) {
    case 'backend':
      await doStartBackend();
      break;
    case 'web':
      await doStartWeb();
      break;
    case 'neo4j':
      await doStartNeo4j();
      break;
    case 'all':
      await doStartNeo4j();
      await doStartBackend();
      await doStartWeb();
      break;
    default:
      err(`未知服务: ${svc}（可选: backend / web / neo4j / all）`);
      return 1;
  }
  return failed ? 1 : 0;
}

async function cmdStop(args) {
  const flags = parseFlags(args);
  const svc = getService(flags) || flags.only || 'all';
  const mode = flags.appmode;
  const ports = getServicePorts(mode);
  if (flags.portBackend) ports.backend = flags.portBackend;
  if (flags.portWeb) ports.web = flags.portWeb;

  header(`停止服务 (mode=${mode}): ${svc}`);

  switch (svc) {
    case 'backend': await stopBackend(ports.backend, mode); break;
    case 'web': await stopWeb(ports.web, mode); break;
    case 'neo4j': await stopNeo4j(); break;
    case 'all':
      await stopWeb(ports.web, mode);
      await stopBackend(ports.backend, mode);
      if (!flags.noNeo4j && (flags.force || flags.positional.includes('all') || args.includes('--all'))) {
        await stopNeo4j();
      }
      break;
    default:
      err(`未知服务: ${svc}（可选: backend / web / neo4j / all）`);
      return 1;
  }
  return 0;
}

async function cmdRestart(args) {
  const flags = parseFlags(args);
  // restart = stop + start (force implied)
  flags.force = true;
  const svc = getService(flags) || flags.only || 'all';
  header(`重启服务 (mode=${flags.appmode}): ${svc}`);

  const stopArgs = svc === 'all' ? ['all'] : [svc];
  // Build args array for cmdStop
  const stopFlags = [];
  if (flags.appmode) stopFlags.push('--appmode', flags.appmode);
  if (flags.noNeo4j) stopFlags.push('--no-neo4j');
  const stopCode = await cmdStop([...stopArgs, ...stopFlags]);
  if (stopCode !== 0) return stopCode;
  await sleep(1500);

  const startArgs = svc === 'all' ? ['all'] : [svc];
  const startFlags = [];
  if (flags.appmode) startFlags.push('--appmode', flags.appmode);
  if (flags.force) startFlags.push('--force');
  if (flags.noNeo4j) startFlags.push('--no-neo4j');
  if (flags.noBackend) startFlags.push('--no-backend');
  if (flags.noWeb) startFlags.push('--no-web');
  if (flags.portBackend) startFlags.push('--port-backend', String(flags.portBackend));
  if (flags.portWeb) startFlags.push('--port-web', String(flags.portWeb));
  const startCode = await cmdStart([...startArgs, ...startFlags]);
  if (startCode !== 0) return startCode;
  ok(`重启完成: ${svc} (mode=${flags.appmode})`);
  return 0;
}

// ── Log viewer ───────────────────────────────────────────────────────────
// `ragctl logs [service] [--tail|-f] [--lines N|-n N]`
//   service ∈ {backend, web, mineru} (default: backend)
// Reads the SAME files that Tauri's desktop log viewer tails and that
// spawnService writes — so output is consistent across all three surfaces.
async function cmdLogs(args) {
  const flags = parseFlags(args);
  const service = getService(flags) || 'backend';
  const wantTail = flags.tail;
  const lines = flags.lines;

  const logPath = getLogPath(service);
  if (!logPath) {
    err(`未知服务: ${service}`);
    info('可用: backend / web / mineru');
    return 1;
  }
  if (!fs.existsSync(logPath)) {
    warn(`日志文件尚未生成: ${logPath}`);
    info(`提示: 先启动该服务 → ragctl start ${service}，日志会自动写入`);
    info('所有服务均为静默启动（无终端窗口），日志统一落盘到此处 + Tauri 日志界面。');
    return 1;
  }

  if (wantTail) {
    info(`实时跟踪 ${service} 日志 (Ctrl+C 退出): ${logPath}`);
    const child = IS_WIN
      ? spawn('powershell', ['-NoProfile', '-Command',
          `Get-Content -LiteralPath '${logPath.replace(/'/g, "''")}' -Tail ${lines} -Wait -Encoding utf8`],
          { stdio: 'inherit' })
      : spawn('tail', ['-n', String(lines), '-f', logPath], { stdio: 'inherit' });
    return await new Promise(resolve => {
      const done = code => resolve(code || 0);
      child.on('close', done);
      child.on('exit', done);
      child.on('error', (e) => { err(`跟踪失败: ${e.message}`); resolve(1); });
    });
  }

  const content = fs.readFileSync(logPath, 'utf8');
  const all = content.split('\n');
  const tail = all.slice(-lines).join('\n');
  console.log(`\n  ${_c(C.GRAY, `── ${service} 日志（最后 ${lines} 行）── ${logPath} ──`)}`);
  console.log(tail.endsWith('\n') ? tail : tail + '\n');
  return 0;
}

async function cmdUp(args) {
  const flags = parseFlags(args);
  const mode = flags.appmode;
  const ports = getServicePorts(mode);
  if (flags.portBackend) ports.backend = flags.portBackend;
  if (flags.portWeb) ports.web = flags.portWeb;

  // Pre-flight: refuse to start a half-broken stack
  if (!flags.skipCheck) {
    const problems = preflightReady();
    if (problems.length) {
      header(`启动 RAG Knowledge Platform (mode=${mode}) — 预检失败`);
      err('环境未就绪：');
      for (const p of problems) console.log(`  ${_c(C.YELLOW, '• ' + p)}`);
      console.log();
      info('一键修复: ragctl setup');
      info('仅检查:   ragctl check');
      info('强制跳过: ragctl up --skip-check   （不推荐）');
      return 1;
    }
  }

  // Warn if the OTHER mode's ports are occupied (mixed-mode guard)
  const otherMode = mode === 'dev' ? 'prod' : 'dev';
  const otherPorts = getServicePorts(otherMode);
  const otherBackendUp = await portInUse(otherPorts.backend);
  const otherWebUp = await portInUse(otherPorts.web);
  if (otherBackendUp || otherWebUp) {
    warn(`${otherMode} 模式服务仍在运行（Backend:${otherPorts.backend} ${otherBackendUp ? 'UP' : 'DOWN'}, Web:${otherPorts.web} ${otherWebUp ? 'UP' : 'DOWN'}）`);
    info(`当前启动 mode=${mode}，如需停止 ${otherMode}：ragctl down --appmode ${otherMode}`);
  }

  header(`启动 RAG Knowledge Platform (mode=${mode})`);
  info(`端口: Backend=${ports.backend}, Web=${ports.web}`);

  const composeFile = path.join(PROJECT_ROOT, 'docker-compose.yml');
  const timeoutSec = flags.timeout || null;
  let backendOk = true;
  let webOk = true;

  // Neo4j (shared between modes) — config-driven ports/mode
  if (!flags.noNeo4j && !(await portInUse(readGraphBoltPort()))) {
    await startNeo4j();
  } else if (flags.noNeo4j) {
    warn('Neo4j 已跳过 (--no-neo4j)');
  } else if (await portInUse(7687)) {
    ok('Neo4j 已在运行');
  }

  // Backend
  if (flags.noBackend) {
    warn('Backend 已跳过 (--no-backend)');
  } else {
    if (flags.force && await portInUse(ports.backend)) {
      info(`强制重启: 先停止端口 ${ports.backend} 上的 Backend...`);
      await stopBackend(ports.backend, mode);
      await sleep(1000);
    }
    const r = await startBackend(mode, flags.portBackend || null, { timeoutSec: timeoutSec || 60 });
    backendOk = !!r.ok;
  }

  // Web
  if (flags.noWeb) {
    warn('Web 已跳过 (--no-web)');
  } else {
    if (flags.force && await portInUse(ports.web)) {
      info(`强制重启: 先停止端口 ${ports.web} 上的 Web...`);
      await stopWeb(ports.web, mode);
      await sleep(1000);
    }
    const r = await startWeb(mode, flags.portWeb || null, { timeoutSec: timeoutSec || 45 });
    webOk = !!r.ok;
  }

  // Summary — use health, not bare port
  const bHealth = backendOk
    ? await httpGet(`http://127.0.0.1:${ports.backend}/api/v1/health`, 2500)
    : { code: 0 };
  const wHealth = webOk
    ? await httpGet(`http://127.0.0.1:${ports.web}/api/kb/catalog`, 2500)
    : { code: 0 };
  const bUp = bHealth.code === 200;
  const wUp = wHealth.code === 200;

  console.log();
  if (bUp && wUp) {
    console.log(`  ${_c(C.GREEN, _c(C.BOLD, '✓ 所有服务已静默启动并就绪（无终端窗口）'))}`);
  } else {
    console.log(`  ${_c(C.YELLOW, '⚠ 部分服务未就绪')}`);
    if (!bUp) err(`Backend 未就绪 — 看日志: ragctl logs backend`);
    if (!wUp) err(`Web 未就绪 — 看日志: ragctl logs web`);
  }
  if (bUp) console.log(`  Backend (${mode}): ${_c(C.CYAN, `http://localhost:${ports.backend}`)}`);
  if (wUp) console.log(`  Web UI  (${mode}): ${_c(C.CYAN, `http://localhost:${ports.web}`)}`);
  console.log(`  ${_c(C.GRAY, '查看日志: ragctl logs [backend|web|mineru] --tail')}`);
  console.log(`  ${_c(C.GRAY, '查看状态: ragctl status')}`);
  return (bUp && wUp) ? 0 : 1;
}

async function cmdDown(args) {
  const flags = parseFlags(args);
  const mode = flags.appmode;
  const ports = getServicePorts(mode);
  if (flags.portBackend) ports.backend = flags.portBackend;
  if (flags.portWeb) ports.web = flags.portWeb;

  header(`停止 RAG Knowledge Platform (mode=${mode})`);
  info(`目标端口: Backend=${ports.backend}, Web=${ports.web}`);

  await stopWeb(ports.web, mode);
  await stopBackend(ports.backend, mode);

  // Neo4j is shared infra — only stop if explicitly requested via --all / --force-neo4j
  // (prevents `down --appmode prod` from killing Neo4j needed by dev)
  if (flags.positional.includes('all') || args.includes('--all') || flags.force) {
    // Only stop Neo4j when user is explicit; --force alone shouldn't kill shared DB
    // unless combined with 'all' positional or --all.
    if (flags.positional.includes('all') || args.includes('--all')) {
      await stopNeo4j();
    }
  }

  ok(`所有 ${mode} 服务已停止 (Neo4j 保留)`);
  return 0;
}

async function cmdStatus(args) {
  const flags = parseFlags(args);

  // If user specifies --appmode, show only that mode. Otherwise show both.
  if (flags.appmode && (args.includes('--appmode') || args.includes('--mode') || args.includes('-m'))) {
    return await _showModeStatus(flags.appmode);
  }

  // Default: show both dev and prod
  await _showModeStatus('dev');
  console.log('');
  await _showModeStatus('prod');
  return 0;
}

async function _showModeStatus(mode) {
  const ports = getServicePorts(mode);

  async function probe(port, healthPath) {
    const listening = await portInUse(port);
    if (!listening) return { listening: false, health: '', pid: null };
    const pid = findPidOnPort(port);
    const r = await httpGet(`http://localhost:${port}${healthPath}`, 3000);
    const health = r.code === 200 ? 'healthy' : (r.code ? `HTTP ${r.code}` : 'no-response');
    return { listening: true, health, pid };
  }

  const b = await probe(ports.backend, '/api/v1/health');
  const w = await probe(ports.web, '/api/kb/catalog');
  const neo4jUp = await portInUse(7687);
  const neo4jHttp = await portInUse(7474);

  let mineru = 'n/a (backend down)';
  if (b.health === 'healthy') {
    const m = await httpGet(`http://localhost:${ports.backend}/api/v1/mineru/status`, 4000);
    mineru = m.code === 200 ? 'up' : (m.code ? `HTTP ${m.code}` : 'unreachable');
  }
  const mcpProcs = findPythonProcesses('server.py');

  const dot = (on) => on ? _c(C.GREEN, '●') : _c(C.RED, '○');
  const hcol = (h) => h === 'healthy' ? _c(C.GREEN, h)
    : (h ? _c(C.YELLOW, h) : _c(C.GRAY, 'stopped'));

  const ready = b.health === 'healthy' && w.health === 'healthy';

  console.log(`${_c(C.BOLD, _c(C.CYAN, `  ══ ${mode.toUpperCase()} MODE ══`))}${ready ? '  ' + _c(C.GREEN, '✓ READY') : '  ' + _c(C.YELLOW, '✗ NOT READY')}`);
  console.log(`  ${dot(b.listening)} Backend  :${String(ports.backend).padEnd(5)} ${hcol(b.health)}${b.pid ? '  pid=' + _c(C.GRAY, b.pid) : ''}`);
  console.log(`  ${dot(w.listening)} Web      :${String(ports.web).padEnd(5)} ${hcol(w.health)}${w.pid ? '  pid=' + _c(C.GRAY, w.pid) : ''}`);
  if (mode === 'dev') {
    console.log(`  ${dot(neo4jUp)} Neo4j    :7687  ${neo4jUp ? _c(C.GREEN, 'listening') + (neo4jHttp ? ' ' + _c(C.GRAY,'(+http :7474)') : '') : _c(C.GRAY, 'stopped')}`);
    console.log(`  ${mineru.startsWith('up') ? _c(C.GREEN, '●') : _c(C.GRAY, '○')} MinerU          ${_c(mineru.startsWith('up') ? C.GREEN : C.GRAY, mineru)}`);
    console.log(`  ${mcpProcs.length > 0 ? _c(C.GREEN, '●') : _c(C.GRAY, '○')} kb-mcp  (stdio) ${mcpProcs.length > 0 ? _c(C.GREEN, mcpProcs.length + ' proc') : _c(C.GRAY, 'managed by Claude Code via .mcp.json')}`);
  }
}

// ── Global registration + Tauri launcher ────────────────────────────────

// `ragctl install` — register `ragctl` globally so it works from any directory.
// Writes a small wrapper that hardcodes the absolute project path (NOT a copy/
// symlink of the repo wrapper — those break because ragctl.bat resolves paths
// relative to its own location). Target dir is ~/.local/bin (same place uv
// installs, so it's already on PATH after `ragctl setup`).
async function cmdInstall() {
  header('全局注册 ragctl');
  const binDir = path.join(os.homedir(), '.local', 'bin');
  fs.mkdirSync(binDir, { recursive: true });
  const jsEntry = path.join(PROJECT_ROOT, 'command', 'ragctl.js');

  if (IS_WIN) {
    const dest = path.join(binDir, 'ragctl.cmd');
    fs.writeFileSync(dest, `@echo off\r\nnode "${jsEntry}" %*\r\n`, 'utf8');
    ok(`已写入 ${dest}`);
  } else {
    const dest = path.join(binDir, 'ragctl');
    fs.writeFileSync(dest, `#!/usr/bin/env bash\nexec node "${jsEntry}" "$@"\n`, 'utf8');
    fs.chmodSync(dest, 0o755);
    ok(`已写入 ${dest}`);
  }

  // PATH check + safe persist on Windows
  const pathDirs = (process.env.PATH || '').split(path.delimiter);
  if (pathDirs.includes(binDir)) {
    ok(`${binDir} 已在 PATH 中 — ragctl 现可全局使用`);
  } else {
    if (IS_WIN && appendUserPath(binDir)) {
      ok(`已将 ${binDir} 写入用户 PATH（新开终端后生效）`);
    } else {
      warn(`${binDir} 尚不在 PATH 中。添加方法：`);
      if (IS_WIN) info(`  手动: 系统属性 → 环境变量 → Path → 新建 ${binDir}`);
      else info(`  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc`);
    }
  }
  info('测试: 在任意目录运行 `ragctl status`');
  return 0;
}

// ── Clean: cache & MinerU artifact management ───────────────────────────

// Recursively compute a directory's size in bytes (best-effort, skips errors).
function dirSizeBytes(dir) {
  if (!dir || !fs.existsSync(dir)) return 0;
  let total = 0;
  const walk = (d) => {
    let entries;
    try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      const p = path.join(d, e.name);
      try {
        if (e.isDirectory()) walk(p);
        else total += fs.statSync(p).size;
      } catch {}
    }
  };
  walk(dir);
  return total;
}

function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

// rm -rf — force-remove a path, never throws.
function rmrf(target) {
  try { fs.rmSync(target, { recursive: true, force: true }); return true; }
  catch { return false; }
}

// Scan for __pycache__ / .pytest_cache / *.pyc under a root (depth-limited).
function findPyCacheDirs(root, maxDepth = 4) {
  const found = [];
  if (!fs.existsSync(root)) return found;
  const walk = (d, depth) => {
    if (depth > maxDepth) return;
    let entries;
    try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (!e.isDirectory()) continue;
      const p = path.join(d, e.name);
      if (e.name === '__pycache__' || e.name === '.pytest_cache') {
        found.push(p);
      } else if (!e.name.startsWith('.') && e.name !== 'node_modules' && e.name !== '.venv' && e.name !== 'site-packages') {
        walk(p, depth + 1);
      }
    }
  };
  walk(root, 0);
  return found;
}

// Interactive y/N prompt. Returns true for [y]/[yes].
function confirm(message) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    rl.question(message, (answer) => {
      rl.close();
      resolve(['y', 'yes'].includes(String(answer).toLowerCase().trim()));
    });
  });
}

// `ragctl clean` — reclaim disk by removing caches and MinerU parse artifacts.
//
// Safety model:
//   • Default scope = MinerU output only (the most common ask, always safe —
//     artifacts are already imported into the KB before they land here).
//   • Model caches are NEVER touched without an explicit --model flag, and
//     require an extra yes-confirm (re-download is ~4 GB for BGE-M3 alone).
//   • KB data (storage/tree-file-system), .env, and config.yml are never
//     in scope — clean only deletes what ragctl/setup/parse generated.
async function cmdClean(args) {
  header('清理缓存与 MinerU 解析产物');

  const dryRun = args.includes('--dry-run') || args.includes('-n');
  const force = args.includes('--force') || args.includes('-y') || args.includes('--yes');
  const wantMineru = args.includes('--mineru') || args.includes('--parse');
  const wantLogs = args.includes('--logs');
  const wantPycache = args.includes('--pycache');
  const wantModel = args.includes('--model') || args.includes('--models');
  const wantAll = args.includes('--all');
  // No specific scope flag → default to MinerU output (the primary use case).
  const defaultScope = !wantMineru && !wantLogs && !wantPycache && !wantModel && !wantAll;
  const scopeMineru = wantMineru || defaultScope || wantAll;
  const scopeLogs = wantLogs || wantAll;
  const scopePycache = wantPycache || wantAll;
  const scopeModel = wantModel;  // never implied by --all

  // ---- gather targets -----------------------------------------------------

  // 1. MinerU parse output — backend/output/{uuid}/{stem.md, images/, uploads/}
  const mineruOut = path.join(BACKEND_DIR, 'output');
  const mineruSize = dirSizeBytes(mineruOut);

  // 2. Service logs — backend/logs + web/logs
  const logDirs = [path.join(BACKEND_DIR, 'logs'), path.join(WEB_DIR, 'logs')];
  const logsSize = logDirs.reduce((s, d) => s + dirSizeBytes(d), 0);

  // 3. Python __pycache__ / .pytest_cache under backend/ and kb-mcp/
  const pyDirs = [
    ...findPyCacheDirs(BACKEND_DIR),
    ...findPyCacheDirs(MCP_DIR),
  ];
  const pySize = pyDirs.reduce((s, d) => s + dirSizeBytes(d), 0);

  // 4. Model caches (LARGE — explicit --model only)
  const modelDirs = [path.join(PROJECT_ROOT, 'models_cache')];
  const home = os.homedir();
  const msCache = path.join(home, '.cache', 'modelscope');
  if (fs.existsSync(msCache)) modelDirs.push(msCache);
  const modelSize = modelDirs.reduce((s, d) => s + dirSizeBytes(d), 0);

  // ---- print scan table ---------------------------------------------------

  console.log(`\n  ${_c(C.BOLD, '扫描结果:')}\n`);
  const rows = [
    ['MinerU 解析产物', mineruSize, scopeMineru, 'backend/output/ — 解析生成的 md/images/uploads'],
    ['服务日志', logsSize, scopeLogs, 'backend/logs/ + web/logs/'],
    ['Python 缓存', pySize, scopePycache, '__pycache__ / .pytest_cache（可重建）'],
    ['模型缓存', modelSize, scopeModel, 'BGE-M3 + MinerU 模型（清理后需重新下载）'],
  ];
  console.log(`  ${'类别'.padEnd(18)}${'大小'.padEnd(12)}${'操作'.padEnd(10)}说明`);
  console.log(`  ${'─'.repeat(70)}`);
  for (const [name, size, enabled, desc] of rows) {
    const op = enabled
      ? (size > 0 ? _c(C.GREEN, '清理'.padEnd(10)) : _c(C.GRAY, '空'.padEnd(10)))
      : _c(C.GRAY, '跳过'.padEnd(10));
    console.log(`  ${name.padEnd(18)}${fmtSize(size).padEnd(12)}${op}${_c(C.GRAY, desc)}`);
  }

  // ---- compute active set & total -----------------------------------------

  const active = [];
  if (scopeMineru && mineruSize > 0) active.push({ name: 'MinerU 解析产物', size: mineruSize, paths: [mineruOut], mode: 'contents', safe: true });
  if (scopeLogs && logsSize > 0) active.push({ name: '服务日志', size: logsSize, paths: logDirs, mode: 'contents', safe: true });
  if (scopePycache && pySize > 0) active.push({ name: 'Python 缓存', size: pySize, paths: pyDirs, mode: 'dirs', safe: true });
  if (scopeModel && modelSize > 0) active.push({ name: '模型缓存', size: modelSize, paths: modelDirs, mode: 'dirs', safe: false });

  const totalSize = active.reduce((s, t) => s + t.size, 0);

  if (active.length === 0) {
    console.log(`\n  ${_c(C.GREEN, '✓')} 所选范围内无需清理 — 全部为空。`);
    console.log(`  ${_c(C.GRAY, '提示: ragctl clean --all (安全项) · ragctl clean --model (含模型, 重新下载)')}`);
    return 0;
  }

  console.log(`\n  ${_c(C.BOLD, '将清理:')} ${active.map(t => `${t.name} (${fmtSize(t.size)})`).join(' · ')}`);
  console.log(`  ${_c(C.BOLD, '释放空间:')} ${_c(C.CYAN, fmtSize(totalSize))}`);

  if (dryRun) {
    console.log(`\n  ${_c(C.GRAY, 'ⓘ --dry-run 模式：仅扫描，未删除任何文件')}`);
    return 0;
  }

  // ---- confirm ------------------------------------------------------------

  const hasModel = active.some(t => !t.safe);
  if (hasModel && !force) {
    console.log(`\n  ${_c(C.RED, '⚠ 模型缓存将被删除 — 下次使用需重新下载 ~' + fmtSize(modelSize))}`);
  }
  if (!force) {
    const msg = hasModel
      ? `\n  ${_c(C.BOLD, '输入 yes 确认清理 (含模型): ')}`
      : `\n  ${_c(C.BOLD, '确认清理以上内容? [y/N]: ')}`;
    const yes = await confirm(msg);
    if (!yes) { console.log(`  ${_c(C.GRAY, '已取消')}`); return 0; }
  }

  // ---- execute ------------------------------------------------------------

  let freed = 0;
  for (const t of active) {
    for (const p of t.paths) {
      if (!p || !fs.existsSync(p)) continue;
      const sz = dirSizeBytes(p);
      if (t.mode === 'contents') {
        // Delete directory contents but keep the directory itself.
        let entries = [];
        try { entries = fs.readdirSync(p, { withFileTypes: true }); } catch {}
        for (const e of entries) rmrf(path.join(p, e.name));
        ok(`已清空 ${path.relative(PROJECT_ROOT, p) || p}/`);
      } else {
        rmrf(p);
        ok(`已删除 ${path.relative(PROJECT_ROOT, p) || p}`);
      }
      freed += sz;
    }
  }

  console.log(`\n  ${_c(C.GREEN, _c(C.BOLD, '✓ 清理完成 — 释放 ' + fmtSize(freed) + ' 磁盘空间'))}`);
  if (hasModel) {
    info('模型已删除 — 下次 ragctl model 或首次向量索引时自动重新下载');
  }
  return 0;
}

// `ragctl backup` / `ragctl restore` — Cross-platform backup & restore
// (replaces the bash-only scripts/backup.sh and scripts/restore.sh).
// Uses tar (available on Windows 10+, macOS, Linux) + docker for Neo4j.
//
// Usage:
//   ragctl backup [dest] [--dry-run] [-y]     Backs up KB docs + ChromaDB + Neo4j
//   ragctl restore <src> [--force] [-y]        Restores from a backup dir

const NEO4J_CONTAINER = 'rag-knowledge-neo4j';

// tar is available on Windows 10+ (bsdtar/libarchive), macOS (bsdtar), Linux (GNU tar).
// Flags -czf / -xzf are portable across all three.
function tarAvailable() {
  try { execSync('tar --version', { stdio: 'ignore', timeout: 5000, shell: IS_WIN }); return true; }
  catch { return false; }
}

// `ragctl backup [dest-dir] [--dry-run] [-y]`
async function cmdBackup(args = []) {
  const dryRun = args.includes('--dry-run') || args.includes('-n');

  const positional = args.filter(a => !a.startsWith('-'));
  const timestamp = new Date().toISOString().replace(/[:T]/g, '-').slice(0, 19);
  const destDir = positional[0]
    ? path.resolve(positional[0])
    : path.join(PROJECT_ROOT, 'storage', 'backups', timestamp);

  header('RAG Knowledge Platform — Backup');
  console.log(`  ${_c(C.GRAY, '目标:')} ${destDir}`);
  if (dryRun) console.log(`  ${_c(C.YELLOW, '[DRY-RUN] 仅扫描，不写入')}`);
  console.log('');

  if (!tarAvailable()) {
    err('未找到 tar — Windows 10 1803+ 自带 bsdtar，Linux/macOS 默认有');
    return 1;
  }

  if (!dryRun) fs.mkdirSync(destDir, { recursive: true });

  let failCount = 0;

  // ── 1. KB Documents + Metadata ────────────────────────────
  step('1/3 — KB 文档 + 元数据 (tree-file-system)');
  const treeFs = path.join(PROJECT_ROOT, 'storage', 'tree-file-system');
  if (fs.existsSync(treeFs)) {
    info(`源: storage/tree-file-system (${fmtSize(dirSizeBytes(treeFs))})`);
    if (!dryRun) {
      const archive = path.join(destDir, 'tree-fs.tar.gz');
      const r = await spawnAsync('tar', ['-czf', archive, '-C', path.join(PROJECT_ROOT, 'storage'), 'tree-file-system'], { silent: true });
      if (r.code === 0) ok(`tree-fs.tar.gz (${fmtSize(fs.statSync(archive).size)})`);
      else { err(`打包失败: ${(r.stderr || '').slice(0, 200)}`); failCount++; }
    } else info('[DRY-RUN] 将打包 tree-fs.tar.gz');
  } else warn('storage/tree-file-system/ 不存在，跳过');

  // ── 2. Vector Index (ChromaDB) ────────────────────────────
  step('2/3 — 向量索引 (chroma_db)');
  const chromaDir = path.join(PROJECT_ROOT, 'chroma_db');
  if (fs.existsSync(chromaDir)) {
    info(`源: chroma_db/ (${fmtSize(dirSizeBytes(chromaDir))})`);
    if (!dryRun) {
      const archive = path.join(destDir, 'chroma_db.tar.gz');
      const r = await spawnAsync('tar', ['-czf', archive, '-C', PROJECT_ROOT, 'chroma_db'], { silent: true });
      if (r.code === 0) ok(`chroma_db.tar.gz (${fmtSize(fs.statSync(archive).size)})`);
      else { err(`打包失败: ${(r.stderr || '').slice(0, 200)}`); failCount++; }
    } else info('[DRY-RUN] 将打包 chroma_db.tar.gz');
  } else warn('chroma_db/ 不存在 — 先运行 kb_reindex');

  // ── 3. Neo4j Graph Database ───────────────────────────────
  step('3/3 — Neo4j 图数据库');
  let neo4jRunning = false;
  try {
    const out = execSync('docker ps --format {{.Names}}', { encoding: 'utf8', timeout: 8000, shell: IS_WIN, stdio: ['pipe', 'pipe', 'pipe'] });
    neo4jRunning = out.split('\n').some(n => n.trim() === NEO4J_CONTAINER);
  } catch {}

  if (neo4jRunning) {
    if (!dryRun) {
      const dumpResult = await spawnAsync('docker', ['exec', NEO4J_CONTAINER, 'neo4j-admin', 'database', 'dump', 'neo4j', '--to-path=/tmp', '--overwrite-destination=true'], { silent: true });
      if (dumpResult.code === 0) {
        const cpResult = await spawnAsync('docker', ['cp', `${NEO4J_CONTAINER}:/tmp/neo4j.dump`, path.join(destDir, 'neo4j.dump')], { silent: true });
        if (cpResult.code === 0) ok(`neo4j.dump (${fmtSize(fs.statSync(path.join(destDir, 'neo4j.dump')).size)})`);
        else warn('dump 已创建但复制失败');
      } else {
        warn(`Neo4j dump 失败 — 社区版不支持 database dump，可用 schema export 替代`);
      }
    } else info('[DRY-RUN] 将通过 docker exec 导出 neo4j.dump');
  } else warn('Neo4j 容器未运行 — 图数据库未备份（可选）');

  // ── Summary ─────────────────────────────────────────────
  console.log('');
  if (failCount > 0) { err(`备份完成，${failCount} 项失败`); return 1; }
  ok(dryRun ? `[DRY-RUN] 无错误 → ${destDir}` : `备份完成!  位置: ${destDir}`);
  return 0;
}

// `ragctl restore <backup-dir> [--force] [-y]`
async function cmdRestore(args = []) {
  const positional = args.filter(a => !a.startsWith('-'));
  const skipConfirm = args.includes('--force') || args.includes('-y') || args.includes('--yes');
  const backupDir = positional[0] ? path.resolve(positional[0]) : null;

  header('RAG Knowledge Platform — Restore');
  if (!backupDir || !fs.existsSync(backupDir)) {
    err('用法: ragctl restore <backup-directory>');
    info('示例: ragctl restore storage/backups/2026-07-14_12-00-00');
    return 1;
  }
  console.log(`  ${_c(C.GRAY, '来源:')} ${backupDir}\n`);

  // Pre-flight: services must be stopped
  const { backend: bp, web: wp } = getServicePorts(getAppMode());
  if ((await portInUse(bp)) || (await portInUse(wp))) {
    err('服务仍在运行 — 恢复前先停止: ragctl down');
    return 1;
  }

  if (!tarAvailable()) { err('未找到 tar'); return 1; }

  if (!skipConfirm) {
    warn('此操作将覆盖当前数据!');
    if (!await confirm('确定继续恢复?')) { info('已取消'); return 0; }
  }

  let failCount = 0;

  // 1. tree-file-system
  step('1/3 — 恢复 KB 文档');
  const treeArchive = path.join(backupDir, 'tree-fs.tar.gz');
  if (fs.existsSync(treeArchive)) {
    rmrf(path.join(PROJECT_ROOT, 'storage', 'tree-file-system'));
    const r = await spawnAsync('tar', ['-xzf', treeArchive, '-C', path.join(PROJECT_ROOT, 'storage')], { silent: true });
    if (r.code === 0) ok('tree-file-system 已恢复'); else { err('恢复失败'); failCount++; }
  } else warn('无 tree-fs.tar.gz，跳过');

  // 2. chroma_db
  step('2/3 — 恢复向量索引');
  const chromaArchive = path.join(backupDir, 'chroma_db.tar.gz');
  if (fs.existsSync(chromaArchive)) {
    rmrf(path.join(PROJECT_ROOT, 'chroma_db'));
    const r = await spawnAsync('tar', ['-xzf', chromaArchive, '-C', PROJECT_ROOT], { silent: true });
    if (r.code === 0) ok('chroma_db 已恢复'); else { err('恢复失败'); failCount++; }
  } else warn('无 chroma_db.tar.gz，跳过');

  // 3. neo4j
  step('3/3 — 恢复 Neo4j 图数据库');
  const neo4jDump = path.join(backupDir, 'neo4j.dump');
  if (fs.existsSync(neo4jDump)) {
    let neo4jRunning = false;
    try {
      const out = execSync('docker ps --format {{.Names}}', { encoding: 'utf8', timeout: 8000, shell: IS_WIN, stdio: ['pipe', 'pipe', 'pipe'] });
      neo4jRunning = out.split('\n').some(n => n.trim() === NEO4J_CONTAINER);
    } catch {}

    if (neo4jRunning) {
      const cpResult = await spawnAsync('docker', ['cp', neo4jDump, `${NEO4J_CONTAINER}:/tmp/neo4j.dump`], { silent: true });
      if (cpResult.code === 0) {
        info('手动完成恢复:');
        info(`  docker exec ${NEO4J_CONTAINER} neo4j-admin database load neo4j --from-path=/tmp --overwrite-destination=true`);
        info(`  docker restart ${NEO4J_CONTAINER}`);
        ok('neo4j.dump 已就位');
      } else warn('dump 复制失败');
    } else {
      warn('Neo4j 容器未运行 — 启动后手动恢复');
      info(`  docker cp ${neo4jDump} ${NEO4J_CONTAINER}:/tmp/neo4j.dump`);
    }
  } else warn('无 neo4j.dump，跳过');

  console.log('');
  if (failCount > 0) { err(`恢复完成，${failCount} 项失败`); return 1; }
  ok('恢复完成!  下一步: ragctl up → kb_graph_build 验证');
  return 0;
}

// `ragctl desktop` / `ragctl ui` — launch the Tauri desktop console (the GUI
// launcher). Prefers a compiled binary; falls back to `cargo tauri dev`.
// The Tauri app starts/monitors services through the SAME shared log files
// ragctl uses, so the two launchers are fully interchangeable.
async function cmdDesktop(args) {
  header('启动 Tauri 桌面控制台');
  const tauriDir = path.join(PROJECT_ROOT, 'src-tauri');
  if (!fs.existsSync(path.join(tauriDir, 'Cargo.toml'))) {
    err('src-tauri/ 未找到（Tauri 桌面应用未包含）');
    return 1;
  }
  const ext = IS_WIN ? '.exe' : '';
  const releaseBin = path.join(tauriDir, 'target', 'release', `rag-knowledge-desktop${ext}`);
  const debugBin = path.join(tauriDir, 'target', 'debug', `rag-knowledge-desktop${ext}`);
  const wantDev = args.includes('--dev') || args.includes('dev');

  function launch(bin, label) {
    spawn(bin, [], { detached: true, stdio: 'ignore', windowsHide: false }).unref();
    ok(`Tauri 桌面控制台已启动 (${label})`);
    info('桌面控制台可启动/停止/监控所有服务，日志与 ragctl 共享同一文件。');
  }

  if (!wantDev && fs.existsSync(releaseBin)) { launch(releaseBin, 'release'); return 0; }
  if (!wantDev && fs.existsSync(debugBin)) { launch(debugBin, 'debug'); return 0; }

  // No prebuilt binary → build via cargo tauri (long first compile)
  if (!commandExists('cargo')) {
    err('未找到编译好的 Tauri 二进制，也未找到 cargo (Rust)');
    info('先安装 Rust: https://rustup.rs  然后构建: cd src-tauri && cargo tauri build');
    return 1;
  }
  // confirm tauri CLI is available
  let hasTauriCli = false;
  try { execSync('cargo tauri --version', { stdio: 'ignore', timeout: 8000, shell: IS_WIN }); hasTauriCli = true; }
  catch {
    // try the npm-installed tauri too
    try { execSync('npx tauri --version', { stdio: 'ignore', timeout: 15000, shell: IS_WIN }); hasTauriCli = true; } catch {}
  }
  if (!hasTauriCli) {
    err('cargo-tauri CLI 未安装');
    info('安装: cargo install tauri-cli --version "^2.0.0"  (然后重跑 ragctl desktop)');
    return 1;
  }
  info('以 cargo tauri dev 启动 (首次编译需数分钟，请耐心等待)...');
  spawn('cargo', ['tauri', 'dev'], { cwd: tauriDir, detached: true, stdio: 'ignore', windowsHide: false }).unref();
  ok('cargo tauri dev 已在后台启动');
  return 0;
}

// ── Version + Update ───────────────────────────────────────────────────

async function cmdVersion(args = []) {
  const json = args.includes('--json');
  const localVersion = readLocalVersion();
  const git = getLocalGitInfo();
  let remote = null;
  if (!args.includes('--local')) {
    try { remote = await fetchRemoteVersionInfo(); } catch (e) {
      remote = { error: e.message };
    }
    // Prefer local origin/* tip (after lightweight fetch) for accurate ancestry
    if (git.isGit) {
      const originTip = fetchOriginTip(git.branch && git.branch !== 'HEAD' ? git.branch : GITHUB_DEFAULT_BRANCH);
      if (originTip) {
        remote = remote || {};
        // Keep GitHub API sha if present, but origin tip is authoritative for pull decision
        remote.originSha = originTip;
        if (!remote.remoteSha) remote.remoteSha = originTip;
        if (!remote.source) remote.source = 'origin-ref';
      }
    }
  }

  const payload = {
    local: {
      version: localVersion,
      sha: git.sha,
      branch: git.branch,
      dirty: git.dirty,
      is_git: git.isGit,
      project_root: PROJECT_ROOT,
    },
    remote: remote ? {
      version: remote.remoteVersion || null,
      tag: remote.remoteTag || null,
      sha: remote.remoteSha || null,
      origin_sha: remote.originSha || null,
      url: remote.remoteUrl || `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}`,
      source: remote.source || null,
      error: remote.error || null,
    } : null,
  };

  // Decide update status: semver first, then git ancestry
  let comparison = 'unknown';
  let updateAvailable = null;
  if (remote && remote.remoteVersion) {
    const cmp = compareSemver(localVersion, remote.remoteVersion);
    if (cmp < 0) { comparison = 'behind'; updateAvailable = true; }
    else if (cmp > 0) { comparison = 'ahead'; updateAvailable = false; }
    else {
      // same VERSION number — refine with git ancestry
      const tip = remote.originSha || remote.remoteSha;
      const rel = compareGitTips(git.sha, tip);
      comparison = rel === 'equal' ? 'equal' : rel;
      updateAvailable = rel === 'behind' || rel === 'diverged';
    }
  } else if (remote && (remote.originSha || remote.remoteSha) && git.sha) {
    const tip = remote.originSha || remote.remoteSha;
    const rel = compareGitTips(git.sha, tip);
    comparison = rel;
    updateAvailable = rel === 'behind' || rel === 'diverged';
  }
  payload.update_available = updateAvailable;
  payload.comparison = comparison;

  if (json) {
    console.log(JSON.stringify(payload, null, 2));
    return 0;
  }

  header(`ragctl version  v${localVersion}`);
  info(`Local version : ${_c(C.BOLD, localVersion)}`);
  if (git.isGit) {
    info(`Git           : ${git.branch || '?'} @ ${git.sha || '?'}${git.dirty ? ' (dirty)' : ''}`);
  } else {
    warn('Not a git checkout — update via git pull unavailable');
  }
  info(`Project root  : ${PROJECT_ROOT}`);

  if (remote) {
    if (remote.remoteVersion || remote.remoteSha || remote.originSha) {
      const rSha = remote.originSha || remote.remoteSha || '';
      info(`Remote        : ${remote.remoteVersion ? 'v' + remote.remoteVersion : '(no VERSION)'} ${remote.remoteTag ? `(${remote.remoteTag})` : ''} ${rSha ? '@ ' + rSha : ''}`);
      info(`Source        : ${remote.source || 'n/a'} · ${remote.remoteUrl || ''}`);
      if (updateAvailable === true) {
        warn(`Update available: ${comparison} (local ${localVersion}@${git.sha || '?'} → remote ${remote.remoteVersion || ''}@${rSha})`);
        info('Run: ragctl update');
      } else if (updateAvailable === false) {
        ok(`Up to date / local ahead (${comparison})`);
      } else {
        warn(`Could not determine update status (${comparison})${remote.error ? ': ' + remote.error : ''}`);
      }
    } else {
      warn(`Could not reach GitHub: ${remote.error || 'unknown error'}`);
    }
  }
  return 0;
}

/**
 * ragctl update — compare local VERSION/SHA with GitHub, pull if newer.
 *
 * Flags:
 *   --check / -n     Dry-run: only report, never pull
 *   --force / -f     Pull even if versions look equal (or only SHA differs)
 *   --no-deps        After pull, skip reinstalling deps
 *   --restart        After pull, restart services (ragctl up --force)
 *   --json           Machine-readable result
 *   --yes / -y       Non-interactive (always proceed when update available)
 */
async function cmdUpdate(args = []) {
  const flags = {
    check: args.includes('--check') || args.includes('-n'),
    force: args.includes('--force') || args.includes('-f'),
    noDeps: args.includes('--no-deps'),
    restart: args.includes('--restart'),
    json: args.includes('--json'),
    yes: args.includes('--yes') || args.includes('-y'),
  };

  header(flags.check ? '检查更新 (dry-run)' : '检查并更新项目');

  const localVersion = readLocalVersion();
  const git = getLocalGitInfo();
  if (!git.isGit) {
    err('当前目录不是 git 仓库，无法自动更新。请重新 clone：');
    info(`  git clone https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}.git`);
    return 1;
  }

  info(`Local  : v${localVersion}  (${git.branch || '?'} @ ${git.sha || '?'}${git.dirty ? ', dirty' : ''})`);

  let remote;
  try {
    remote = await fetchRemoteVersionInfo();
  } catch (e) {
    err(`无法获取远程版本: ${e.message}`);
    return 1;
  }
  // Always try local origin tip (more accurate for ancestry than short GitHub API sha)
  const branch = git.branch && git.branch !== 'HEAD' ? git.branch : GITHUB_DEFAULT_BRANCH;
  const originTip = fetchOriginTip(branch);
  if (originTip) {
    remote.originSha = originTip;
    if (!remote.remoteSha) remote.remoteSha = originTip;
    if (!remote.source) remote.source = 'origin-ref';
  }

  if (!remote.remoteVersion && !remote.remoteSha && !remote.originSha) {
    err(`无法获取远程版本信息: ${remote.error || 'unknown'}`);
    info('可检查网络 / 代理，或手动: git pull');
    return 1;
  }

  const tipSha = remote.originSha || remote.remoteSha || '';
  info(`Remote : ${remote.remoteVersion ? 'v' + remote.remoteVersion : '(no VERSION)'} ${remote.remoteTag ? `(${remote.remoteTag})` : ''} ${tipSha ? '@ ' + tipSha : ''}  [${remote.source || 'n/a'}]`);

  let needUpdate = false;
  let reason = '';
  let relation = 'unknown';

  if (remote.remoteVersion) {
    const cmp = compareSemver(localVersion, remote.remoteVersion);
    if (cmp < 0) {
      needUpdate = true;
      relation = 'behind';
      reason = `version behind (${localVersion} < ${remote.remoteVersion})`;
    } else if (cmp > 0) {
      relation = 'ahead';
      reason = `local ahead (${localVersion} > ${remote.remoteVersion})`;
    } else {
      relation = compareGitTips(git.sha, tipSha);
      if (relation === 'behind' || relation === 'diverged') {
        needUpdate = true;
        reason = `same version ${localVersion} but git is ${relation} (local ${git.sha} vs remote ${tipSha})`;
      } else if (relation === 'ahead') {
        reason = `same version ${localVersion}; local commits not on remote (ahead)`;
      } else if (relation === 'equal') {
        reason = `up to date (v${localVersion} @ ${git.sha})`;
      } else {
        reason = `same version ${localVersion}; git relation unknown`;
      }
    }
  } else {
    relation = compareGitTips(git.sha, tipSha);
    if (relation === 'behind' || relation === 'diverged') {
      needUpdate = true;
      reason = `git is ${relation} (local ${git.sha} ≠ remote ${tipSha})`;
    } else if (relation === 'ahead') {
      reason = `local ahead of remote (${git.sha} has commits not on ${tipSha})`;
    } else if (relation === 'equal') {
      reason = `SHA match (${git.sha})`;
    } else {
      reason = `unable to compare SHAs (local ${git.sha}, remote ${tipSha})`;
    }
  }

  if (flags.force && !needUpdate) {
    needUpdate = true;
    reason = (reason ? reason + '; ' : '') + 'forced by --force';
  }

  if (!needUpdate) {
    ok(`已是最新 / 无需 pull: ${reason}`);
    if (flags.json) {
      console.log(JSON.stringify({
        success: true, updated: false, reason, relation,
        local: { version: localVersion, sha: git.sha },
        remote: { version: remote.remoteVersion, sha: tipSha, tag: remote.remoteTag },
      }, null, 2));
    }
    return 0;
  }

  warn(`发现更新: ${reason}`);
  if (flags.check) {
    info('Dry-run 模式 — 未执行 pull。去掉 --check 以实际更新。');
    if (flags.json) {
      console.log(JSON.stringify({
        success: true, updated: false, dry_run: true, reason, relation,
        local: { version: localVersion, sha: git.sha },
        remote: { version: remote.remoteVersion, sha: tipSha, tag: remote.remoteTag },
      }, null, 2));
    }
    return 0;
  }

  // Safety: refuse to pull over dirty tree unless --force
  if (git.dirty && !flags.force) {
    err('工作区有未提交改动，拒绝自动 pull（避免覆盖本地修改）。');
    info('处理方式：');
    info('  1. 提交/暂存改动后重试');
    info('  2. 或 stash: git stash -u && ragctl update && git stash pop');
    info('  3. 确认可丢弃本地改动时: ragctl update --force');
    return 1;
  }

  // Fetch + pull
  step('git fetch origin');
  let r = runGit(['fetch', 'origin', '--tags', '--prune'], { allowFail: true });
  if (r.code !== 0) {
    err(`git fetch 失败 (exit ${r.code})`);
    if (r.stderr) console.error(r.stderr);
    return 1;
  }
  ok('fetch 完成');

  step(`git pull --ff-only origin ${branch}`);
  r = runGit(['pull', '--ff-only', 'origin', branch], { allowFail: true });
  if (r.code !== 0) {
    // ff-only may fail on diverged history — offer merge fallback only with --force
    if (flags.force) {
      warn('fast-forward 失败，--force 下尝试 merge pull…');
      r = runGit(['pull', '--no-rebase', 'origin', branch], { allowFail: true });
    }
    if (r.code !== 0) {
      err(`git pull 失败 (exit ${r.code})`);
      if (r.stderr) console.error(r.stderr);
      info('可能原因: 本地与远程分叉，或本地超前。手动处理: git status / git pull --rebase');
      return 1;
    }
  }
  ok('pull 完成');

  const newVersion = readLocalVersion();
  const newGit = getLocalGitInfo();
  ok(`更新后版本: v${newVersion} @ ${newGit.sha || '?'}`);

  // Optional: reinstall deps (safe incremental)
  if (!flags.noDeps) {
    step('增量重装依赖 (ragctl deps)');
    try {
      const depsCode = await cmdDeps();
      if (depsCode === 0) ok('依赖已同步');
      else warn(`deps 返回 ${depsCode} — 可稍后手动: ragctl deps`);
    } catch (e) {
      warn(`deps 失败: ${e.message}`);
    }
  } else {
    info('已跳过依赖重装 (--no-deps)');
  }

  // Re-register global wrapper so path stays correct after moves (cheap)
  try { await cmdInstall(); } catch {}

  // Optional restart
  if (flags.restart) {
    step('重启服务 (ragctl up --force)');
    try {
      await cmdUp(['--force', '--skip-check']);
    } catch (e) {
      warn(`重启失败: ${e.message} — 可手动: ragctl up --force`);
    }
  } else {
    info('提示: 若服务正在运行，建议重启以加载新代码: ragctl up --force');
    info('      MCP 代码变更需重启 Claude Code 才能生效。');
  }

  if (flags.json) {
    console.log(JSON.stringify({
      success: true,
      updated: true,
      reason,
      relation,
      before: { version: localVersion, sha: git.sha },
      after: { version: newVersion, sha: newGit.sha },
      remote: { version: remote.remoteVersion, sha: tipSha, tag: remote.remoteTag },
    }, null, 2));
  } else {
    console.log('');
    ok(`更新完成: v${localVersion} → v${newVersion}`);
  }
  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  CLI Entry Point
// ═══════════════════════════════════════════════════════════════════════

function showHelp() {
  const ver = readLocalVersion();
  console.log(`
${_c(C.BOLD, 'ragctl')} — RAG Knowledge Platform CLI  v${ver}

${_c(C.CYAN, '核心命令:')}
  ${_c(C.BOLD, 'setup')}            一键完整部署（自动安装 uv → Python 3.12 → 依赖 → 模型 → 配置）
  ${_c(C.BOLD, 'check')}            全面环境检查（显示缺失项 + 修复方案）
  ${_c(C.BOLD, 'deps')}             安装所有依赖（实时进度；backend 固定 Python 3.12）
  ${_c(C.BOLD, 'model')}            预下载 BGE-M3 嵌入模型 (~2.2GB)
          model --source modelscope   ⭐ 中国区推荐（阿里云 CDN，默认）
          model --source hf-mirror    HuggingFace 镜像 (hf-mirror.com)
          model --source huggingface  HuggingFace 直连（海外）
  ${_c(C.BOLD, 'mineru-model')}      预下载 MinerU Pipeline + VLM 模型 (OCR引擎，~5-7GB)
  ${_c(C.BOLD, 'version')}          显示本地/远程版本（VERSION + git SHA）
  ${_c(C.BOLD, 'update')}           对比 GitHub 最新版并拉取更新

${_c(C.CYAN, '服务管理（全部静默启动 · 无终端窗口）:')}
  up / start-all             启动全部服务（根据 --appmode 选择端口组）
  down / stop-all            停止全部服务
  start [svc]                启动指定服务 (backend|web|neo4j|all)
  stop  [svc]                停止指定服务
  restart [svc]              重启指定服务（自动 stop + start）
  status                     查看服务状态（默认同时显示 dev + prod）

${_c(C.CYAN, '日志:')}
  logs [svc]                 查看最近日志（默认 backend, 80 行）
  logs [svc] --tail          实时跟踪日志（Ctrl+C 退出）
  logs [svc] --lines N       指定行数

${_c(C.CYAN, '全局注册 / 桌面:')}
  install                    全局注册 ragctl → ~/.local/bin（任意目录可用）
  desktop / ui [--dev]       启动 Tauri 桌面控制台

${_c(C.CYAN, '清理缓存:')}
  clean                      清理 MinerU 解析产物（默认范围，安全）
  clean --dry-run            仅扫描，不删除
  clean --mineru             仅清理 backend/output/（PDF 解析 md/images/uploads）
  clean --logs               同时清理 backend/logs + web/logs
  clean --pycache            同时清理 __pycache__ / .pytest_cache
  clean --all                所有安全项（mineru+logs+pycache，不含模型）
  clean --model              含模型缓存（BGE-M3 ~4GB + MinerU ~2-5GB，需重新下载，需二次确认）
  clean --force / -y         跳过确认提示

${_c(C.CYAN, '备份 / 恢复 (跨平台 · 替代 scripts/backup.sh):')}
  backup [dest]             备份 KB文档 + ChromaDB + Neo4j图数据库
  backup --dry-run          仅扫描，不写入
  restore [src]             从指定备份恢复

${_c(C.CYAN, '经验冥想 (自动经验沉淀):')}
  meditation status [kb]   查看冥想状态（全局或按KB）
  meditation run [kb]      手动触发一次冥想运行
  meditation history [kb]  查看最近冥想运行历史
  meditation config <kb>   查看/设置 KB 冥想配置

${_c(C.CYAN, '示例:')}
  update --restart                     拉取后强制重启服务

${_c(C.CYAN, '选项 (-- 二级参数):')}
  ${_c(C.BOLD, '--appmode')} dev|prod    选择启动模式（默认: .env APP_MODE 或 dev）
           别名: --mode, -m
  ${_c(C.BOLD, '--port-backend')} N     覆盖后端端口
           别名: --backend-port
  ${_c(C.BOLD, '--port-web')} N          覆盖前端端口
           别名: --web-port
  ${_c(C.BOLD, '--host')} HOST           覆盖主机地址
  ${_c(C.BOLD, '--no-neo4j')}            跳过 Neo4j
  ${_c(C.BOLD, '--no-backend')}          跳过 Backend
  ${_c(C.BOLD, '--no-web')}              跳过 Web
  ${_c(C.BOLD, '--only')} SERVICE        仅操作指定服务
  ${_c(C.BOLD, '--force')} / ${_c(C.BOLD, '-f')}      强制（先停后启，用于 up/start；update 时覆盖脏工作区）
  ${_c(C.BOLD, '--timeout')} N           启动超时秒数（默认: backend=30, web=25）
  ${_c(C.BOLD, '--skip-check')}          跳过 pre-flight 检查

${_c(C.CYAN, '使用示例:')}
  ${_c(C.BOLD, 'ragctl up --appmode dev')}             # 以 dev 模式启动（8765+6789）
  ${_c(C.BOLD, 'ragctl up --appmode prod')}            # 以 prod 模式启动（8001+3000）
  ${_c(C.BOLD, 'ragctl up -m dev --force')}            # 强制重启 dev 模式
  ${_c(C.BOLD, 'ragctl up --no-neo4j')}                # 启动但不启动 Neo4j
  ${_c(C.BOLD, 'ragctl start backend --port-backend 9000')}  # 自定义端口启动 Backend
  ${_c(C.BOLD, 'ragctl down --appmode prod')}          # 停止 prod 模式服务
  ${_c(C.BOLD, 'ragctl status')}                       # 同时查看 dev + prod 状态
  ${_c(C.BOLD, 'ragctl status --appmode dev')}         # 仅查看 dev 状态
  ${_c(C.BOLD, 'ragctl restart web -m prod -f')}       # 强制重启 prod Web
  ${_c(C.BOLD, 'ragctl logs backend --tail --lines 100')} # 实时跟踪后端日志
  ${_c(C.BOLD, 'ragctl version')}                      # 对比本地/远程版本
  ${_c(C.BOLD, 'ragctl update --check')}               # 仅检查是否有新版本
  ${_c(C.BOLD, 'ragctl update --yes --restart')}       # 拉取最新并重启服务

${_c(C.GRAY, '端口对照:')}
${_c(C.GRAY, '  dev:  Backend=8765  Web=6789')}
${_c(C.GRAY, '  prod: Backend=8001  Web=3000')}
`);
}

// ── Meditation ────────────────────────────────────────────────────────

/** Backend base URL (dev:8765 / prod:8001, env/config overrides). Fixes getBackendUrl is not defined. */
function getBackendUrl() {
  const ports = getServicePorts();
  return `http://127.0.0.1:${ports.backend}`;
}

// ── SOUL ──────────────────────────────────────────────────────────────

/**
 * ragctl harness [omp|claude] [--model M] — 全局默认 harness(配置驱动, 写 backend/config.yml soul 段)
 * 无参 = 查看当前默认; 带参 = 设置(默认 omp)。
 */
async function cmdHarness(args) {
  const positional = args.filter(a => !a.startsWith('--'));
  const target = (positional[0] || '').toLowerCase();
  const modelFlagIdx = args.indexOf('--model');
  const model = modelFlagIdx >= 0 && args[modelFlagIdx + 1] ? args[modelFlagIdx + 1] : '';

  const backendCfgPath = path.join(BACKEND_DIR, 'config.yml');
  const cfg = readYaml(backendCfgPath);
  const current = (cfg.soul && cfg.soul.default_harness) || 'omp';

  if (!target) {
    header('全局默认 harness(SOUL 训练/冥想引擎)');
    console.log(`  当前默认: ${_c(C.CYAN, current)}`);
    console.log(`  默认模型: ${_c(C.CYAN, (cfg.soul && cfg.soul.default_model) || '(引擎默认)')}`);
    console.log(`  配置来源: ${backendCfgPath}`);
    console.log('');
    console.log(`  设置: ragctl harness <omp|claude> [--model M]`);
    console.log(`  单人格覆盖: ragctl soul harness <soul_kb_id> <omp|claude> [--model M]`);
    console.log(`  说明: 每个 SOUL 的 meditation config 可单独指定 harness; 未指定时回退此全局默认。`);
    return 0;
  }

  if (!['omp', 'claude'].includes(target)) {
    err(`未知 harness: ${target}(可选 omp|claude)`);
    return 1;
  }

  // 可用性校验(安装但未配置 key 的 claude 会警告)
  if (target === 'claude') {
    try {
      const r = execSync('claude --version', { stdio: ['ignore', 'pipe', 'pipe'], timeout: 15000 });
      const hasKey = !!process.env.ANTHROPIC_API_KEY;
      if (!hasKey) warn('claude CLI 已安装但 ANTHROPIC_API_KEY 未设置 — 调用将失败直到配置密钥');
      else ok(`claude 可用: ${r.toString().trim()}`);
    } catch {
      warn('claude CLI 未安装或不在 PATH — 设置仍会写入, 但训练会回退/失败');
    }
  } else {
    try {
      const r = execSync('omp --version', { stdio: ['ignore', 'pipe', 'pipe'], timeout: 15000 });
      ok(`omp 可用: ${r.toString().trim()}`);
    } catch {
      warn('omp CLI 未安装或不在 PATH — 训练将不可用');
    }
  }

  if (!cfg.soul) cfg.soul = {};
  cfg.soul.default_harness = target;
  if (args.includes('--model')) cfg.soul.default_model = model;

  try {
    const body = yaml.dump(cfg, { indent: 2, lineWidth: -1, noRefs: true, sortKeys: false });
    fs.writeFileSync(backendCfgPath, body, 'utf8');
  } catch (e) {
    err(`写入配置失败: ${e.message}`);
    return 1;
  }
  ok(`全局默认 harness → ${target}${model ? ` (model=${model})` : ''}`);
  info('后端重启后生效(ragctl restart backend); 已创建的 SOUL 未显式指定 harness 时自动回退此默认');
  return 0;
}


async function cmdSoul(args) {
  const [sub, ...rest] = args;
  const backendUrl = getBackendUrl();

  async function apiGet(path) {
    const res = await fetch(`${backendUrl}${path}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return res.json();
  }
  async function apiPost(path, body) {
    const res = await fetch(`${backendUrl}${path}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return res.json();
  }
  async function apiPut(path, body) {
    const res = await fetch(`${backendUrl}${path}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return res.json();
  }
  async function apiDelete(path) {
    const res = await fetch(`${backendUrl}${path}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return res.json();
  }

  // 异步任务轮询: 提交后打印进度(训练/审批长任务), 完成后返回 result
  async function pollTask(taskId, label) {
    let lastLine = '';
    for (;;) {
      await new Promise(r => setTimeout(r, 10000));
      let view;
      try {
        view = await apiGet(`/api/v1/soul/tasks/${taskId}`);
      } catch { continue; }
      const p = view.progress || {};
      let line;
      if (p.phase === 'learn') {
        line = `  ⏳ ${label} 学习轮 ${p.round ?? 1}/${p.rounds ?? 1} ｜ 问题 ${p.questions ?? 0} ｜ 记忆 ${p.memories ?? 0} ｜ 文档 ${p.docs_processed ?? 0}`;
      } else if (p.phase === 'reward') {
        line = `  🎯 ${label} 第 ${p.round}/${p.rounds} 轮评价得分 ${p.reward?.toFixed?.(2) ?? p.reward} ｜ 认知草稿 ${p.drafts_created ?? 0}`;
      } else if (p.processed !== undefined) {
        line = `  ⏳ ${label} 审批 ${p.processed}/${p.total} (批准 ${p.approved ?? 0} / 驳回 ${p.rejected ?? 0})`;
      } else {
        line = `  ⏳ ${label} 执行中…(elapsed ${view.elapsed_seconds ?? '?'}s)`;
      }
      if (line !== lastLine) { console.log(line); lastLine = line; }
      if (view.status === 'done') return view.result || {};
      if (view.status === 'error') throw new Error(view.error || `${label} 失败`);
    }
  }

  const enc = encodeURIComponent;

  // 取 flag 值: 支持 `--flag value` 与 `--flag=value` 两种写法
  function flagVal(name) {
    const eq = args.find(a => a.startsWith(`${name}=`));
    if (eq) return eq.split('=').slice(1).join('=');
    const idx = args.indexOf(name);
    return idx >= 0 && idx + 1 < args.length ? args[idx + 1] : '';
  }
  const flagOn = (name) => args.includes(name);

  switch (sub) {
    case 'distill': case 'distill-persona': {
      // ragctl soul distill <dot-skill产出目录> [--name soul-xxx] [--scope kb1,kb2]
      //   [--labels a,b] [--harness omp|claude] [--types t1,t2] [--values v.md] [--mem m.md]
      // 补天(dot-skill/nuwa 种子)蒸馏产物 → SOUL 人格一键创建(先天种子)
      const personaDir = rest.find(a => !a.startsWith('--'));
      if (!personaDir) {
        console.log('用法: ragctl soul distill <补天种子目录> [--name soul-xxx] [--scope kb1,kb2] [--labels a,b] [--harness omp|claude] [--values values.md] [--mem mem.md]');
        console.log('  输入目录需含 meta.json + persona.md + work.md(dot-skill 原生 / nuwa-skill 经 butian nuwa_to_seed.py 转换)');
        console.log('  --values: 可选, 价值观蒸馏文件(融合进 values.md 宪法层, 创建时一次定型)');
        console.log('  --mem:     可选, 记忆约定蒸馏文件(融合进 memory-conventions.md)');
        console.log('  示例: ragctl soul distill .claude/skills/nuwa-skill/examples/munger-perspective/soul-seed --scope AI-ML-Research --values soul-seed/values.md');
        break;
      }
      const fsD = require('fs');
      const pathD = require('path');
      const dir = pathD.resolve(personaDir);
      const metaPath = pathD.join(dir, 'meta.json');
      const personaPath = pathD.join(dir, 'persona.md');
      const workPath = pathD.join(dir, 'work.md');
      if (!fsD.existsSync(metaPath)) { err(`meta.json 不存在: ${metaPath}`); break; }
      let meta = {};
      try { meta = JSON.parse(fsD.readFileSync(metaPath, 'utf8')); } catch (e) { err(`meta.json 解析失败: ${e.message}`); break; }

      const slug = meta.slug || pathD.basename(dir);
      const name = flagVal('--name') || (slug.startsWith('soul-') ? slug : `soul-${slug}`);
      const displayName = meta.name || name;
      const scope = flagVal('--scope');
      const labels = flagVal('--labels');
      const types = flagVal('--types');
      const harness = flagVal('--harness');

      // domain_labels 默认从补天 meta 提炼(性格标签 + 印象)
      let domainLabels = labels ? labels.split(',').map(s => s.trim()) : [];
      if (!domainLabels.length) {
        const tags = (meta.tags && meta.tags.personality) || [];
        domainLabels = tags.slice(0, 3);
        if (meta.impression) domainLabels.push(String(meta.impression).slice(0, 12));
      }
      const taskTypes = types ? types.split(',').map(s => s.trim()) : ['知识答疑'];

      // 读取 SOUL 模板(与 soul_init 同源: storage/tree-file-system/soul-template/)
      const tplDir = pathD.join(PROJECT_ROOT, 'storage', 'tree-file-system', 'soul-template');
      function tpl(doc) {
        const p = pathD.join(tplDir, doc);
        if (!fsD.existsSync(p)) { err(`模板缺失: ${p}`); return null; }
        return fsD.readFileSync(p, 'utf8');
      }
      const tplDef = tpl('soul-definition.md');
      const tplThink = tpl('thinking-style.md');
      const tplValues = tpl('values.md');
      const tplMem = tpl('memory-conventions.md');
      if (tplDef === null || tplThink === null || tplValues === null || tplMem === null) break;

      const personaText = fsD.existsSync(personaPath) ? fsD.readFileSync(personaPath, 'utf8') : '';
      const workText = fsD.existsSync(workPath) ? fsD.readFileSync(workPath, 'utf8') : '';
      if (!personaText && !workText) { err('persona.md 与 work.md 均为空 — 无法蒸馏'); break; }

      // 可选宪法层增强(补天 nuwa 产物): --values 价值观 / --mem 记忆约定
      let valuesText = tplValues, memText = tplMem;
      const valuesPath = flagVal('--values');
      const memPath = flagVal('--mem');
      if (valuesPath) {
        if (fsD.existsSync(valuesPath)) {
          valuesText = `${tplValues}\n\n---\n\n# 补天蒸馏价值观: ${displayName}\n\n${fsD.readFileSync(valuesPath, 'utf8')}\n`;
        } else { warn(`--values 文件不存在: ${valuesPath}(保持模板 values.md)`); }
      }
      if (memPath) {
        if (fsD.existsSync(memPath)) {
          memText = `${tplMem}\n\n---\n\n# 补天蒸馏记忆约定: ${displayName}\n\n${fsD.readFileSync(memPath, 'utf8')}\n`;
        } else { warn(`--mem 文件不存在: ${memPath}(保持模板 memory-conventions.md)`); }
      }

      // 融合: 模板结构(profile/language-style 解析依赖) + 补天人格原文(进化基础)
      const soulDef = `${tplDef}\n\n---\n\n# 补天蒸馏人格: ${displayName}\n\n${personaText || '(无 persona.md, 仅使用模板人格)'}\n`;
      const thinkStyle = `${tplThink}\n\n---\n\n# 补天蒸馏工作方式: ${displayName}\n\n${workText || '(无 work.md)'}\n`;

      // 1) 建库(web 层)
      const portsD = getServicePorts();
      const webUrl = `http://127.0.0.1:${portsD.web}`;
      const kbRes = await fetch(`${webUrl}/api/kb/create`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description: `补天蒸馏人格: ${displayName} — ${meta.impression || ''}`.slice(0, 300) }),
      }).catch(e => ({ _error: e.message }));
      const kbJson = kbRes._error ? kbRes : await kbRes.json();
      if (kbRes._error || !(kbJson && kbJson.knowledgeBase)) {
        err(`建库失败: ${kbRes._error || JSON.stringify(kbJson).slice(0, 200)}`);
        break;
      }
      const kbId = kbJson.knowledgeBase.id;
      ok(`知识库已创建: ${name} (${kbId})`);

      // 2) 写 4 个人格文档(web 层, 原子)
      const docs = [
        ['soul-definition.md', soulDef],
        ['thinking-style.md', thinkStyle],
        ['values.md', valuesText],
        ['memory-conventions.md', memText],
      ];
      for (const [docName, content] of docs) {
        const r = await fetch(`${webUrl}/api/kb/documents/create`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ kbId, name: docName, content }),
        });
        if (!r.ok) { warn(`文档创建失败 ${docName}: ${r.status}`); }
      }
      ok('4 个人格文档已写入(模板结构 + 补天人格内容)');

      // 3) bootstrap(后端: soul-config + profile-summary + meditation config)
      const boot = await apiPost('/api/v1/soul/bootstrap', {
        soul_kb_id: kbId,
        kb_scope: scope ? scope.split(',').map(s => s.trim()) : ['*'],
        domain_labels: domainLabels,
        supported_task_types: taskTypes,
        harness: harness || '',
        model: '',
      });
      if (!boot.success) { warn(`bootstrap 警告: ${JSON.stringify(boot).slice(0, 200)}`); }
      else ok(`bootstrap 完成: profile=${boot.profile_summary_generated} meditation=${boot.meditation_config_created}`);

      // 4) 索引 4 文档
      for (const docName of ['soul-definition.md', 'thinking-style.md', 'values.md', 'memory-conventions.md']) {
        try {
          await apiPost('/api/v1/search/index-document', { kb_id: kbId, doc_path: docName });
        } catch (e) { warn(`索引失败 ${docName}: ${e.message}`); }
      }
      ok('4 文档已索引(60s 内可检索)');

      console.log(`\n🧠 补天蒸馏完成 → SOUL 人格: ${name}`);
      console.log('════════════════════════════════════');
      console.log(`  kb_id:    ${kbId}`);
      console.log(`  labels:   ${domainLabels.join(', ') || '—'}`);
      console.log(`  scope:    ${scope || '["*"] 全部知识库'}`);
      console.log(`  harness:  ${harness || '(全局默认)'}`);
      console.log('');
      console.log(`  下一步 — 后天好奇心训练(先天种子进化):`);
      console.log(`    ragctl soul learn-all ${name} --rounds 2`);
      console.log(`    ragctl soul review ${name} --action list   # 审查记忆草稿`);
      console.log(`    ragctl soul ask "问题" --soul ${name}      # 人格增强问答`);
      break;
    }
    case 'list': {
      const souls = await apiGet('/api/v1/soul/list');
      console.log('\n🤖 SOUL Personas');
      console.log('════════════════');
      if (!souls.length) { console.log('  (空 — 尚无 SOUL,用 ragctl soul init 创建)'); break; }
      for (const s of souls) {
        const status = s._status || {};
        console.log(`  ${s.is_template ? '📄' : '🧠'} ${s.name}  [scope: ${(s.kb_scope || []).join(',') || '空(仅问答)'}]`);
        console.log(`      labels: ${(s.domain_labels || []).join(', ') || '—'} | task_types: ${(s.supported_task_types || []).join(', ') || '—'} | weight: ${s.route_weight}`);
      }
      break;
    }
    case 'status': {
      const kbId = rest[0];
      if (!kbId) { console.log('用法: ragctl soul status <soul_kb_id>'); break; }
      const st = await apiGet(`/api/v1/soul/${enc(kbId)}/status?summary_window=30`);
      console.log(`\n🧠 ${kbId} 学习指标`);
      console.log('════════════════════');
      console.log(`  记忆: ${st.total_memories} | 待审草稿: ${st.drafts_pending_review} | 缺口: ${st.total_gaps}`);
      console.log(`  判官分歧: ${st.judge_divergence_count} | stale 记忆: ${st.stale_memory_count} | training_stale: ${st.training_stale}`);
      console.log(`  掌握: ${st.mastery?.question_count ?? 0} 问题, 均分 ${st.mastery?.avg_score ?? 0}`);
      console.log(`  成本: $${st.estimated_cost_usd?.toFixed?.(4) ?? st.estimated_cost_usd} | 路由成本: $${st.route_cost_usd}`);
      if (st.recent_learned_docs?.length) {
        console.log(`  最近学习:`);
        for (const d of st.recent_learned_docs.slice(0, 5)) console.log(`    • ${d.doc_path} (score ${d.score})`);
      }
      break;
    }
    case 'init': case 'create': {
      // ragctl soul init <name> --scope kb1,kb2 --labels 材料,催化 --types 文献综述 --harness omp
      const name = rest[0];
      if (!name) { console.log('用法: ragctl soul init <soul_name> [--scope kb1,kb2] [--labels a,b] [--types t1,t2] [--harness omp|claude]'); break; }
      const scope = flagVal('--scope');
      const labels = flagVal('--labels');
      const types = flagVal('--types');
      const harness = flagVal('--harness');
      const full = name.startsWith('soul-') ? name : `soul-${name}`;
      // 后端 /init 兼容入口(实际编排在 kb-mcp);此处提示 MCP 路径
      const res = await apiPost('/api/v1/soul/init', {
        soul_name: full,
        kb_scope: scope ? scope.split(',').map(s => s.trim()) : [],
        domain_labels: labels ? labels.split(',').map(s => s.trim()) : [],
        supported_task_types: types ? types.split(',').map(s => s.trim()) : [],
        harness,
        model: '',
      }).catch(e => ({ _error: e.message }));
      if (res._error) {
        console.log(`\n⚠ 后端 /init 为兼容入口: ${res._error}`);
        console.log('   完整创建(模板复制+profile+索引)请用 MCP 工具 soul_init 或 Web SOUL 页面');
      } else {
        console.log(`\n🧠 ${full} 初始化请求已提交${harness ? ` [harness=${harness}]` : ''}:`, JSON.stringify(res).slice(0, 200));
      }
      break;
    }
    case 'learn': {
      const posArgs = rest.filter(a => !a.startsWith('--'));
      const kbId = posArgs[0];
      const docs = flagVal('--docs');
      if (!kbId || !docs) { console.log('用法: ragctl soul learn <soul_kb_id> --docs kb/doc1,kb/doc2 [--limit 6] [--rounds N]'); break; }
      const limit = parseInt(flagVal('--limit') || '6');
      const rounds = parseInt(flagVal('--rounds') || '1');
      console.log(`\n🧠 ${kbId} 训练已提交(rounds=${rounds}, 异步执行)…`);
      const res = await apiPost(`/api/v1/soul/${enc(kbId)}/learn`, {
        doc_paths: docs.split(',').map(s => s.trim()), limit, rounds, async_mode: true,
      });
      if (res.task_id) {
        const result = await pollTask(res.task_id, `${kbId} 训练`);
        console.log('  训练完成:', JSON.stringify(result.report || result).slice(0, 400));
      } else {
        console.log('  结果:', JSON.stringify(res.report || res).slice(0, 300));
      }
      break;
    }
    case 'learn-all': case 'train-all': {
      // 过滤 flag 参数: kbId 是第一个非 -- 开头的参数
      const posArgs = rest.filter(a => !a.startsWith('--'));
      const kbId = posArgs[0] || '';
      const dry = flagOn('--dry-run');
      const rounds = parseInt(flagVal('--rounds') || '1');
      const path = kbId ? `/api/v1/soul/${enc(kbId)}/learn-all` : '/api/v1/soul/learn-all';
      if (dry) {
        const res = await apiPost(path, { max_docs: 20, dry_run: true, rounds });
        console.log(`\n🌱 全库自举预估(${kbId || '全部人格'}, rounds=${rounds}):`);
        const r = res.report || {};
        if (r.estimated_llm_calls !== undefined) {
          console.log(`  预估: ${r.estimated_llm_calls} LLM 调用 | 唯一文档: ${r.unique_docs} | 重复: ${r.duplicate_docs} | 跨人格重叠: ${r.cross_soul_overlap_pct}%`);
          for (const p of r.per_soul_breakdown || []) console.log(`    • ${p.soul_kb_id.slice(0, 20)}: ${p.scope_docs} 文档`);
        } else {
          console.log(JSON.stringify(r, null, 2).slice(0, 400));
        }
        break;
      }
      console.log(`\n🌱 全库自举已提交(${kbId || '全部人格'}, rounds=${rounds}, 异步执行)…`);
      const res = await apiPost(path, { max_docs: 20, dry_run: false, rounds, async_mode: true });
      if (res.task_id) {
        const result = await pollTask(res.task_id, '全库自举');
        const r = result.report || result;
        console.log(`  完成: ${r.total_docs ?? ''} 文档 / ${r.total_questions ?? ''} 问题 / ${r.total_memories ?? ''} 记忆`);
        console.log(JSON.stringify(r, null, 2).slice(0, 400));
      } else {
        console.log('  结果:', JSON.stringify(res.report || res).slice(0, 300));
      }
      break;
    }
    case 'train-rl': {
      // ragctl soul train-rl <soul_kb_id> [--rounds N] — RL 强化训练(好奇心×评价×策略更新)
      const kbId = rest[0];
      if (!kbId) { console.log('用法: ragctl soul train-rl <soul_kb_id> [--rounds N]'); break; }
      const rounds = parseInt(flagVal('--rounds') || '1');
      console.log(`\n🤖 RL 强化训练已提交(${kbId}, rounds=${rounds}): 好奇心探索 → 评价Agent打分 → 认知草稿策略更新…`);
      const res = await apiPost(`/api/v1/soul/${enc(kbId)}/train-rl`, { rounds, async_mode: true });
      if (res.task_id) {
        const result = await pollTask(res.task_id, `${kbId} RL`);
        console.log('  RL 训练完成:');
        for (const r of (result.per_round || [])) {
          console.log(`    第 ${r.round} 轮: reward=${r.reward?.toFixed?.(2) ?? r.reward} (id=${r.scores?.identity} va=${r.scores?.values} th=${r.scores?.thinking} la=${r.scores?.language}) 认知草稿=${r.cognition_drafts_created?.length ?? 0} 学习: ${r.learn?.docs_processed ?? 0} 文档`);
        }
        console.log(`  进化曲线: ${result.reward_history_path || ''}`);
        console.log('  下一步: ragctl soul review-cognition <soul_kb_id> 审批认知草稿 → 合并入人格定义');
      } else {
        console.log('  结果:', JSON.stringify(res).slice(0, 300));
      }
      break;
    }
    case 'evaluate': {
      // ragctl soul evaluate <soul_kb_id> — 评价 Agent 四维打分(RL 奖励信号)
      const kbId = rest[0];
      if (!kbId) { console.log('用法: ragctl soul evaluate <soul_kb_id>'); break; }
      console.log(`\n📊 评价 Agent 评分中(${kbId})…`);
      const res = await apiPost(`/api/v1/soul/${enc(kbId)}/evaluate`, {});
      console.log(`  overall: ${res.overall}`);
      console.log(`  identity: ${res.identity} | values: ${res.values} | thinking: ${res.thinking} | language: ${res.language}`);
      break;
    }
    case 'review-cognition': {
      // ragctl soul review-cognition <soul_kb_id> [--action list|approve|reject] [--draft id] [--all]
      const kbId = rest[0];
      if (!kbId) { console.log('用法: ragctl soul review-cognition <soul_kb_id> [--action approve|reject] [--draft id] [--all 批量]'); break; }
      const action = flagVal('--action') || 'list';
      const draftId = flagVal('--draft');
      const all = flagOn('--all');
      if (action === 'list') {
        const res = await apiPost(`/api/v1/soul/${enc(kbId)}/review-drafts`, { action: 'list', type: 'cognition' });
        console.log(`\n🧬 ${kbId} 认知草稿(${res.drafts?.length || 0}) — RL 策略更新建议:`);
        for (const d of (res.drafts || []).slice(0, 10)) {
          console.log(`  • ${d.draft_id}  reward=${d.scores?.reward ?? '-'} | ${d.answer_text?.split('\n')[0]?.slice(0, 60)}`);
        }
      } else if (action === 'approve' && all && !draftId) {
        const list = await apiPost(`/api/v1/soul/${enc(kbId)}/review-drafts`, { action: 'list', type: 'cognition' });
        const ids = (list.drafts || []).map(d => d.draft_id);
        if (!ids.length) { console.log('\n无待审批认知草稿'); break; }
        console.log(`\n✅ 批量审批 ${ids.length} 条认知草稿(异步)…`);
        const res = await apiPost(`/api/v1/soul/${enc(kbId)}/review-drafts`, {
          action: 'approve', type: 'cognition', draft_ids: ids, async_mode: true,
        });
        if (res.task_id) {
          const result = await pollTask(res.task_id, '认知审批');
          console.log('  审批完成:', JSON.stringify(result.results || result).slice(0, 300));
        }
      } else {
        const res = await apiPost(`/api/v1/soul/${enc(kbId)}/review-drafts`, {
          action, type: 'cognition', draft_id: draftId, async_mode: false,
        });
        console.log(`\n✅ ${action}:`, JSON.stringify(res).slice(0, 250));
      }
      break;
    }
    case 'harness': {
      // ragctl soul harness <soul_kb_id> <omp|claude> [--model M] — 指定单个 SOUL 的训练引擎
      const kbId = rest[0];
      const harness = rest[1];
      if (!kbId || !harness) {
        console.log('用法: ragctl soul harness <soul_kb_id> <omp|claude> [--model M]');
        console.log('  查看: ragctl soul harness <soul_kb_id>  (不带引擎参数时显示当前配置)');
        break;
      }
      if (!['omp', 'claude'].includes(harness)) { console.log(`❌ 未知 harness: ${harness}(可选 omp|claude)`); break; }
      const cfgRes = await apiPut('/api/v1/meditation/config', {
        kb_id: kbId,
        config: { harness, model: flagVal('--model'), meditation_mode: 'soul' },
      });
      if (cfgRes.success) {
        console.log(`\n⚙️ ${kbId} harness → ${cfgRes.config?.harness}${cfgRes.config?.model ? ` (model=${cfgRes.config.model})` : ''}`);
      } else {
        console.log(`❌ 设置失败: ${cfgRes.error || JSON.stringify(cfgRes)}`);
      }
      break;
    }
    case 'ask': {
      // ragctl soul ask <query> [--soul kb_id] [--type 文献综述] [--goal 研究] [--qdcvr]
      const query = rest.join(' ');
      if (!query) { console.log('用法: ragctl soul ask <query> [--soul kb_id] [--type 任务类型] [--goal 目标] [--qdcvr 先检索后人格]'); break; }
      const soulKbId = flagVal('--soul');
      const taskType = flagVal('--type');
      const taskGoal = flagVal('--goal');
      const qdcvr = flagOn('--qdcvr');
      console.log(`\n🤖 人格问答中(约 1-2 分钟)…${soulKbId ? ` [人格: ${soulKbId}]` : ' [自动路由]'}${qdcvr ? ' [QDCVR 先检索后人格]' : ''}`);
      const endpoint = qdcvr ? '/api/v1/soul/qdcvr-ask' : '/api/v1/soul/ask';
      const res = await apiPost(endpoint, {
        query, soul_kb_id: soulKbId, task_type: taskType, task_goal: taskGoal,
        top_k: qdcvr ? 5 : undefined,
      });
      console.log('════════════════════════');
      console.log(res.answer || JSON.stringify(res));
      console.log('════════════════════════');
      if (res.selected_soul) console.log(`路由 → ${res.selected_soul} (conf ${res.route_confidence})`);
      if (res.pas_score !== undefined && res.pas_score !== null) console.log(`PAS: ${res.pas_score}`);
      if (res.evidence_count !== undefined) console.log(`证据注入: ${res.evidence_count} 条(先检索后人格)`);
      if (res.citations?.length) {
        console.log(`引用(${res.citations.length}):`);
        for (const c of res.citations.slice(0, 5)) console.log(`  • ${c.path} (${c.score?.toFixed?.(3) ?? c.score})`);
      }
      break;
    }
    case 'router': {
      const query = rest.join(' ');
      if (!query) { console.log('用法: ragctl soul router <query> [--type 任务类型]'); break; }
      const taskType = flagVal('--type');
      const res = await apiPost('/api/v1/soul/router', { query, task_type: taskType });
      console.log(`\n🧭 路由决策: ${res.route_uncertain ? '不确定(候选如下)' : `→ ${res.top1} (conf ${res.route_confidence})`}`);
      for (const c of (res.ranked || []).slice(0, 5)) {
        console.log(`  • ${c.kb_id}  score=${c.score}  ${c.reason || ''}`);
      }
      break;
    }
    case 'review': {
      const kbId = rest[0];
      if (!kbId) { console.log('用法: ragctl soul review <soul_kb_id> [--action list|approve|reject] [--draft id]'); break; }
      const action = flagVal('--action') || 'list';
      const draftId = flagVal('--draft');
      const res = await apiPost(`/api/v1/soul/${enc(kbId)}/review-drafts`, {
        action, type: 'memory', draft_id: draftId,
      });
      if (action === 'list') {
        console.log(`\n📋 ${kbId} 记忆草稿(${res.drafts?.length || 0}):`);
        for (const d of (res.drafts || []).slice(0, 10)) {
          const s = d.scores || {};
          console.log(`  • ${d.draft_id}  G${s.groundedness ?? '-'} C${s.completeness ?? '-'} C${s.coherence ?? '-'} I${s.info_gain ?? '-'} | ${d.question?.slice(0, 50)}`);
        }
      } else {
        console.log(`\n✅ ${action}:`, JSON.stringify(res).slice(0, 200));
      }
      break;
    }
    case 'reflect': {
      const kbId = rest[0];
      if (!kbId) { console.log('用法: ragctl soul reflect <soul_kb_id>'); break; }
      const res = await apiPost(`/api/v1/soul/${enc(kbId)}/reflect`, {});
      console.log(`\n🔍 反思完成: drift=${res.drift_detected} | ${res.report_path || ''}`);
      break;
    }
    case 'export': {
      const kbId = rest[0];
      if (!kbId) { console.log('用法: ragctl soul export <soul_kb_id> [--min-score 4]'); break; }
      const minScore = parseFloat(flagVal('--min-score') || '4');
      const res = await apiPost(`/api/v1/soul/${enc(kbId)}/export`, { min_score: minScore, limit: 1000 });
      console.log(`\n📤 导出: ${res.record_count || 0} 条 → ${res.export_path || ''}`);
      break;
    }
    case 'distill-files': {
      // ragctl soul distill-files <name> <file1,file2,...> [--req R] [--scope k1,k2]
      const name = rest[0];
      const filesArg = rest[1];
      if (!name || !filesArg) {
        console.log('用法: ragctl soul distill-files <name> <file1,file2,...> [--req "需求"] [--scope k1,k2] [--labels a,b]');
        console.log('  支持类型: md/txt/json(对话)/eml/mbox/xlsx/docx/pdf/图片/pptx — 批量逗号分隔');
        break;
      }
      const fs = require('fs');
      const path = require('path');
      const paths = filesArg.split(',').map(x => x.trim()).filter(x => fs.existsSync(x));
      if (!paths.length) { console.log('❌ 无有效文件路径'); break; }
      console.log(`\n🎭 文件补天蒸馏中(${name}, ${paths.length} 个文件)…`);
      const form = new FormData();
      form.append('name', name);
      form.append('kb_scope', flagVal('--scope') || '*');
      form.append('domain_labels', flagVal('--labels') || '');
      form.append('personality_req', flagVal('--req') || '');
      for (const fp of paths) {
        const buf = fs.readFileSync(fp);
        form.append('files', new Blob([buf]), path.basename(fp));
      }
      const res = await fetch(`${backendUrl}/api/v1/soul/distill-files`, { method: 'POST', body: form });
      const js = await res.json();
      if (js.task_id) {
        const result = await pollTask(js.task_id, `${name} 文件蒸馏`);
        console.log('  蒸馏完成:', JSON.stringify(result).slice(0, 300));
      } else {
        console.log('  结果:', JSON.stringify(js).slice(0, 300));
      }
      break;
    }
    case 'task': {
      // ragctl soul task <pause|resume|status> <task_id>
      const sub = rest[0];
      const taskId = rest[1];
      if (!sub || !taskId) { console.log('用法: ragctl soul task <pause|resume|status> <task_id>'); break; }
      if (sub === 'pause' || sub === 'resume') {
        const res = await apiPost(`/api/v1/soul/tasks/${enc(taskId)}/${sub}`, {});
        console.log(`\n⏯ 任务 ${sub}: ${res.status || res.detail || JSON.stringify(res)}`);
      } else {
        const res = await apiGet(`/api/v1/soul/tasks/${enc(taskId)}`);
        console.log(`\n📊 任务 ${taskId}: status=${res.status}`);
        if (res.progress) console.log('  progress:', JSON.stringify(res.progress).slice(0, 200));
        if (res.result) console.log('  result:', JSON.stringify(res.result).slice(0, 300));
      }
      break;
    }
    case 'training': {
      // ragctl soul training [soul_kb_id] [--limit N] [--run <run_id>]
      const kbId = rest[0] || '';
      const runId = flagVal('--run');
      if (runId) {
        const res = await apiGet(`/api/v1/soul/training/runs/${enc(runId)}`);
        console.log(`\n📈 训练运行 ${runId}: status=${res.run?.status} kind=${res.run?.kind} reward=${res.run?.reward}`);
        for (const e of (res.events || []).slice(0, 20)) {
          const p = e.payload || {};
          console.log(`  [${e.ts.slice(11, 19)}] ${e.phase}: ${JSON.stringify(p).slice(0, 120)}`);
        }
        break;
      }
      const limit = parseInt(flagVal('--limit') || '20');
      const res = await apiGet(`/api/v1/soul/training/history?soul_kb_id=${enc(kbId)}&limit=${limit}`);
      console.log(`\n📚 训练历史(${kbId || '全部'}): ${res.count} 条`);
      for (const r of (res.runs || [])) {
        const dur = r.finished_at ? `${(new Date(r.finished_at) - new Date(r.started_at)) / 1000}s` : '运行中';
        console.log(`  • ${r.id.slice(0, 18)} ${r.kind} ${r.status} | Q${r.questions} M${r.memories} D${r.docs} $${r.cost_usd ?? 0}${r.reward != null ? ' reward=' + r.reward : ''} | ${dur}`);
      }
      break;
    }
    case 'distill-text': {
      // ragctl soul distill-text <name> --req "人格需求" --material "源材料" [--scope k1,k2] [--labels a,b]
      const name = rest[0];
      const req = flagVal('--req');
      const material = flagVal('--material');
      if (!name || (!req && !material)) {
        console.log('用法: ragctl soul distill-text <name> --req "人格需求" --material "聊天记录/描述" [--scope k1,k2] [--labels a,b] [--harness omp]');
        break;
      }
      console.log(`\n🎭 补天蒸馏中(${name})… LLM 提取人格画像 → 建库+4文档+索引(异步)`);
      const res = await apiPost('/api/v1/soul/distill', {
        name, personality_req: req, source_material: material,
        kb_scope: flagVal('--scope') ? flagVal('--scope').split(',').map(x => x.trim()) : ['*'],
        domain_labels: flagVal('--labels') ? flagVal('--labels').split(',').map(x => x.trim()) : [],
        harness: flagVal('--harness') || '',
        async_mode: true,
      });
      if (res.task_id) {
        const result = await pollTask(res.task_id, `${name} 蒸馏`);
        console.log('  蒸馏完成:', JSON.stringify(result).slice(0, 300));
      } else {
        console.log('  结果:', JSON.stringify(res).slice(0, 300));
      }
      break;
    }
    case 'delete': {
      const kbId = rest[0];
      if (!kbId) { console.log('用法: ragctl soul delete <soul_kb_id>'); break; }
      const res = await apiDelete(`/api/v1/soul/${enc(kbId)}`);
      console.log(`\n🗑 删除请求已提交: checkpoint=${res.checkpoint_saved || '—'} (完整删除需经 kb-mcp soul_delete 或 Web)`);
      break;
    }
    case 'checkpoint': {
      const kbId = rest[0];
      if (!kbId) { console.log('用法: ragctl soul checkpoint <soul_kb_id>'); break; }
      console.log(`\n📸 创建检查点中(${kbId})…`);
      const res = await apiPost(`/api/v1/soul/${enc(kbId)}/checkpoint`, {});
      console.log(`  检查点: ${res.checkpoint_id || ''} | 快照文件: ${res.snapshot_path || ''}`);
      console.log(`  hash: ${res.config_hash || ''}`);
      break;
    }
    default:
      console.log(`\n🤖 SOUL 人格管理 — 用法:`);
      console.log('  ragctl soul list                                   列出全部人格');
      console.log('  ragctl soul distill <dot-skill目录> [--scope k1,k2]  补天蒸馏产物→SOUL(先天种子)');
      console.log('  ragctl soul status <soul_kb_id>                    人格学习指标');
      console.log('  ragctl soul init <name> [--scope k1,k2] [--labels a,b] [--harness omp|claude]  创建人格(后端兼容入口)');
      console.log('  ragctl soul learn <soul_kb_id> --docs=kb/f1,kb/f2 [--rounds N]  训练指定文档(固定轮数)');
      console.log('  ragctl soul learn-all [soul_kb_id] [--dry-run] [--rounds N]   全库自举(增量, 固定轮数, 异步+进度)');
      console.log('  ragctl soul train-rl <soul_kb_id> [--rounds N]   RL强化训练(好奇心×评价Agent×策略更新, 异步+进度)');
      console.log('  ragctl soul evaluate <soul_kb_id>               评价Agent四维评分(RL奖励信号)');
      console.log('  ragctl soul review-cognition <soul_kb_id> [--action approve] [--all]  认知草稿审批(RL策略落地)');
      console.log('  ragctl soul task <pause|resume|status> <task_id>      任务暂停/继续/状态');
      console.log('  ragctl soul training [soul_kb_id] [--run run_id]      训练历史(SQLite)');
      console.log('  ragctl soul distill-text <name> --req R --material M   文本补天蒸馏创建');
      console.log('  ragctl soul distill-files <name> <f1,f2,...> [--req R]  文件批量蒸馏创建');
      console.log('  ragctl soul harness <soul_kb_id> <omp|claude> [--model M]    指定单人格训练引擎');
      console.log('  ragctl soul ask <query> [--soul kb] [--type t] [--goal g]  人格问答(自动路由)');
      console.log('  ragctl soul router <query> [--type t]              路由决策预览');
      console.log('  ragctl soul review <soul_kb_id> [--action approve] [--draft id]  记忆审批');
      console.log('  ragctl soul checkpoint <soul_kb_id>                创建检查点快照');
      console.log('  ragctl soul reflect <soul_kb_id>                   人格反思');
      console.log('  ragctl soul export <soul_kb_id> [--min-score 4]    导出训练数据');
      console.log('  ragctl soul delete <soul_kb_id>                    删除人格');
      console.log('  完整能力(模板复制/索引/审批)请用 Web SOUL 页面或 MCP soul_* 工具');
  }
  return 0;
}

async function cmdMeditation(args) {
  const [sub, ...rest] = args;
  const backendUrl = getBackendUrl();

  async function apiGet(path) {
    const res = await fetch(`${backendUrl}${path}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return res.json();
  }

  async function apiPost(path, body) {
    const res = await fetch(`${backendUrl}${path}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return res.json();
  }

  switch (sub) {
    case 'status': {
      const kbId = rest[0] || '';
      const url = kbId ? `/api/v1/meditation/status?kb_id=${kbId}` : '/api/v1/meditation/status';
      const data = await apiGet(url);
      if (data.success) {
        console.log('\n🧘 Meditation Status');
        console.log('═══════════════════');
        console.log(`  Scheduler: ${data.scheduler?.enabled ? '✅ enabled' : '⏸ disabled'}`);
        if (data.scheduler?.running_now) console.log('  Currently running: YES');
        if (data.scheduler?.last_run) console.log(`  Last run: ${data.scheduler.last_run}`);
        console.log('');
        console.log('  Harness Status:');
        for (const [name, info] of Object.entries(data.harnesses || {})) {
          const status = info.installed ? '✅' : '❌';
          console.log(`    ${status} ${name}: ${info.version || 'not installed'}`);
        }
        if (data.circuit_breaker) {
          for (const [name, cb] of Object.entries(data.circuit_breaker)) {
            if (cb.tripped) console.log(`    ⚠ ${name} circuit breaker OPEN until ${new Date(cb.until * 1000).toISOString()}`);
          }
        }
        console.log('');
        if (data.kb_configs?.length) {
          console.log('  KB Configs:');
          for (const kc of data.kb_configs) {
            const cfg = kc.config;
            console.log(`    ${cfg.enabled ? '🧘' : '⏸'} ${kc.kb_name}: harness=${cfg.harness} interval=${cfg.interval_hours}h runs=${cfg.total_runs} exp=${cfg.total_experiences_generated}`);
          }
        }
      } else {
        console.log(JSON.stringify(data, null, 2));
      }
      break;
    }

    case 'run': {
      const kbId = rest.find(a => !a.startsWith('--')) || '';
      const data = await apiPost('/api/v1/meditation/run', { kb_id: kbId, trigger: 'manual' });
      console.log(data.success ? '✅ Meditation triggered' : `❌ Failed: ${data.error || JSON.stringify(data)}`);
      if (data.report) console.log(JSON.stringify(data.report, null, 2));
      break;
    }

    case 'history': {
      const kbId = rest[0] || '';
      const limit = parseInt(rest.find(a => a.startsWith('--lines='))?.split('=')[1] || '20', 10);
      const url = `/api/v1/meditation/history?limit=${limit}${kbId ? `&kb_id=${kbId}` : ''}`;
      const data = await apiGet(url);
      if (data.success && data.runs) {
        console.log('\n🧘 Meditation History');
        console.log('═════════════════════');
        for (const r of data.runs) {
          const statusIcon = r.status === 'completed' ? '✅' : r.status === 'failed' ? '❌' : r.status === 'timeout' ? '⏰' : '🔄';
          console.log(`  ${statusIcon} #${r.id}: ${r.kb_id} via ${r.harness} (${r.trigger})`);
          console.log(`     ${r.started_at} → ${r.finished_at || '...'}  exp=${r.experiences_created} drafts=${r.drafts_created}`);
          if (r.error) console.log(`     Error: ${r.error}`);
        }
      } else {
        console.log(JSON.stringify(data, null, 2));
      }
      break;
    }

    case 'config': {
      const kbId = rest[0];
      if (!kbId) {
        console.log('Usage: ragctl meditation config <kb_id>');
        return 1;
      }
      const data = await apiGet(`/api/v1/meditation/config?kb_id=${kbId}`);
      if (data.success) {
        console.log(`\n🧘 Meditation Config for ${data.kb_path}`);
        console.log('═══════════════════════════════════');
        console.log(JSON.stringify(data.config, null, 2));
      } else {
        console.log(JSON.stringify(data, null, 2));
      }
      break;
    }

    default:
      console.log(`
🧘 ragctl meditation <subcommand> [options]

Subcommands:
  status [kb_id]     Show meditation status (global or per-KB)
  run [kb_id]        Manually trigger a meditation run
  history [kb_id]    Show recent meditation runs (--lines=N)
  config <kb_id>     Show meditation config for a KB

Examples:
  ragctl meditation status
  ragctl meditation status my-kb
  ragctl meditation run
  ragctl meditation run my-kb
  ragctl meditation history --lines=10
`);
      return 1;
  }
 }
async function main() {
  if (IS_WIN) {
    try { require('child_process').execSync('chcp 65001 >nul 2>&1', { stdio: 'ignore' }); } catch {}
  }
  ensureUvOnPath();

  const args = process.argv.slice(2);
  const command = args[0];
  const ver = readLocalVersion();

  if (!command || command === 'help' || command === '--help' || command === '-h') { showHelp(); return 0; }
  if (command === '--version' || command === '-V') { console.log(`ragctl ${ver}`); return 0; }

  // Route to sub-args (everything after the command name)
  const subArgs = args.slice(1);

  try {
    switch (command) {
      // Core (init = setup alias for backward compat)
      case 'setup': case 'init': return await cmdSetup();
      case 'check': return await cmdCheck();
      case 'deps': return await cmdDeps();
      case 'model': return await cmdModel(subArgs);
      case 'mineru-model': return await cmdMineruModel(subArgs);
      case 'version': case 'ver': return await cmdVersion(subArgs);
      case 'update': case 'upgrade': return await cmdUpdate(subArgs);

      // Service management
      case 'up': case 'start-all': return await cmdUp(subArgs);
      case 'down': case 'stop-all': return await cmdDown(subArgs);
      case 'start': return await cmdStart(subArgs);
      case 'stop': return await cmdStop(subArgs);
      case 'restart': case 'reload': return await cmdRestart(subArgs);
      case 'status': return await cmdStatus(subArgs);

      // Logs
      case 'logs': return await cmdLogs(subArgs);

      // Registration + desktop
      case 'install': return await cmdInstall();
      case 'desktop': case 'ui': return await cmdDesktop(subArgs);

      // Cache & artifact cleanup
      case 'clean': case 'prune': return await cmdClean(subArgs);
      case 'backup': return await cmdBackup(subArgs);
      case 'restore': return await cmdRestore(subArgs);
      case 'meditation': case 'meditate': return await cmdMeditation(subArgs);
      case 'soul': case 'persona': return await cmdSoul(subArgs);
      case 'harness': return await cmdHarness(subArgs);
        err(`未知命令: ${command}`);
        showHelp();
        return 1;
    }
  } catch (e) {
    err(`错误: ${e.message}`);
    console.error(e.stack);
    return 1;
  }
}

process.on('SIGINT', () => { console.log('\n'); process.exit(130); });
main().then(code => process.exit(code)).catch(e => { console.error(e); process.exit(1); });
