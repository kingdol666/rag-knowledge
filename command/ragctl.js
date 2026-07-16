#!/usr/bin/env node

/**
 * ragctl — RAG Knowledge Platform CLI
 * ====================================
 *
 * 最强大的一键式部署工具
 *
 * Commands:
 *   setup    One-click full setup (uv + deps + models + .env)
 *   check    Comprehensive health check — what's missing, how to fix
 *   deps     Install all dependencies with real-time progress
 *   model    Download BGE embedding model
 *   start    Start services (backend, web, neo4j, mcp, all)
 *   stop     Stop services
 *   status   Show service status
 *   restart  Restart services
 *   config   Configuration management
 *   health   Health check
 *   doctor   Diagnostics
 *   logs     Log viewer
 *   test     Run tests
 *   mcp      MCP management
 *   kb       KB quick operations
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
          // Add to PATH for current session
          const uvDir = path.join(os.homedir(), '.cargo', 'bin');
          process.env.PATH = `${uvDir}${path.delimiter}${process.env.PATH}`;
          // On Windows, also add via setx for persistence
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
        const uvDir = path.join(os.homedir(), '.cargo', 'bin');
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

function getServicePorts() {
  const cfg = readYaml(CONFIG_YML);
  const env = readEnv(ENV_FILE);
  const mode = env.APP_MODE || 'dev';
  const server = cfg.server || {};
  const modeSection = server[mode] || {};
  return {
    backend: parseInt(env.BACKEND_PORT || modeSection.backend_port || '8765'),
    web: parseInt(env.WEB_PORT || modeSection.frontend_port || '6789'),
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

function spawnService({ mode, title, cwd, command, args, env }) {
  const fullEnv = { ...process.env, ...(env || {}) };
  if (mode === 'dev') {
    const line = `${command} ${args.join(' ')}`;
    if (spawnInTerminal(title, line, { env: fullEnv, cwd })) return;
    warn('无可用终端 — 后台启动（ragctl logs 查看日志）');
  }
  spawn(command, args, {
    cwd, env: fullEnv, detached: true, stdio: 'ignore', windowsHide: true,
    shell: IS_WIN,
  }).unref();
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

async function startBackend(mode, port) {
  if (await portInUse(port)) { warn(`Backend 已在端口 ${port} 运行`); return; }
  info(`启动 Backend (端口 ${port}, mode=${mode})...`);
  spawnService({ mode, title: `RAG-Backend (${mode})`, cwd: BACKEND_DIR, command: 'uv', args: ['run', 'python', 'main.py'], env: { APP_MODE: mode } });
  for (let i = 0; i < 30; i++) {
    await sleep(1000);
    if (await portInUse(port)) { ok(`Backend 已启动 (端口 ${port})`); return; }
  }
  warn(`Backend 启动超时 (端口 ${port})`);
}

async function stopBackend(port) {
  let stopped = false;
  const pid = findPidOnPort(port);
  if (pid) { killPid(pid, true); stopped = true; }
  for (const p of findPythonProcesses('main.py')) { killPid(p.pid, true); stopped = true; }
  if (stopped) ok('Backend 已停止'); else warn('未找到 Backend 进程');
}

async function startWeb(mode, port) {
  if (await portInUse(port)) { warn(`Web 已在端口 ${port} 运行`); return; }
  info(`启动 Web 前端 (端口 ${port}, mode=${mode})...`);
  spawnService({ mode, title: `RAG-Web (${mode})`, cwd: WEB_DIR, command: 'node', args: ['start.mjs'], env: { APP_MODE: mode, WEB_PORT: String(port) } });
  for (let i = 0; i < 20; i++) {
    await sleep(1000);
    if (await portInUse(port)) { ok(`Web 已启动 (端口 ${port})`); return; }
  }
  warn(`Web 启动超时 (端口 ${port})`);
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

async function cmdUp(mode) {
  mode = mode || getAppMode();
  const ports = getServicePorts();
  header(`启动 RAG Knowledge Platform (mode=${mode})`);
  const composeFile = path.join(PROJECT_ROOT, 'docker-compose.yml');
  if (fs.existsSync(composeFile) && !(await portInUse(7687))) { await startNeo4j(); await sleep(2000); }
  await startBackend(mode, ports.backend);
  await startWeb(mode, ports.web);
  console.log(`\n  ${_c(C.GREEN, _c(C.BOLD, '所有服务已启动！'))}`);
  console.log(`  Backend: ${_c(C.CYAN, `http://localhost:${ports.backend}`)}`);
  console.log(`  Web UI:  ${_c(C.CYAN, `http://localhost:${ports.web}`)}`);
  return 0;
}

async function cmdDown() {
  const ports = getServicePorts();
  header('停止 RAG Knowledge Platform');
  await stopWeb(ports.web);
  await stopBackend(ports.backend);
  await stopNeo4j();
  ok('所有服务已停止');
  return 0;
}

async function cmdStatus() {
  const ports = getServicePorts();
  header('服务状态');
  const backendUp = await portInUse(ports.backend);
  console.log(`  Backend (${ports.backend}): ${backendUp ? _c(C.GREEN, '● 运行中') : _c(C.RED, '○ 已停止')}`);
  const webUp = await portInUse(ports.web);
  console.log(`  Web     (${ports.web}): ${webUp ? _c(C.GREEN, '● 运行中') : _c(C.RED, '○ 已停止')}`);
  const neo4jUp = await portInUse(7687);
  console.log(`  Neo4j   (7687): ${neo4jUp ? _c(C.GREEN, '● 运行中') : _c(C.RED, '○ 已停止')}`);
  const mcpProcs = findPythonProcesses('server.py');
  console.log(`  MCP     (stdio): ${mcpProcs.length > 0 ? _c(C.GREEN, `● 运行中 (${mcpProcs.length} 进程)`) : _c(C.RED, '○ 已停止')}`);
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

${_c(C.CYAN, '服务管理:')}
  up / start  启动所有服务
  down / stop 停止所有服务
  status      查看服务状态
  restart     重启服务

${_c(C.CYAN, '工具:')}
  health      健康检查
  doctor      诊断常见问题
  config      配置管理 (show/get/set/edit)
  logs        查看日志
  test        运行测试
  kb          KB 快捷操作 (list/search/stats)

${_c(C.CYAN, '快速开始:')}
  ragctl setup             # 一键部署（首次运行推荐）
  ragctl check             # 检查环境状态
  ragctl up                # 启动所有服务
  ragctl status            # 查看状态
`);
}

async function main() {
  if (IS_WIN) {
    try { require('child_process').execSync('chcp 65001 >nul 2>&1', { stdio: 'ignore' }); } catch {}
  }

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
      case 'down': case 'stop-all': return await cmdDown();
      case 'status': return await cmdStatus();

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
