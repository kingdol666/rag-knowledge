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
 *   model    Download BGE embedding model
 *   up       Start all services (silent — no terminal windows)
 *   down     Stop all services
 *   start    Start a specific service (backend|web|neo4j|all)
 *   stop     Stop a specific service (backend|web|neo4j|all)
 *   restart  Restart a specific service (backend|web|neo4j|all)
 *   status   Show service status
 *   logs     View/tail service logs (backend|web|mineru) [--tail] [--lines N]
 */

'use strict';

const { spawn, exec, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
const net = require('net');
const http = require('http');
const https = require('https');
const yaml = require('js-yaml');

// ── Project Paths ──────────────────────────────────────────────────────
const PROJECT_ROOT = path.resolve(__dirname, '..');
const BACKEND_DIR = path.join(PROJECT_ROOT, 'backend');
const WEB_DIR = path.join(PROJECT_ROOT, 'web');
const MCP_DIR = path.join(PROJECT_ROOT, 'kb-mcp');
const CONFIG_YML = path.join(PROJECT_ROOT, 'config.yml');
const BACKEND_CONFIG_YML = path.join(BACKEND_DIR, 'config.yml');
const ENV_FILE = path.join(PROJECT_ROOT, '.env');
const UV_VERSION = '0.7.0'; // Recommended uv version

const IS_WIN = os.platform() === 'win32';

// ── Log paths (single source of truth — MUST match src-tauri watch_log paths) ──
// Both ragctl and Tauri write/read the same files so the desktop log viewer works
// regardless of which launcher started the service. Truncated on each start.
const LOG_PATHS = {
  backend: path.join(BACKEND_DIR, 'logs', 'desktop-stdout.log'),
  web:     path.join(WEB_DIR, 'logs', 'desktop-stdout.log'),
  mineru:  path.join(BACKEND_DIR, 'logs', 'mineru-api.log'),
};
function getLogPath(service) { return LOG_PATHS[service]; }

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
      const output = execSync(`netstat -ano | findstr :${port} | findstr LISTENING`, { encoding: 'utf8', timeout: 10000, stdio: ['pipe','pipe','pipe'] });
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
      execSync(`taskkill /PID ${pid} /T${force ? ' /F' : ''}`, { timeout: 10000, stdio: ['pipe','pipe','pipe'] });
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

  // uv check with version
  let uvVersion = '';
  try {
    uvVersion = execSync('uv --version', { encoding: 'utf8', timeout: 5000, stdio: ['pipe','pipe','pipe'] }).trim();
    const match = uvVersion.match(/uv (\d+\.\d+\.\d+)/);
    const ver = match ? match[1] : 'unknown';
    addResult('pass', 'uv (Python 包管理器)', `已安装: ${uvVersion}`, null);
  } catch {
    addResult('fail', 'uv (Python 包管理器)', '未找到 uv', IS_WIN
      ? '运行: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
      : '运行: curl -LsSf https://astral.sh/uv/install.sh | sh');
  }

  // Node.js
  addResult('pass', 'Node.js', process.version, null);

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
    addResult('warn', 'Git', '未找到 Git（子模块管理需要）', '安装: https://git-scm.com/downloads');
  }

  // Docker (optional)
  try {
    const dockerVer = execSync('docker --version', { encoding: 'utf8', timeout: 5000, stdio: ['pipe','pipe','pipe'] }).trim();
    addResult('pass', 'Docker', dockerVer, null);
  } catch {
    addResult('warn', 'Docker', '未找到（Neo4j 图谱需要）', '安装 Docker Desktop: https://docker.com');
  }

  // 3. Project files
  console.log(`\n${_c(C.BOLD, '── 项目文件 ──')}\n`);

  const fileChecks = [
    ['config.yml', CONFIG_YML, '主配置文件缺失'],
    ['backend/config.yml', BACKEND_CONFIG_YML, '后端配置文件缺失'],
    ['.env', ENV_FILE, '环境变量文件缺失（运行: ragctl setup）'],
    ['backend/app/main.py', path.join(BACKEND_DIR, 'app', 'main.py'), '后端子模块未初始化（运行: git submodule update --init --recursive）'],
    ['web/package.json', path.join(WEB_DIR, 'package.json'), '前端子模块未初始化（运行: git submodule update --init --recursive）'],
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
  if (fs.existsSync(path.join(BACKEND_DIR, '.venv')) || fs.existsSync(path.join(BACKEND_DIR, 'uv.lock'))) {
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
  if (fs.existsSync(path.join(MCP_DIR, '.venv')) || fs.existsSync(path.join(MCP_DIR, 'uv.lock'))) {
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

  // 5. BGE Model
  console.log(`\n${_c(C.BOLD, '── AI 模型 ──')}\n`);
  const modelDir = path.join(os.homedir(), '.cache', 'huggingface', 'hub', 'models--BAAI--bge-m3');
  const modelSnapshot = fs.existsSync(modelDir) ? fs.readdirSync(path.join(modelDir, 'snapshots')).length > 0 ? '已下载' : '未完成' : '未下载';
  if (modelSnapshot === '已下载') {
    addResult('pass', 'BGE-M3 嵌入模型', '已下载 (向量搜索核心模型)', null);
  } else {
    addResult('warn', 'BGE-M3 嵌入模型', `${modelSnapshot}（首次向量索引时自动下载 ~2.2GB）`, '预下载: ragctl model');
  }

  // 6. Ports
  console.log(`\n${_c(C.BOLD, '── 端口状态 ──')}\n`);

  const ports = [
    [8765, 'Backend API'],
    [6789, 'Web UI (dev)'],
    [3000, 'Web UI (prod)'],
    [7687, 'Neo4j Bolt'],
    [7474, 'Neo4j HTTP'],
  ];

  for (const [port, name] of ports) {
    if (await portInUse(port)) {
      const pid = findPidOnPort(port);
      const pidInfo = pid ? ` (PID ${pid})` : '';
      addResult('pass', `端口 ${port} (${name})`, `运行中${pidInfo}`, null);
    } else {
      addResult('warn', `端口 ${port} (${name})`, '未使用', '服务未启动，运行: ragctl up');
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

  // 1. Install uv if missing
  if (!commandExists('uv')) {
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
          // On Windows, persist to PATH via setx (takes effect in NEW terminals;
          // ensureUvOnPath() covers the current session / ragctl wrappers).
          if (IS_WIN) {
            try {
              execSync(`setx PATH "%PATH%;${uvDir}"`, { stdio: 'ignore', timeout: 5000 });
            } catch {}
          }
          info(`uv 已安装到: ${uvDir}`);
        } else {
          err(`uv 安装失败 (exit ${result.code})`);
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
        process.env.PATH = `${uvDir}:${process.env.PATH}`;
      } else {
        err('uv 安装失败');
        return 1;
      }
    }
    try { fs.unlinkSync(path.join(os.tmpdir(), 'uv-install.ps1')); } catch {}
  } else {
    let uvVer = '';
    try { uvVer = execSync('uv --version', { encoding: 'utf8', timeout: 5000, stdio: ['pipe','pipe','pipe'] }).trim(); } catch {}
    ok(`uv 已安装: ${uvVer}`);
  }

  // 2. Git submodules
  step('初始化 Git 子模块...');
  if (fs.existsSync(path.join(BACKEND_DIR, 'app', 'main.py')) && fs.existsSync(path.join(WEB_DIR, 'package.json'))) {
    ok('子模块已初始化');
  } else {
    const result = await spawnAsync('git', ['submodule', 'update', '--init', '--recursive'], { cwd: PROJECT_ROOT, silent: true });
    if (result.code === 0) ok('子模块初始化完成');
    else { err('子模块初始化失败'); return 1; }
  }

  // 3. .env
  step('配置环境变量...');
  if (!fs.existsSync(ENV_FILE)) {
    const examplePath = path.join(PROJECT_ROOT, '.env.example');
    if (fs.existsSync(examplePath)) {
      fs.copyFileSync(examplePath, ENV_FILE);
      ok('.env 已从 .env.example 创建');
    } else {
      writeEnv({ APP_MODE: 'dev', PYTHONUTF8: '1' });
      ok('.env 已创建（默认值）');
    }
  } else {
    ok('.env 已存在');
  }

  // 4. Install dependencies with progress
  await cmdDeps();

  // 5. BGE Model
  await cmdModel();

  // 6. Final check
  console.log();
  return await cmdCheck();
}

// ═══════════════════════════════════════════════════════════════════════
//  ⭐ NEW: deps — Install all dependencies with real-time progress
// ═══════════════════════════════════════════════════════════════════════

async function cmdDeps() {
  step('安装所有依赖（实时进度）...');

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

  // Backend (uv sync with real-time output)
  info('安装 Backend (Python) 依赖...');
  console.log(`  ${_c(C.GRAY, '── uv sync backend ──')}`);
  const beResult = await spawnAsync('uv', ['sync'], { cwd: BACKEND_DIR });
  if (beResult.code === 0) ok('Backend 依赖安装完成');
  else { err('Backend 依赖安装失败'); return 1; }

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
    await spawnAsync('npm', ['install'], { cwd: WEB_DIR });
  }

  // MCP
  info('安装 MCP Server 依赖...');
  console.log(`  ${_c(C.GRAY, '── uv sync kb-mcp ──')}`);
  const mcpResult = await spawnAsync('uv', ['sync'], { cwd: MCP_DIR });
  if (mcpResult.code === 0) ok('MCP 依赖安装完成');
  else { err('MCP 依赖安装失败'); return 1; }

  console.log();
  ok(_c(C.BOLD, '所有依赖安装完成！'));
  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  ⭐ NEW: model — Pre-download BGE-M3 embedding model
// ═══════════════════════════════════════════════════════════════════════

async function cmdModel() {
  step('BGE-M3 嵌入模型下载 (~2.2 GB)...');

  // 1. Quick check: is model already loadable via backend venv?
  const backendVenvPy = path.join(BACKEND_DIR, '.venv', IS_WIN ? 'Scripts' : 'bin', IS_WIN ? 'python.exe' : 'python');
  if (fs.existsSync(backendVenvPy)) {
    try {
      const check = execSync(
        `"${backendVenvPy}" -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"`,
        { encoding: 'utf8', timeout: 30000, stdio: ['pipe','pipe','pipe'] }
      );
      if (!check.includes('Error') && !check.includes('Traceback')) {
        ok('BGE-M3 模型已缓存（跳过下载）');
        return 0;
      }
    } catch {
      // Model not cached yet, continue with download
    }
  }

  // 2. Check huggingface cache
  const home = os.homedir();
  const cacheDir = path.join(home, '.cache', 'huggingface', 'hub', 'models--BAAI--bge-m3');
  if (fs.existsSync(cacheDir)) {
    const snapshots = path.join(cacheDir, 'snapshots');
    if (fs.existsSync(snapshots) && fs.readdirSync(snapshots).length > 0) {
      ok('BGE-M3 模型已缓存（跳过下载）');
      return 0;
    }
  }

  // 3. Download if not found
  if (fs.existsSync(backendVenvPy)) {
    info('通过 Python 下载模型（约 2.2GB，使用 hf-mirror 镜像）...');
    console.log(`  ${_c(C.GRAY, '── 下载中，请耐心等待 ──')}`);

    const script = `
import sys
print("Loading sentence_transformers...")
from sentence_transformers import SentenceTransformer
print("Downloading BAAI/bge-m3 model to local cache...")
model = SentenceTransformer("BAAI/bge-m3")
print("Model loaded. Dimension:", model.get_embedding_dimension())
`;
    const scriptPath = path.join(os.tmpdir(), 'ragctl_bge_download.py');
    fs.writeFileSync(scriptPath, script, 'utf8');

    const result = await spawnAsync(backendVenvPy, [scriptPath], {
      cwd: BACKEND_DIR,
      env: { ...process.env, HF_ENDPOINT: process.env.HF_ENDPOINT || 'https://hf-mirror.com' },
    });

    try { fs.unlinkSync(scriptPath); } catch {}

    if (result.code === 0) {
      ok('BGE-M3 模型下载完成！');
      return 0;
    }
    warn('模型下载未完全成功，首次索引时系统会自动重试');
  } else {
    warn('Backend venv 未就绪，请先运行 ragctl deps 再下载模型');
  }

  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMANDS: start / stop / status / restart (same as before, improved)
// ═══════════════════════════════════════════════════════════════════════

function getServicePorts(modeOverride) {
  const cfg = readYaml(CONFIG_YML);
  const env = readEnv(ENV_FILE);
  const mode = modeOverride || env.APP_MODE || 'dev';
  const server = cfg.server || {};
  const modeSection = server[mode] || {};
  // When a mode is EXPLICITLY passed (--mode prod), resolve ports from config.yml
  // for that mode and IGNORE .env BACKEND_PORT/WEB_PORT — otherwise .env (which
  // pins a specific mode's ports) would silently override the runtime choice.
  if (modeOverride) {
    return {
      backend: parseInt(modeSection.backend_port || '8765'),
      web: parseInt(modeSection.frontend_port || '6789'),
      mode,
    };
  }
  // Default: .env is the single source of truth (env BACKEND_PORT/WEB_PORT win).
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
      const output = execSync('tasklist /FO CSV /NH', { encoding: 'utf8', timeout: 10000, stdio: ['pipe','pipe','pipe'] });
      for (const line of output.split('\n')) {
        if (line.includes(name) || line.includes('pythonw.exe')) {
          const match = line.match(/"(\d+)"/);
          if (match) procs.push({ pid: parseInt(match[1]), cmd: '' });
        }
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
  const child = spawn(bin, args, {
    cwd,
    env: fullEnv,
    detached: true,
    stdio: ['ignore', fd, fd],
    windowsHide: true,
    shell: false,
  });
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

async function startBackend(mode) {
  const { backend: port } = getServicePorts(mode);
  if (await portInUse(port)) { warn(`Backend 已在端口 ${port} 运行`); return; }
  info(`启动 Backend (端口 ${port}, mode=${mode}, 静默)...`);
  const { pid } = spawnService({
    title: `RAG-Backend (${mode})`,
    cwd: BACKEND_DIR,
    command: 'uv',
    args: ['run', 'python', 'main.py'],
    env: { APP_MODE: mode, BACKEND_PORT: String(port) },
    serviceName: 'backend',
  });
  info(`Backend pid=${pid} · 日志: ${getLogPath('backend')}`);
  for (let i = 0; i < 30; i++) {
    await sleep(1000);
    if (await portInUse(port)) { ok(`Backend 已启动 (端口 ${port}) · ragctl logs backend 查看日志`); return; }
  }
  warn(`Backend 启动超时 (端口 ${port}) — 排查: ragctl logs backend`);
}

async function stopBackend(port) {
  let stopped = false;
  const pid = findPidOnPort(port);
  if (pid) { killPid(pid, true); stopped = true; }
  for (const p of findPythonProcesses('main.py')) { killPid(p.pid, true); stopped = true; }
  if (stopped) ok('Backend 已停止'); else warn('未找到 Backend 进程');
}

async function startWeb(mode) {
  const { web: port, backend } = getServicePorts(mode);
  if (await portInUse(port)) { warn(`Web 已在端口 ${port} 运行`); return; }
  info(`启动 Web 前端 (端口 ${port}, mode=${mode}, 静默)...`);
  const { pid } = spawnService({
    title: `RAG-Web (${mode})`,
    cwd: WEB_DIR,
    command: 'node',
    args: ['start.mjs'],
    // Pass both WEB_PORT and BACKEND_PORT so start.mjs binds the right port
    // AND proxies to the mode-correct backend (overriding root .env defaults).
    env: { APP_MODE: mode, WEB_PORT: String(port), BACKEND_PORT: String(backend) },
    serviceName: 'web',
  });
  info(`Web pid=${pid} · 日志: ${getLogPath('web')}`);
  for (let i = 0; i < 25; i++) {
    await sleep(1000);
    if (await portInUse(port)) { ok(`Web 已启动 (端口 ${port}) · ragctl logs web 查看日志`); return; }
  }
  warn(`Web 启动超时 (端口 ${port}) — 排查: ragctl logs web`);
}

async function stopWeb(port) {
  let stopped = false;
  const pid = findPidOnPort(port);
  if (pid) { killPid(pid, true); stopped = true; }
  if (stopped) ok('Web 已停止'); else warn('未找到 Web 进程');
}

async function startNeo4j() {
  const composeFile = path.join(PROJECT_ROOT, 'docker-compose.yml');
  if (!fs.existsSync(composeFile)) { warn('docker-compose.yml 未找到'); return; }
  try {
    await spawnAsync('docker', ['compose', 'up', '-d', 'neo4j'], { cwd: PROJECT_ROOT, silent: true });
    ok('Neo4j 已启动');
  } catch { warn('Docker 未找到 — 跳过 Neo4j'); }
}

async function stopNeo4j() {
  try {
    await spawnAsync('docker', ['compose', 'down'], { cwd: PROJECT_ROOT, silent: true });
    ok('Neo4j 已停止');
  } catch {}
}

// Parse `--mode dev|prod` from arg list, falling back to .env APP_MODE.
function parseModeArg(args) {
  const i = args.indexOf('--mode');
  if (i !== -1 && args[i + 1]) return args[i + 1];
  return getAppMode();
}

// First positional service arg, skipping `--mode <val>` and any other flags.
function parseServiceArg(args) {
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--mode') { i++; continue; } // skip flag + its value
    if (args[i].startsWith('-')) continue;        // skip other flags
    return args[i];
  }
  return null;
}

// ── Per-service start/stop/restart (silent — same as `up`) ───────────────
async function cmdStart(args) {
  const mode = parseModeArg(args);
  const svc = parseServiceArg(args) || 'all';
  header(`启动服务 (mode=${mode}): ${svc}`);
  const composeFile = path.join(PROJECT_ROOT, 'docker-compose.yml');
  switch (svc) {
    case 'backend':
      await startBackend(mode); break;
    case 'web':
      await startWeb(mode); break;
    case 'neo4j':
      if (fs.existsSync(composeFile) && !(await portInUse(7687))) { await startNeo4j(); }
      else if (await portInUse(7687)) warn('Neo4j 已在运行');
      break;
    case 'all':
      if (fs.existsSync(composeFile) && !(await portInUse(7687))) { await startNeo4j(); await sleep(2000); }
      await startBackend(mode);
      await startWeb(mode);
      break;
    default:
      err(`未知服务: ${svc}（可选: backend / web / neo4j / all）`);
      return 1;
  }
  return 0;
}

async function cmdStop(args) {
  const mode = parseModeArg(args);
  const ports = getServicePorts(mode);
  const svc = parseServiceArg(args) || 'all';
  header(`停止服务 (mode=${mode}): ${svc}`);
  switch (svc) {
    case 'backend': await stopBackend(ports.backend); break;
    case 'web': await stopWeb(ports.web); break;
    case 'neo4j': await stopNeo4j(); break;
    case 'all':
      await stopWeb(ports.web);
      await stopBackend(ports.backend);
      await stopNeo4j();
      break;
    default:
      err(`未知服务: ${svc}（可选: backend / web / neo4j / all）`);
      return 1;
  }
  return 0;
}

async function cmdRestart(args) {
  const svc = parseServiceArg(args) || 'all';
  header(`重启服务: ${svc}`);
  const stopCode = await cmdStop([svc === 'all' ? 'all' : svc]);
  if (stopCode !== 0) return stopCode;
  await sleep(1500);
  const startCode = await cmdStart(args);
  if (startCode !== 0) return startCode;
  ok(`重启完成: ${svc}`);
  return 0;
}

// ── Log viewer ───────────────────────────────────────────────────────────
// `ragctl logs [service] [--tail|-f] [--lines N|-n N]`
//   service ∈ {backend, web, mineru} (default: backend)
// Reads the SAME files that Tauri's desktop log viewer tails and that
// spawnService writes — so output is consistent across all three surfaces.
async function cmdLogs(args) {
  const positional = args.filter(a => !a.startsWith('-'));
  const service = positional[0] || 'backend';
  const wantTail = args.includes('--tail') || args.includes('-f') || args.includes('tail');
  let lines = 80;
  const li = args.indexOf('--lines'); if (li !== -1 && args[li + 1]) lines = parseInt(args[li + 1]) || 80;
  const ni = args.indexOf('-n');      if (ni !== -1 && args[ni + 1]) lines = parseInt(args[ni + 1]) || 80;

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

async function cmdUp(mode) {
  mode = mode || getAppMode();
  const ports = getServicePorts(mode);
  header(`启动 RAG Knowledge Platform (mode=${mode})`);
  const composeFile = path.join(PROJECT_ROOT, 'docker-compose.yml');
  if (fs.existsSync(composeFile) && !(await portInUse(7687))) { await startNeo4j(); await sleep(2000); }
  await startBackend(mode);
  await startWeb(mode);
  console.log(`\n  ${_c(C.GREEN, _c(C.BOLD, '✓ 所有服务已静默启动（无终端窗口）'))}`);
  console.log(`  Backend: ${_c(C.CYAN, `http://localhost:${ports.backend}`)}`);
  console.log(`  Web UI:  ${_c(C.CYAN, `http://localhost:${ports.web}`)}`);
  console.log(`  ${_c(C.GRAY, '查看日志: ragctl logs [backend|web|mineru] [--tail]  ·  或打开 Tauri 桌面控制台')}`);
  return 0;
}

async function cmdDown(mode) {
  mode = mode || getAppMode();
  const ports = getServicePorts(mode);
  header(`停止 RAG Knowledge Platform (mode=${mode})`);
  await stopWeb(ports.web);
  await stopBackend(ports.backend);
  await stopNeo4j();
  ok('所有服务已停止');
  return 0;
}

async function cmdStatus(modeArg) {
  const mode = modeArg || getAppMode();
  const ports = getServicePorts(mode);
  header(`服务状态 (mode=${mode})`);

  // Probe one HTTP service: port-listening → pid → health endpoint.
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

  // MinerU — only meaningful when backend is healthy
  let mineru = 'n/a (backend down)';
  if (b.health === 'healthy') {
    const m = await httpGet(`http://localhost:${ports.backend}/api/v1/mineru/status`, 4000);
    mineru = m.code === 200 ? 'up' : (m.code ? `HTTP ${m.code}` : 'unreachable');
  }
  const mcpProcs = findPythonProcesses('server.py');

  const dot = (on) => on ? _c(C.GREEN, '●') : _c(C.RED, '○');
  const hcol = (h) => h === 'healthy' ? _c(C.GREEN, h)
    : (h ? _c(C.YELLOW, h) : _c(C.GRAY, 'stopped'));

  console.log(`  ${dot(b.listening)} Backend  :${String(ports.backend).padEnd(5)} ${hcol(b.health)}${b.pid ? '  pid=' + _c(C.GRAY, b.pid) : ''}`);
  console.log(`  ${dot(w.listening)} Web      :${String(ports.web).padEnd(5)} ${hcol(w.health)}${w.pid ? '  pid=' + _c(C.GRAY, w.pid) : ''}`);
  console.log(`  ${dot(neo4jUp)} Neo4j    :7687  ${neo4jUp ? _c(C.GREEN, 'listening') + (neo4jHttp ? ' ' + _c(C.GRAY,'(+http :7474)') : '') : _c(C.GRAY, 'stopped')}`);
  console.log(`  ${mineru.startsWith('up') ? _c(C.GREEN, '●') : _c(C.GRAY, '○')} MinerU          ${_c(mineru.startsWith('up') ? C.GREEN : C.GRAY, mineru)}`);
  console.log(`  ${mcpProcs.length > 0 ? _c(C.GREEN, '●') : _c(C.GRAY, '○')} kb-mcp  (stdio) ${mcpProcs.length > 0 ? _c(C.GREEN, mcpProcs.length + ' proc') : _c(C.GRAY, 'managed by Claude Code via .mcp.json')}`);

  const ready = b.health === 'healthy' && w.health === 'healthy';
  console.log(`\n  ${_c(C.GRAY, '日志 →')} ragctl logs backend | ragctl logs web | ragctl logs mineru`);
  console.log(`  ${ready ? _c(C.GREEN, _c(C.BOLD, '✓ 项目就绪')) : _c(C.YELLOW, '✗ 未就绪')}  ·  ${_c(C.CYAN, 'ragctl up')} 启动  ·  MCP: ${_c(C.CYAN, 'kb_project_status')} / ${_c(C.CYAN, 'kb_project_start')}`);
  return 0;
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

  // PATH check
  const pathDirs = (process.env.PATH || '').split(path.delimiter);
  if (pathDirs.includes(binDir)) {
    ok(`${binDir} 已在 PATH 中 — ragctl 现可全局使用`);
  } else {
    warn(`${binDir} 尚不在 PATH 中。添加方法：`);
    if (IS_WIN) info(`  setx PATH "%PATH%;${binDir}"   (然后重开终端)`);
    else info(`  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc`);
  }
  info('测试: 在任意目录运行 `ragctl status`');
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

// ═══════════════════════════════════════════════════════════════════════
//  CLI Entry Point
// ═══════════════════════════════════════════════════════════════════════

function showHelp() {
  console.log(`
${_c(C.BOLD, 'ragctl')} — RAG Knowledge Platform 一键部署 CLI

${_c(C.CYAN, '⭐ 核心命令（一键式部署）:')}
  ${_c(C.BOLD, 'setup')}   一键完整部署（自动安装 uv → 依赖 → 模型 → 配置）
  ${_c(C.BOLD, 'check')}   全面环境检查（显示缺失项 + 修复方案）
  ${_c(C.BOLD, 'deps')}    安装所有依赖（实时进度条）
  ${_c(C.BOLD, 'model')}   预下载 BGE-M3 嵌入模型 (~2.2GB)

${_c(C.CYAN, '服务管理（全部静默启动 · 无终端窗口 · dev/prod 行为一致）:')}
  up / start-all               启动全部服务（backend + web + neo4j）
  down / stop-all              停止全部服务
  start [backend|web|neo4j|all]  启动指定服务
  stop  [backend|web|neo4j|all]  停止指定服务
  restart [backend|web|neo4j|all] 重启指定服务
  status                       查看服务状态

${_c(C.CYAN, '日志（统一落盘 · 三处同源：文件 / Tauri 界面 / 本命令）:')}
  logs [backend|web|mineru]            查看最近日志（默认 backend, 80 行）
  logs <svc> --tail | -f               实时跟踪日志（Ctrl+C 退出）
  logs <svc> --lines N | -n N          指定行数

${_c(C.CYAN, '全局注册 / 桌面控制台:')}
  install                              全局注册 ragctl → ~/.local/bin（任意目录可用）
  desktop | ui [--dev]                 启动 Tauri 桌面控制台（GUI 启动器，与 ragctl 共享日志）

${_c(C.CYAN, '选项:')}
  --mode dev|prod              覆盖 .env 的 APP_MODE（影响端口/行为）

${_c(C.CYAN, '快速开始:')}
  ragctl setup             # 一键部署（首次运行推荐）
  ragctl check             # 检查环境状态
  ragctl up                # 静默启动所有服务（无弹窗）
  ragctl status            # 查看状态
  ragctl logs backend --tail   # 实时查看后端日志

${_c(C.GRAY, '日志路径（与 Tauri 桌面控制台共享同一文件）:')}
${_c(C.GRAY, '  backend → backend/logs/desktop-stdout.log')}
${_c(C.GRAY, '  web     → web/logs/desktop-stdout.log')}
${_c(C.GRAY, '  mineru  → backend/logs/mineru-api.log')}
`);
}

async function main() {
  if (IS_WIN) {
    try { require('child_process').execSync('chcp 65001 >nul 2>&1', { stdio: 'ignore' }); } catch {}
  }
  // Make uv callable in this process even if a fresh terminal hasn't picked up
  // the setx PATH update yet (modern uv lives in ~/.local/bin). No-op if uv is
  // already on PATH.
  ensureUvOnPath();

  const args = process.argv.slice(2);
  const command = args[0];

  if (!command || command === 'help' || command === '--help') { showHelp(); return 0; }
  if (command === '--version') { console.log('ragctl 2.0.0'); return 0; }

  try {
    switch (command) {
      // ⭐ NEW commands
      case 'setup': return await cmdSetup();
      case 'check': return await cmdCheck();
      case 'deps': return await cmdDeps();
      case 'model': return await cmdModel();

      // Service management
      case 'up': case 'start-all': {
        const mode = args.includes('--mode') ? args[args.indexOf('--mode') + 1] : null;
        return await cmdUp(mode);
      }
      case 'down': case 'stop-all': {
        const dmode = args.includes('--mode') ? args[args.indexOf('--mode') + 1] : null;
        return await cmdDown(dmode);
      }
      case 'status': {
        const smode = args.includes('--mode') ? args[args.indexOf('--mode') + 1] : null;
        return await cmdStatus(smode);
      }

      // Per-service lifecycle (silent — same no-terminal behavior as `up`)
      case 'start': return await cmdStart(args.slice(1));
      case 'stop': return await cmdStop(args.slice(1));
      case 'restart': case 'reload': return await cmdRestart(args.slice(1));

      // Logs — read/tail the same files Tauri's desktop viewer watches
      case 'logs': return await cmdLogs(args.slice(1));

      // Global registration + Tauri launcher
      case 'install': return await cmdInstall();
      case 'desktop': case 'ui': return await cmdDesktop(args.slice(1));

      default:
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
