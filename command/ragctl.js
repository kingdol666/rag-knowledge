#!/usr/bin/env node

/**
 * ragctl — RAG Knowledge Platform CLI
 * ====================================
 *
 * Unified command-line interface for the entire RAG Knowledge Platform.
 * Ported from Python to Node.js — zero external runtime dependencies
 * except js-yaml (for YAML read/write).
 *
 * Usage:
 *   ragctl <command> [subcommand] [options]
 *
 * Commands:
 *   start    Start services (backend, web, neo4j, mcp, all)
 *   stop     Stop services (backend, web, neo4j, mcp, all)
 *   status   Show service status
 *   restart  Restart services
 *   config   Configuration management (show, get, set, reload, edit)
 *   health   Health check for all services
 *   doctor   Diagnose common issues
 *   logs     View service logs
 *   install  Install dependencies (backend, web, mcp, all)
 *   test     Run tests (backend, web, mcp)
 *   mcp      MCP server management
 *   kb       Knowledge base quick operations
 */

'use strict';

const { spawn, exec, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
const net = require('net');
const http = require('http');
const yaml = require('js-yaml');

// ── Project Paths ──────────────────────────────────────────────────────
const PROJECT_ROOT = path.resolve(__dirname, '..');
const BACKEND_DIR = path.join(PROJECT_ROOT, 'backend');
const WEB_DIR = path.join(PROJECT_ROOT, 'web');
const MCP_DIR = path.join(PROJECT_ROOT, 'kb-mcp');
const CONFIG_YML = path.join(PROJECT_ROOT, 'config.yml');
const BACKEND_CONFIG_YML = path.join(BACKEND_DIR, 'config.yml');
const ENV_FILE = path.join(PROJECT_ROOT, '.env');

const IS_WIN = os.platform() === 'win32';

// ── ANSI Colors ────────────────────────────────────────────────────────
const C = {
  RESET: '\x1b[0m',
  BOLD: '\x1b[1m',
  RED: '\x1b[91m',
  GREEN: '\x1b[92m',
  YELLOW: '\x1b[93m',
  CYAN: '\x1b[96m',
  GRAY: '\x1b[90m',
};

function _c(color, text) {
  return `${color}${text}${C.RESET}`;
}

function info(msg) { console.log(`  ${_c(C.CYAN, '[INFO]')} ${msg}`); }
function ok(msg) { console.log(`  ${_c(C.GREEN, '[OK]')} ${msg}`); }
function warn(msg) { console.log(`  ${_c(C.YELLOW, '[WARN]')} ${msg}`); }
function err(msg) { console.error(`  ${_c(C.RED, '[ERROR]')} ${msg}`); }

function header(title) {
  const line = '='.repeat(60);
  console.log(`\n${_c(C.BOLD, line)}`);
  console.log(_c(C.BOLD, `  ${title}`));
  console.log(_c(C.BOLD, line));
}

// ── Config Readers ─────────────────────────────────────────────────────

function readYaml(filePath) {
  if (!fs.existsSync(filePath)) return {};
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return yaml.load(content) || {};
  } catch {
    return {};
  }
}

function writeYaml(filePath, data) {
  const content = yaml.dump(data, { lineWidth: -1, noRefs: true });
  fs.writeFileSync(filePath, content, 'utf8');
}

function readEnv(filePath) {
  const result = {};
  if (!fs.existsSync(filePath)) return result;
  const content = fs.readFileSync(filePath, 'utf8');
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const idx = trimmed.indexOf('=');
    if (idx > 0) {
      result[trimmed.slice(0, idx).trim()] = trimmed.slice(idx + 1).trim();
    }
  }
  return result;
}

function writeEnv(env) {
  const lines = [
    '# ============================================',
    '# RAG Knowledge Platform - Environment Variables',
    '# ============================================',
    '# Env vars override config.yml values.',
    '# Modified via the web Settings page or manually.',
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

function getConfig() {
  const shared = readYaml(CONFIG_YML);
  const backend = readYaml(BACKEND_CONFIG_YML);
  const merged = { ...shared };
  if (backend.mineru) merged.mineru = backend.mineru;
  return merged;
}

function getEffectiveConfig() {
  const cfg = getConfig();
  const env = readEnv(ENV_FILE);
  const mode = env.APP_MODE || 'dev';
  const server = cfg.server || {};
  const modeSection = server[mode] || {};

  return {
    app_mode: mode,
    backend_port: env.BACKEND_PORT || String(modeSection.backend_port || ''),
    frontend_port: env.WEB_PORT || String(modeSection.frontend_port || ''),
    backend_url: env.BACKEND_URL || modeSection.backend_url || '',
    tree_storage_path: env.TREE_STORAGE_PATH || (cfg.storage || {}).tree_fs_root || '',
    vector_enabled: (cfg.vector || {}).enabled || false,
    graph_enabled: (cfg.graph || {}).enabled || false,
    mineru_enabled: (cfg.mineru || {}).enabled || false,
  };
}

function getServicePorts() {
  const eff = getEffectiveConfig();
  return {
    backend: parseInt(eff.backend_port) || 8765,
    web: parseInt(eff.frontend_port) || 6789,
  };
}

// ── Port / Process Helpers ─────────────────────────────────────────────

function portInUse(port) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(1000);
    socket.once('connect', () => {
      socket.destroy();
      resolve(true);
    });
    socket.once('timeout', () => {
      socket.destroy();
      resolve(false);
    });
    socket.once('error', () => {
      resolve(false);
    });
    socket.connect(port, '127.0.0.1');
  });
}

function portInUseSync(port) {
  try {
    const socket = new net.Socket();
    socket.setTimeout(100);
    let connected = false;
    socket.on('connect', () => { connected = true; socket.destroy(); });
    socket.on('error', () => { socket.destroy(); });
    socket.on('timeout', () => { socket.destroy(); });
    socket.connect(port, '127.0.0.1');
    // Brief synchronous wait — this is a best-effort check
    const start = Date.now();
    while (Date.now() - start < 300 && !socket.destroyed) {
      // spin briefly
    }
    return connected;
  } catch {
    return false;
  }
}

function findPidOnPort(port) {
  try {
    let output;
    if (IS_WIN) {
      output = execSync(`netstat -ano | findstr :${port} | findstr LISTENING`, {
        encoding: 'utf8', timeout: 10000
      });
      const lines = output.trim().split('\n');
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        if (parts.length > 0) return parseInt(parts[parts.length - 1]);
      }
    } else {
      output = execSync(`lsof -ti:${port} 2>/dev/null || ss -tlnp | grep ':${port}'`, {
        encoding: 'utf8', timeout: 10000
      });
      const pid = output.trim().split('\n')[0];
      if (pid) return parseInt(pid);
    }
  } catch {}
  return null;
}

function killPid(pid, force = false) {
  try {
    if (IS_WIN) {
      const cmd = `taskkill /PID ${pid} /T${force ? ' /F' : ''}`;
      execSync(cmd, { timeout: 10000, stdio: 'pipe' });
    } else {
      const sig = force ? 'SIGKILL' : 'SIGTERM';
      process.kill(pid, sig);
    }
    return true;
  } catch {
    return false;
  }
}

function findProcesses(keyword, processName) {
  const procs = [];
  try {
    let output;
    if (IS_WIN) {
      const wmicCmd = `wmic process where "name='${processName}'" get ProcessId,CommandLine /format:list`;
      output = execSync(wmicCmd, { encoding: 'utf8', timeout: 10000, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true });
      if (output.includes('No Instance')) output = '';
      const entries = output.split('\n\n');
      for (const entry of entries) {
        const cmdMatch = entry.match(/CommandLine=(.+)/);
        const pidMatch = entry.match(/ProcessId=(\d+)/);
        if (cmdMatch && pidMatch) {
          const cmd = cmdMatch[1].trim();
          if (cmd.toLowerCase().includes(keyword.toLowerCase())) {
            procs.push({ pid: parseInt(pidMatch[1]), cmd });
          }
        }
      }
    } else {
      output = execSync('ps aux', { encoding: 'utf8', timeout: 10000 });
      for (const line of output.split('\n')) {
        if (line.toLowerCase().includes(keyword.toLowerCase()) && line.toLowerCase().includes(processName.toLowerCase().replace('.exe', ''))) {
          const parts = line.trim().split(/\s+/);
          if (parts.length >= 2) {
            procs.push({ pid: parseInt(parts[1]), cmd: parts.slice(10).join(' ') });
          }
        }
      }
    }
  } catch {}
  return procs;
}

function findPythonProcesses(keyword) {
  const name = IS_WIN ? 'python.exe' : 'python';
  return findProcesses(keyword, name).concat(
    IS_WIN ? findProcesses(keyword, 'pythonw.exe') : []
  );
}

function findNodeProcesses(keyword) {
  const name = IS_WIN ? 'node.exe' : 'node';
  return findProcesses(keyword, name);
}

// ── Terminal / Spawn Helpers ───────────────────────────────────────────

function commandExists(cmd) {
  try {
    execSync(IS_WIN ? `where ${cmd}` : `command -v ${cmd}`, {
      stdio: 'ignore', timeout: 3000, shell: IS_WIN,
    });
    return true;
  } catch {
    return false;
  }
}

/**
 * dev 模式专用：打开一个可见终端窗口运行 commandLine，实时显示 stdout/stderr 日志，
 * 窗口标题 = title，关闭窗口即停止该服务。
 *
 * 跨平台策略：
 *   Windows : `cmd /c start "title" cmd /k "<commandLine>"`（新 cmd 窗口，/k 保持开启）
 *   macOS   : osascript → Terminal.app（custom title）
 *   Linux   : 按优先级探测 gnome-terminal / xfce4-terminal / konsole / mate-terminal / xterm
 *
 * 返回 true 表示成功开窗；false 表示无可用终端（调用方应降级到后台日志）。
 */
function spawnInTerminal(title, commandLine, opts = {}) {
  const env = { ...process.env, ...(opts.env || {}) };
  const cwd = opts.cwd || PROJECT_ROOT;

  if (IS_WIN) {
    // `start` 是 cmd 内置命令，必须经 cmd /c；/k 让窗口在命令结束后保持开启（持续看日志）
    spawn('cmd', ['/c', 'start', `"${title}"`, 'cmd', '/k', commandLine], {
      cwd, env, shell: false, windowsHide: false,
    }).unref();
    return true;
  }

  if (process.platform === 'darwin') {
    const esc = commandLine.replace(/"/g, '\\"');
    const script = `tell application "Terminal"
      activate
      do script "cd \\"${cwd}\\" && ${esc}"
      set custom title of front window to "${title}"
    end tell`;
    spawn('osascript', ['-e', script], { cwd, env, stdio: 'ignore', detached: true }).unref();
    return true;
  }

  // Linux: 按优先级探测终端模拟器
  const runners = [
    ['gnome-terminal', (t, c) => ['--title', t, '--', 'bash', '-lc', `${c}; exec bash`]],
    ['xfce4-terminal', (t, c) => ['--title', t, '-x', 'bash', '-lc', `${c}; exec bash`]],
    ['konsole',        (t, c) => ['-p', `tabtitle=${t}`, '-e', 'bash', '-lc', `${c}; exec bash`]],
    ['mate-terminal',  (t, c) => ['--title', t, '-x', 'bash', '-lc', `${c}; exec bash`]],
    ['xterm',          (t, c) => ['-T', t, '-e', 'bash', '-lc', c]],
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
 * 启动单个服务进程的统一入口，按 mode 分流：
 *   dev  → 可见终端窗口（实时日志，关闭窗口即停）
 *   prod → 后台静默（detached + windowsHide + stdio:ignore，日志写文件由服务自身负责）
 *
 * 在无可用终端的 headless Linux 上 dev 自动降级到后台（与 prod 同行为，提示用 `ragctl logs`）。
 */
function spawnService({ mode, title, cwd, command, args, env }) {
  const fullEnv = { ...process.env, ...(env || {}) };

  if (mode === 'dev') {
    const line = `${command} ${args.join(' ')}`;
    if (spawnInTerminal(title, line, { env: fullEnv, cwd })) {
      info(`${title.split(' (')[0]} launching in a new terminal window (close it to stop)`);
      return;
    }
    warn('No terminal emulator available — starting in background (use `ragctl logs` to view)');
  }

  // prod（或 dev 降级）：后台静默
  spawn(command, args, {
    cwd, env: fullEnv, detached: true, stdio: 'ignore', windowsHide: true, shell: IS_WIN,
  }).unref();
}

// ── HTTP Helpers ───────────────────────────────────────────────────────

function httpGet(url, timeout = 5000) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout }, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => resolve({ code: res.statusCode, body }));
    });
    req.on('error', (e) => resolve({ code: 0, body: e.message }));
    req.on('timeout', () => { req.destroy(); resolve({ code: 0, body: 'timeout' }); });
  });
}

function httpRequest(url, method, data, timeout = 10000) {
  return new Promise((resolve) => {
    const urlObj = new URL(url);
    const body = data ? JSON.stringify(data) : null;
    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port,
      path: urlObj.pathname + urlObj.search,
      method,
      timeout,
      headers: {},
    };
    if (body) {
      options.headers['Content-Type'] = 'application/json';
      options.headers['Content-Length'] = Buffer.byteLength(body);
    }
    const req = http.request(options, (res) => {
      let respBody = '';
      res.on('data', (chunk) => respBody += chunk);
      res.on('end', () => resolve({ code: res.statusCode, body: respBody }));
    });
    req.on('error', (e) => resolve({ code: 0, body: e.message }));
    req.on('timeout', () => { req.destroy(); resolve({ code: 0, body: 'timeout' }); });
    if (body) req.write(body);
    req.end();
  });
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: start
// ═══════════════════════════════════════════════════════════════════════

async function cmdStart(service, mode) {
  mode = mode || getAppMode();
  const ports = getServicePorts();

  header(`Starting ${service.toUpperCase()} (mode=${mode})`);

  if (service === 'backend' || service === 'all') {
    await startBackend(mode, ports.backend);
  }
  if (service === 'web' || service === 'all') {
    await startWeb(mode, ports.web);
  }
  if (service === 'neo4j' || service === 'all') {
    await startNeo4j();
  }
  if (service === 'mcp') {
    await startMcp(mode);
  }

  return 0;
}

async function startBackend(mode, port) {
  const inUse = await portInUse(port);
  if (inUse) {
    const pid = findPidOnPort(port);
    warn(`Backend port ${port} already in use` + (pid ? ` (PID ${pid})` : ''));
    return;
  }

  info(`Starting backend on port ${port} (mode=${mode})...`);
  spawnService({
    mode,
    title: `RAG-Backend (${mode})`,
    cwd: BACKEND_DIR,
    command: 'uv',
    args: ['run', 'python', 'main.py'],
    env: { APP_MODE: mode },
  });

  // Wait for port to come up
  for (let i = 0; i < 30; i++) {
    await sleep(1000);
    if (await portInUse(port)) {
      ok(`Backend started on port ${port}`);
      return;
    }
  }
  warn(`Backend may still be starting (port ${port} not responding after 30s)`);
}

async function startWeb(mode, port) {
  const inUse = await portInUse(port);
  if (inUse) {
    const pid = findPidOnPort(port);
    warn(`Web port ${port} already in use` + (pid ? ` (PID ${pid})` : ''));
    return;
  }

  info(`Starting web frontend on port ${port} (mode=${mode})...`);
  spawnService({
    mode,
    title: `RAG-Web (${mode})`,
    cwd: WEB_DIR,
    command: 'node',
    args: ['start.mjs'],
    env: { APP_MODE: mode, WEB_PORT: String(port) },
  });

  for (let i = 0; i < 20; i++) {
    await sleep(1000);
    if (await portInUse(port)) {
      ok(`Web frontend started on port ${port}`);
      return;
    }
  }
  warn(`Web frontend may still be starting (port ${port} not responding after 20s)`);
}

async function startNeo4j() {
  const composeFile = path.join(PROJECT_ROOT, 'docker-compose.yml');
  if (!fs.existsSync(composeFile)) {
    warn('docker-compose.yml not found');
    return;
  }

  try {
    const result = await runExec('docker compose up -d neo4j', { cwd: PROJECT_ROOT });
    if (result.code === 0) {
      ok('Neo4j container started');
    } else {
      err(`Failed to start Neo4j: ${result.stderr}`);
    }
  } catch {
    warn('Docker not found - skipping Neo4j');
  }
}

async function startMcp(mode) {
  mode = mode || getAppMode();
  info(`Starting MCP server (stdio mode, mode=${mode})...`);
  spawnService({
    mode,
    title: `RAG-MCP (${mode})`,
    cwd: MCP_DIR,
    command: 'uv',
    args: ['run', 'python', 'server.py'],
    env: { APP_MODE: mode },
  });
  if (mode === 'dev') {
    ok('MCP server launching in a new terminal window (stdio server — shows startup logs, then waits for client)');
  } else {
    ok('MCP server launched in background (prod mode)');
  }
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: stop
// ═══════════════════════════════════════════════════════════════════════

async function cmdStop(service) {
  const ports = getServicePorts();
  header(`Stopping ${service.toUpperCase()}`);

  if (service === 'backend' || service === 'all') {
    await stopBackend(ports.backend);
  }
  if (service === 'web' || service === 'all') {
    await stopWeb(ports.web);
  }
  if (service === 'neo4j' || service === 'all') {
    await stopNeo4j();
  }
  if (service === 'mcp' || service === 'all') {
    await stopMcp();
  }

  return 0;
}

async function stopBackend(port) {
  let stopped = false;
  const pid = findPidOnPort(port);
  if (pid) {
    info(`Stopping backend (PID ${pid}, port ${port})...`);
    if (killPid(pid, true)) {
      ok(`Backend stopped (PID ${pid})`);
      stopped = true;
    } else {
      err(`Failed to kill PID ${pid}`);
    }
  }

  const procs = findPythonProcesses('main.py');
  for (const p of procs) {
    if (p.cmd.toLowerCase().replace(/\\/g, '/').includes('backend')) {
      info(`Killing backend process PID ${p.pid}...`);
      killPid(p.pid, true);
      ok(`Killed PID ${p.pid}`);
      stopped = true;
    }
  }

  if (!stopped) warn('No backend process found');
}

async function stopWeb(port) {
  let stopped = false;
  const pid = findPidOnPort(port);
  if (pid) {
    info(`Stopping web (PID ${pid}, port ${port})...`);
    if (killPid(pid, true)) {
      ok(`Web stopped (PID ${pid})`);
      stopped = true;
    }
  }

  for (const keyword of ['nuxt', 'start.mjs']) {
    const procs = findNodeProcesses(keyword);
    for (const p of procs) {
      info(`Killing node process PID ${p.pid}...`);
      killPid(p.pid, true);
      ok(`Killed PID ${p.pid}`);
      stopped = true;
    }
  }

  if (!stopped) warn('No web process found');
}

async function stopNeo4j() {
  try {
    const result = await runExec('docker compose down', { cwd: PROJECT_ROOT });
    if (result.code === 0) {
      ok('Neo4j container stopped');
    } else {
      err(`Failed to stop Neo4j: ${result.stderr}`);
    }
  } catch {
    warn('Docker not found');
  }
}

async function stopMcp() {
  const procs = findPythonProcesses('server.py');
  for (const p of procs) {
    if (p.cmd.toLowerCase().replace(/\\/g, '/').includes('kb-mcp')) {
      info(`Killing MCP server PID ${p.pid}...`);
      killPid(p.pid, true);
      ok(`Killed PID ${p.pid}`);
      return;
    }
  }
  warn('No MCP server process found');
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: status
// ═══════════════════════════════════════════════════════════════════════

async function cmdStatus() {
  const ports = getServicePorts();
  const eff = getEffectiveConfig();

  header('Service Status');

  // Backend
  const backendPort = ports.backend;
  const backendUp = await portInUse(backendPort);
  const backendStatus = backendUp ? _c(C.GREEN, '* RUNNING') : _c(C.RED, 'o STOPPED');
  console.log(`  Backend  (port ${backendPort})  ${backendStatus}`);
  if (backendUp) {
    const { code, body } = await httpGet(`http://localhost:${backendPort}/api/v1/health`, 3000);
    if (code === 200) {
      try {
        const data = JSON.parse(body);
        console.log(`           Health: ${_c(C.GREEN, data.status || 'unknown')}`);
      } catch {}
    }
    const pid = findPidOnPort(backendPort);
    if (pid) console.log(`           PID: ${pid}`);
  }

  // Web
  const webPort = ports.web;
  const webUp = await portInUse(webPort);
  const webStatus = webUp ? _c(C.GREEN, '* RUNNING') : _c(C.RED, 'o STOPPED');
  console.log(`  Web      (port ${webPort})  ${webStatus}`);
  if (webUp) {
    const pid = findPidOnPort(webPort);
    if (pid) console.log(`           PID: ${pid}`);
  }

  // Neo4j
  const neo4jUp = await portInUse(7687);
  const neo4jStatus = neo4jUp ? _c(C.GREEN, '* RUNNING') : _c(C.RED, 'o STOPPED');
  console.log(`  Neo4j    (port 7687)  ${neo4jStatus}`);

  // MinerU
  if (backendUp) {
    const { code, body } = await httpGet(`http://localhost:${backendPort}/api/v1/mineru/status`, 5000);
    if (code === 200) {
      try {
        const data = JSON.parse(body);
        const mineruRunning = data.running ?? data.is_running;
        if (mineruRunning) {
          console.log(`  MinerU   (ephemeral)  ${_c(C.GREEN, '* RUNNING')} (port ${data.port || '?'})`);
        } else {
          console.log(`  MinerU   (ephemeral)  ${_c(C.YELLOW, 'o IDLE')}`);
        }
      } catch {
        console.log(`  MinerU   (ephemeral)  ${_c(C.GRAY, '? UNKNOWN')}`);
      }
    } else {
      console.log(`  MinerU   (ephemeral)  ${_c(C.GRAY, '? UNKNOWN')}`);
    }
  } else {
    console.log(`  MinerU   (ephemeral)  ${_c(C.GRAY, '? BACKEND DOWN')}`);
  }

  // MCP
  const mcpProcs = findPythonProcesses('server.py');
  const mcpRunning = mcpProcs.some(p => p.cmd.toLowerCase().replace(/\\/g, '/').includes('kb-mcp'));
  const mcpStatus = mcpRunning ? _c(C.GREEN, '* RUNNING') : _c(C.RED, 'o STOPPED');
  console.log(`  MCP      (stdio)      ${mcpStatus}`);

  // Config summary
  console.log();
  console.log(`  ${_c(C.GRAY, '-- Config --')}`);
  console.log(`  Mode:     ${eff.app_mode}`);
  console.log(`  Backend:  ${eff.backend_url || `http://localhost:${backendPort}`}`);
  console.log(`  Storage:  ${eff.tree_storage_path}`);
  console.log(`  Vector:   ${eff.vector_enabled ? 'enabled' : 'disabled'}`);
  console.log(`  Graph:    ${eff.graph_enabled ? 'enabled' : 'disabled'}`);
  console.log(`  MinerU:   ${eff.mineru_enabled ? 'enabled' : 'disabled'}`);

  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: restart
// ═══════════════════════════════════════════════════════════════════════

async function cmdRestart(service, mode) {
  mode = mode || getAppMode();
  const ports = getServicePorts();

  header(`Restarting ${service.toUpperCase()}`);

  if (service === 'backend' || service === 'all') {
    await stopBackend(ports.backend);
    await sleep(2000);
    await startBackend(mode, ports.backend);
  }
  if (service === 'web' || service === 'all') {
    await stopWeb(ports.web);
    await sleep(2000);
    await startWeb(mode, ports.web);
  }
  if (service === 'neo4j' || service === 'all') {
    await stopNeo4j();
    await sleep(2000);
    await startNeo4j();
  }

  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: config
// ═══════════════════════════════════════════════════════════════════════

async function cmdConfig(subcommand, args) {
  switch (subcommand) {
    case 'show': return await configShow();
    case 'get': return configGet(args[0]);
    case 'set': return await configSet(args[0], args[1]);
    case 'reload': return await configReload();
    case 'edit': return configEdit(args[0] || 'shared');
    default:
      err(`Unknown config subcommand: ${subcommand}`);
      console.log('  Available: show, get, set, reload, edit');
      return 1;
  }
}

function printDict(d, indent = 0) {
  const prefix = ' '.repeat(indent);
  for (const [k, v] of Object.entries(d)) {
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      console.log(`${prefix}${k}:`);
      printDict(v, indent + 2);
    } else if (Array.isArray(v)) {
      console.log(`${prefix}${k}:`);
      for (const item of v) console.log(`${prefix}  - ${item}`);
    } else if (typeof v === 'boolean') {
      console.log(`${prefix}${k}: ${v ? _c(C.GREEN, 'true') : _c(C.RED, 'false')}`);
    } else {
      console.log(`${prefix}${k}: ${v}`);
    }
  }
}

async function configShow() {
  header('Current Configuration');
  const cfg = getConfig();
  const env = readEnv(ENV_FILE);
  const eff = getEffectiveConfig();

  console.log(`\n  ${_c(C.CYAN, '-- config.yml --')}`);
  printDict(cfg, 2);

  console.log(`\n  ${_c(C.CYAN, '-- .env --')}`);
  for (const [k, v] of Object.entries(env)) {
    let displayV = v;
    if (k.toUpperCase().includes('PASSWORD') || k.toUpperCase().includes('SECRET')) {
      displayV = '*'.repeat(v.length);
    }
    console.log(`  ${k} = ${displayV}`);
  }

  console.log(`\n  ${_c(C.CYAN, '-- Effective Values --')}`);
  for (const [k, v] of Object.entries(eff)) {
    let displayV = v;
    if (typeof v === 'boolean') {
      displayV = v ? _c(C.GREEN, 'yes') : _c(C.RED, 'no');
    }
    console.log(`  ${k}: ${displayV}`);
  }

  return 0;
}

function configGet(key) {
  if (!key) {
    err('Usage: config get <key>');
    return 1;
  }

  const cfg = getConfig();
  const env = readEnv(ENV_FILE);

  // Try env first
  if (key in env) {
    console.log(env[key]);
    return 0;
  }

  // Try nested config key
  const parts = key.split('.');
  let val = cfg;
  for (const part of parts) {
    if (val && typeof val === 'object') {
      val = val[part];
    } else {
      val = undefined;
      break;
    }
  }

  if (val !== undefined && val !== null) {
    if (typeof val === 'object') {
      console.log(JSON.stringify(val, null, 2));
    } else {
      console.log(val);
    }
    return 0;
  }

  err(`Key '${key}' not found in config or .env`);
  return 1;
}

async function configSet(key, value) {
  if (!key || value === undefined) {
    err('Usage: config set <key> <value>');
    return 1;
  }

  const env = readEnv(ENV_FILE);
  const knownEnvVars = new Set(['APP_MODE', 'BACKEND_PORT', 'WEB_PORT', 'TREE_STORAGE_PATH',
    'NEO4J_PASSWORD', 'NO_RELOAD', 'PYTHONUTF8', 'BACKEND_URL']);

  if (knownEnvVars.has(key) || /^[A-Z_]+$/.test(key)) {
    // Set in .env
    env[key] = value;
    writeEnv(env);
    ok(`Set ${key}=${value} in .env`);

    // Hot-reload
    const ports = getServicePorts();
    if (await portInUse(ports.backend)) {
      const { code } = await httpRequest(
        `http://localhost:${ports.backend}/api/v1/config`,
        'PUT',
        { config: {}, env }
      );
      if (code === 200) ok('Hot-reloaded via backend API');
      else warn('Backend did not accept reload (may need restart)');
    }
    return 0;
  }

  // Set in config.yml
  const cfg = getConfig();
  const parts = key.split('.');
  let cursor = cfg;
  for (const part of parts.slice(0, -1)) {
    if (!cursor[part] || typeof cursor[part] !== 'object') cursor[part] = {};
    cursor = cursor[part];
  }

  // Auto-convert value
  if (value === 'true') cursor[parts[parts.length - 1]] = true;
  else if (value === 'false') cursor[parts[parts.length - 1]] = false;
  else if (/^\d+$/.test(value)) cursor[parts[parts.length - 1]] = parseInt(value);
  else {
    try { cursor[parts[parts.length - 1]] = parseFloat(value); }
    catch { cursor[parts[parts.length - 1]] = value; }
  }

  const sharedSections = new Set(['server', 'storage', 'vector', 'embedding', 'graph', 'search']);
  if (sharedSections.has(parts[0])) {
    const sharedData = {};
    for (const k of sharedSections) {
      if (cfg[k]) sharedData[k] = cfg[k];
    }
    const header = `# ============================================
# RAG Knowledge Platform - Shared Configuration
# ============================================
# Single source of truth for ports and shared settings.
# Env vars in .env override values here.
# ============================================

`;
    const content = header + yaml.dump(sharedData, { lineWidth: -1, noRefs: true });
    fs.writeFileSync(CONFIG_YML, content, 'utf8');
    ok(`Set ${key}=${value} in config.yml`);
  } else if (parts[0] === 'mineru') {
    const mineruHeader = `# ============================================
# MinerU OCR / PDF Engine Configuration
# ============================================

`;
    const content = mineruHeader + yaml.dump({ mineru: cfg.mineru }, { lineWidth: -1, noRefs: true });
    fs.writeFileSync(BACKEND_CONFIG_YML, content, 'utf8');
    ok(`Set ${key}=${value} in backend/config.yml`);
  } else {
    err(`Unknown config section: ${parts[0]}`);
    return 1;
  }

  // Hot-reload
  const ports = getServicePorts();
  if (await portInUse(ports.backend)) {
    const { code } = await httpRequest(
      `http://localhost:${ports.backend}/api/v1/config`,
      'PUT',
      { config: cfg, env: {} }
    );
    if (code === 200) ok('Hot-reloaded via backend API');
    else warn('Backend did not accept reload (may need restart)');
  }

  return 0;
}

async function configReload() {
  const ports = getServicePorts();
  if (!(await portInUse(ports.backend))) {
    err('Backend is not running - cannot reload');
    return 1;
  }

  const { code, body } = await httpRequest(
    `http://localhost:${ports.backend}/api/v1/config/reload`,
    'POST'
  );
  if (code === 200) {
    try {
      const data = JSON.parse(body);
      ok(data.message || 'Configuration reloaded');
      if (data.effective) {
        console.log(`\n  ${_c(C.CYAN, 'Effective values:')}`);
        for (const [k, v] of Object.entries(data.effective)) {
          console.log(`  ${k}: ${v}`);
        }
      }
    } catch {
      ok('Configuration reloaded');
    }
    return 0;
  } else {
    err(`Reload failed: ${body}`);
    return 1;
  }
}

function configEdit(target) {
  let filePath;
  if (target === 'shared' || target === 'config') {
    filePath = CONFIG_YML;
  } else if (target === 'backend' || target === 'mineru') {
    filePath = BACKEND_CONFIG_YML;
  } else if (target === 'env') {
    filePath = ENV_FILE;
  } else {
    err(`Unknown config target: ${target}`);
    return 1;
  }

  const editor = process.env.EDITOR || (IS_WIN ? 'notepad' : 'nano');
  info(`Opening ${filePath} with ${editor}...`);
  spawn(editor, [filePath], { stdio: 'inherit', shell: true });
  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: health
// ═══════════════════════════════════════════════════════════════════════

async function cmdHealth() {
  const ports = getServicePorts();
  let allHealthy = true;

  header('Health Check');

  // Backend
  const backendPort = ports.backend;
  if (await portInUse(backendPort)) {
    const { code, body } = await httpGet(`http://localhost:${backendPort}/api/v1/health`, 5000);
    if (code === 200) {
      try {
        const data = JSON.parse(body);
        ok(`Backend  : ${data.status || 'unknown'}`);
      } catch {
        ok(`Backend  : responding (port ${backendPort})`);
      }
    } else {
      warn(`Backend  : port open but health check failed (HTTP ${code})`);
      allHealthy = false;
    }
  } else {
    err(`Backend  : NOT RUNNING (port ${backendPort})`);
    allHealthy = false;
  }

  // Web
  const webPort = ports.web;
  if (await portInUse(webPort)) {
    const { code } = await httpGet(`http://localhost:${webPort}/`, 5000);
    if (code > 0) {
      ok(`Web      : responding (port ${webPort})`);
    } else {
      warn('Web      : port open but not responding');
      allHealthy = false;
    }
  } else {
    err(`Web      : NOT RUNNING (port ${webPort})`);
    allHealthy = false;
  }

  // Neo4j
  if (await portInUse(7687)) {
    ok('Neo4j    : port 7687 open');
  } else {
    warn('Neo4j    : NOT RUNNING (port 7687)');
    allHealthy = false;
  }

  // Config endpoint
  if (await portInUse(backendPort)) {
    const { code } = await httpGet(`http://localhost:${backendPort}/api/v1/config`, 5000);
    if (code === 200) {
      ok('Config   : API accessible');
    } else {
      warn('Config   : API not responding');
      allHealthy = false;
    }
  }

  // MinerU
  if (await portInUse(backendPort)) {
    const { code, body } = await httpGet(`http://localhost:${backendPort}/api/v1/mineru/status`, 5000);
    if (code === 200) {
      try {
        const data = JSON.parse(body);
        if (data.running ?? data.is_running) {
          ok(`MinerU   : running (port ${data.port || '?'})`);
        } else {
          warn(`MinerU   : not running (idle)`);
        }
      } catch {
        warn('MinerU   : status parse error');
      }
    } else {
      warn('MinerU   : status endpoint not responding');
    }
  }

  console.log();
  if (allHealthy) {
    ok(_c(C.BOLD, 'All critical services are healthy!'));
  } else {
    err(_c(C.BOLD, 'Some services need attention.'));
    console.log(`  ${_c(C.GRAY, 'Run: ragctl doctor')} for diagnostics`);
  }

  return allHealthy ? 0 : 1;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: init  (一键初始化 — 首次运行)
// ═══════════════════════════════════════════════════════════════════════

async function cmdInit() {
  header('Initializing RAG Knowledge Platform');

  let step = 0;
  const totalSteps = 7;
  let failed = false;

  function stepOk(msg) { step++; ok(`[${step}/${totalSteps}] ${msg}`); }
  function stepWarn(msg) { step++; warn(`[${step}/${totalSteps}] ${msg}`); }
  function stepErr(msg) { step++; err(`[${step}/${totalSteps}] ${msg}`); failed = true; }

  // Step 1: Check prerequisites
  stepOk('Checking prerequisites...');
  const checks = [
    { cmd: 'uv', name: 'uv (Python package manager)', url: 'https://docs.astral.sh/uv/' },
    { cmd: 'node', name: 'Node.js 18+', url: 'https://nodejs.org/' },
    { cmd: 'npm', name: 'npm', url: 'https://nodejs.org/' },
  ];
  for (const { cmd, name, url } of checks) {
    if (commandExists(cmd)) {
      console.log(`         ${_c(C.GREEN, '✓')} ${name}`);
    } else {
      console.log(`         ${_c(C.RED, '✗')} ${name} — install from ${url}`);
      failed = true;
    }
  }
  // Docker is optional
  if (commandExists('docker')) {
    console.log(`         ${_c(C.GREEN, '✓')} Docker (for Neo4j graph)`);
  } else {
    console.log(`         ${_c(C.YELLOW, '○')} Docker not found — graph features need Neo4j`);
  }

  // Step 2: Submodules
  stepOk('Initializing git submodules...');
  if (fs.existsSync(path.join(BACKEND_DIR, 'app', 'main.py')) &&
      fs.existsSync(path.join(WEB_DIR, 'package.json'))) {
    console.log('         Already initialized');
  } else {
    const result = await runExec('git submodule update --init --recursive');
    if (result.code === 0) {
      console.log('         Done');
    } else {
      stepErr(`Submodule init failed: ${result.stderr}`);
      return 1;
    }
  }

  // Step 3: Setup .env
  stepOk('Setting up environment...');
  if (!fs.existsSync(ENV_FILE)) {
    const examplePath = path.join(PROJECT_ROOT, '.env.example');
    if (fs.existsSync(examplePath)) {
      fs.copyFileSync(examplePath, ENV_FILE);
      console.log('         .env created from .env.example');
    } else {
      writeEnv({ APP_MODE: 'dev', PYTHONUTF8: '1' });
      console.log('         .env created with defaults');
    }
  } else {
    console.log('         .env already exists');
  }

  // Step 4: Install command/ragctl deps
  stepOk('Installing CLI dependencies...');
  if (!fs.existsSync(path.join(PROJECT_ROOT, 'command', 'node_modules'))) {
    const result = await runExec('npm install --silent', { cwd: path.join(PROJECT_ROOT, 'command') });
    if (result.code === 0) {
      console.log('         Done (js-yaml)');
    } else {
      stepErr(`CLI deps install failed: ${result.stderr}`);
    }
  } else {
    console.log('         Already installed');
  }

  // Step 5: Install backend deps
  stepOk('Installing backend dependencies (uv sync)...');
  if (fs.existsSync(path.join(BACKEND_DIR, 'uv.lock')) || fs.existsSync(path.join(BACKEND_DIR, '.venv'))) {
    console.log('         Running uv sync (incremental)...');
  } else {
    console.log('         First install — this may take a few minutes...');
  }
  const backendResult = await runExec('uv sync', { cwd: BACKEND_DIR, timeout: 600000 });
  if (backendResult.code === 0) {
    console.log('         Done');
  } else {
    stepErr(`Backend install failed: ${backendResult.stderr}`);
  }

  // Step 6: Install web deps
  stepOk('Installing web dependencies (npm install)...');
  if (fs.existsSync(path.join(WEB_DIR, 'node_modules'))) {
    console.log('         Already installed');
  } else {
    console.log('         First install — this may take a few minutes...');
    const webResult = await runExec('npm install', { cwd: WEB_DIR, timeout: 600000 });
    if (webResult.code === 0) {
      console.log('         Done');
    } else {
      stepErr(`Web install failed: ${webResult.stderr}`);
    }
  }

  // Step 7: Install kb-mcp deps
  stepOk('Installing MCP server dependencies (uv sync)...');
  if (fs.existsSync(path.join(MCP_DIR, 'uv.lock')) || fs.existsSync(path.join(MCP_DIR, '.venv'))) {
    console.log('         Running uv sync (incremental)...');
  }
  const mcpResult = await runExec('uv sync', { cwd: MCP_DIR, timeout: 300000 });
  if (mcpResult.code === 0) {
    console.log('         Done');
  } else {
    stepErr(`MCP install failed: ${mcpResult.stderr}`);
  }

  console.log();
  if (failed) {
    err(_c(C.BOLD, 'Some steps failed. Fix the issues above and run `ragctl init` again.'));
    return 1;
  }

  ok(_c(C.BOLD, 'Initialization complete!'));
  console.log();
  console.log(`  ${_c(C.CYAN, 'Next steps:')}`);
  console.log(`    ragctl up          Start all services (Neo4j → Backend → Web)`);
  console.log(`    ragctl status      Check service status`);
  console.log(`    ragctl health      Full health check`);
  console.log(`    ragctl doctor      Run diagnostics`);
  console.log();
  console.log(`  ${_c(C.GRAY, 'Or open the web UI:')} http://localhost:${getServicePorts().web}`);
  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: up / down  (全栈一键启动 / 停止)
// ═══════════════════════════════════════════════════════════════════════

async function cmdUp(mode) {
  mode = mode || getAppMode();
  const ports = getServicePorts();

  header(`Starting RAG Knowledge Platform (mode=${mode})`);

  // 1. Neo4j (if docker available)
  const composeFile = path.join(PROJECT_ROOT, 'docker-compose.yml');
  if (fs.existsSync(composeFile)) {
    if (!(await portInUse(7687))) {
      info('Starting Neo4j...');
      await startNeo4j();
    } else {
      info('Neo4j already running on port 7687');
    }
  }

  // Give Neo4j a moment
  await sleep(2000);

  // 2. Backend
  if (await portInUse(ports.backend)) {
    warn(`Backend already running on port ${ports.backend}`);
  } else {
    info(`Starting Backend on port ${ports.backend}...`);
    spawnService({
      mode,
      title: `RAG-Backend (${mode})`,
      cwd: BACKEND_DIR,
      command: 'uv',
      args: ['run', 'python', 'main.py'],
      env: { APP_MODE: mode },
    });
    for (let i = 0; i < 30; i++) {
      await sleep(1000);
      if (await portInUse(ports.backend)) { ok(`Backend ready on port ${ports.backend}`); break; }
    }
  }

  // 3. Web
  if (await portInUse(ports.web)) {
    warn(`Web already running on port ${ports.web}`);
  } else {
    info(`Starting Web on port ${ports.web}...`);
    spawnService({
      mode,
      title: `RAG-Web (${mode})`,
      cwd: WEB_DIR,
      command: 'node',
      args: ['start.mjs'],
      env: { APP_MODE: mode, WEB_PORT: String(ports.web) },
    });
    for (let i = 0; i < 20; i++) {
      await sleep(1000);
      if (await portInUse(ports.web)) { ok(`Web ready on port ${ports.web}`); break; }
    }
  }

  console.log();
  ok(_c(C.BOLD, 'All services started!'));
  console.log(`  Backend:  http://localhost:${ports.backend}`);
  console.log(`  Web UI:   http://localhost:${ports.web}`);
  console.log(`  Neo4j:    bolt://localhost:7687`);
  return 0;
}

async function cmdDown() {
  const ports = getServicePorts();

  header('Stopping RAG Knowledge Platform');

  // Stop web first (depends on backend)
  if (await portInUse(ports.web)) {
    info(`Stopping Web on port ${ports.web}...`);
    await stopWeb(ports.web);
    // Wait for port release
    for (let i = 0; i < 10; i++) {
      await sleep(500);
      if (!(await portInUse(ports.web))) { ok('Web stopped'); break; }
    }
  } else {
    info('Web not running');
  }

  // Stop backend
  if (await portInUse(ports.backend)) {
    info(`Stopping Backend on port ${ports.backend}...`);
    await stopBackend(ports.backend);
    for (let i = 0; i < 10; i++) {
      await sleep(500);
      if (!(await portInUse(ports.backend))) { ok('Backend stopped'); break; }
    }
  } else {
    info('Backend not running');
  }

  // Stop Neo4j (optional — user may want to keep it)
  if (await portInUse(7687)) {
    info('Stopping Neo4j...');
    await stopNeo4j();
    ok('Neo4j stopped');
  }

  console.log();
  ok(_c(C.BOLD, 'All services stopped.'));
  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: doctor
// ═══════════════════════════════════════════════════════════════════════

async function cmdDoctor() {
  header('Diagnostics');
  let issues = 0;

  // Check Python (try python3 first on Linux, then python)
  let pythonOk = false;
  for (const pyCmd of ['python3', 'python']) {
    try {
      const result = await runExec(`${pyCmd} --version`);
      if (result.code === 0) {
        ok(`Python: ${result.stdout.trim()} (${pyCmd})`);
        pythonOk = true;
        break;
      }
    } catch {}
  }
  if (!pythonOk) { err('Python: not found'); issues++; }

  // Check uv
  try {
    const result = await runExec('uv --version');
    if (result.code === 0) ok(`uv: ${result.stdout.trim()}`);
    else { err('uv: not found (install from https://docs.astral.sh/uv/)'); issues++; }
  } catch { err('uv: not found'); issues++; }

  // Check Node.js
  ok(`Node.js: ${process.version}`);

  // Check npm
  try {
    const result = await runExec('npm --version');
    if (result.code === 0) ok(`npm: ${result.stdout.trim()}`);
    else { err('npm: not found'); issues++; }
  } catch { err('npm: not found'); issues++; }

  // Check Docker
  try {
    const result = await runExec('docker --version');
    if (result.code === 0) ok(`Docker: ${result.stdout.trim()}`);
    else warn('Docker: not found (Neo4j requires Docker)');
  } catch { warn('Docker: not found (Neo4j requires Docker)'); }

  // Check config files
  console.log();
  if (fs.existsSync(CONFIG_YML)) ok(`config.yml: exists (${CONFIG_YML})`);
  else { err('config.yml: MISSING'); issues++; }

  if (fs.existsSync(BACKEND_CONFIG_YML)) ok('backend/config.yml: exists');
  else { err('backend/config.yml: MISSING'); issues++; }

  if (fs.existsSync(ENV_FILE)) ok('.env: exists');
  else { warn('.env: not found (run: ragctl init to create from template)'); issues++; }

  // Check .env.example
  const examplePath = path.join(PROJECT_ROOT, '.env.example');
  if (fs.existsSync(examplePath)) {
    ok('.env.example: exists (template for new installs)');
  } else {
    warn('.env.example: not found (file missing)');
    issues++;
  }

  // Check submodules
  console.log();
  if (fs.existsSync(path.join(BACKEND_DIR, 'app', 'main.py'))) {
    ok('Backend submodule: initialized');
  } else {
    err('Backend submodule: NOT initialized (run: git submodule update --init --recursive)');
    issues++;
  }

  if (fs.existsSync(path.join(WEB_DIR, 'package.json'))) {
    ok('Web submodule: initialized');
  } else {
    err('Web submodule: NOT initialized (run: git submodule update --init --recursive)');
    issues++;
  }

  // Check dependencies
  console.log();
  if (fs.existsSync(path.join(BACKEND_DIR, '.venv')) || fs.existsSync(path.join(BACKEND_DIR, 'uv.lock'))) {
    ok('Backend deps: installed (or lockfile present)');
  } else {
    warn('Backend deps: not installed (run: ragctl install backend)');
    issues++;
  }

  if (fs.existsSync(path.join(WEB_DIR, 'node_modules'))) {
    ok('Web deps: installed');
  } else {
    warn('Web deps: not installed (run: ragctl install web)');
    issues++;
  }

  if (fs.existsSync(path.join(MCP_DIR, '.venv')) || fs.existsSync(path.join(MCP_DIR, 'uv.lock'))) {
    ok('MCP deps: installed (or lockfile present)');
  } else {
    warn('MCP deps: not installed (run: ragctl install mcp)');
    issues++;
  }

  if (!fs.existsSync(path.join(PROJECT_ROOT, 'command', 'node_modules'))) {
    warn('CLI deps: not installed (run: cd command && npm install)');
    issues++;
  }

  // Check port conflicts
  console.log();
  const ports = getServicePorts();
  for (const [name, port] of Object.entries(ports)) {
    if (await portInUse(port)) {
      const pid = findPidOnPort(port);
      warn(`Port ${port} (${name}): in use` + (pid ? ` by PID ${pid}` : ''));
    } else {
      ok(`Port ${port} (${name}): free`);
    }
  }

  // Config consistency
  console.log();
  const eff = getEffectiveConfig();
  if (eff.backend_url && eff.backend_port) {
    const expectedUrl = `http://localhost:${eff.backend_port}`;
    if (eff.backend_url !== expectedUrl) {
      warn(`backend_url mismatch: config=${eff.backend_url}, expected=${expectedUrl}`);
      issues++;
    } else {
      ok('backend_url matches backend_port');
    }
  } else {
    warn('backend_url or backend_port is empty');
    issues++;
  }

  console.log();
  if (issues === 0) {
    ok(_c(C.BOLD, 'No issues found! System looks healthy.'));
  } else {
    warn(_c(C.BOLD, `${issues} issue(s) found. See above for details.`));
  }

  return issues === 0 ? 0 : 1;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: logs
// ═══════════════════════════════════════════════════════════════════════

async function cmdLogs(service, lines) {
  lines = lines || 50;

  const logPaths = {
    backend: [
      path.join(BACKEND_DIR, 'logs', 'backend-8765.log'),
      path.join(BACKEND_DIR, 'logs', 'backend-8766.log'),
      path.join(BACKEND_DIR, 'backend.log'),
    ],
    mineru: [
      path.join(BACKEND_DIR, 'logs', 'mineru-api.log'),
    ],
    web: [
      path.join(WEB_DIR, 'web-start.log'),
      path.join(WEB_DIR, 'web-start-err.log'),
    ],
  };

  if (!(service in logPaths)) {
    err(`Unknown service: ${service}. Available: ${Object.keys(logPaths).join(', ')}`);
    return 1;
  }

  let found = false;
  for (const logPath of logPaths[service]) {
    if (fs.existsSync(logPath)) {
      found = true;
      console.log(`\n  ${_c(C.CYAN, `-- ${logPath} --`)}`);
      try {
        const content = fs.readFileSync(logPath, 'utf8');
        const allLines = content.split('\n');
        const tail = allLines.slice(-lines);
        for (const line of tail) {
          console.log(`  ${line}`);
        }
      } catch (e) {
        err(`Failed to read ${logPath}: ${e.message}`);
      }
    }
  }

  if (!found) {
    warn(`No log files found for ${service}`);
    return 1;
  }

  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: install
// ═══════════════════════════════════════════════════════════════════════

async function cmdInstall(target) {
  header(`Installing ${target}`);

  if (target === 'backend' || target === 'all') {
    info('Installing backend dependencies...');
    const result = await runExec('uv sync', { cwd: BACKEND_DIR });
    if (result.code === 0) ok('Backend dependencies installed');
    else err(`Backend install failed: ${result.stderr}`);
  }

  if (target === 'web' || target === 'all') {
    info('Installing web dependencies...');
    const result = await runExec('npm install', { cwd: WEB_DIR });
    if (result.code === 0) ok('Web dependencies installed');
    else err(`Web install failed: ${result.stderr}`);
  }

  if (target === 'mcp' || target === 'all') {
    info('Installing MCP dependencies...');
    const result = await runExec('uv sync', { cwd: MCP_DIR });
    if (result.code === 0) ok('MCP dependencies installed');
    else err(`MCP install failed: ${result.stderr}`);
  }

  if (target === 'neo4j') {
    info('Starting Neo4j container...');
    await startNeo4j();
  }

  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: test
// ═══════════════════════════════════════════════════════════════════════

async function cmdTest(target, integration) {
  header(`Testing ${target}`);

  if (target === 'backend' || target === 'all') {
    const cmd = integration ? 'uv run pytest --run-integration' : 'uv run pytest -x';
    info(`Running: ${cmd}`);
    const result = await runExec(cmd, { cwd: BACKEND_DIR, timeout: 600000 });
    if (result.stdout) process.stdout.write(result.stdout);
    if (result.stderr) process.stderr.write(result.stderr);
    if (result.code !== 0 && target === 'all') {
      warn('Backend tests failed, continuing...');
    } else if (result.code !== 0) {
      err(`Backend tests failed (exit ${result.code})`);
    } else {
      ok('Backend tests passed');
    }
  }

  if (target === 'web' || target === 'all') {
    info('Running web type checks...');
    const webResult = await runExec('npx nuxi typecheck', { cwd: WEB_DIR, timeout: 300000 });
    if (webResult.stdout) process.stdout.write(webResult.stdout);
    if (webResult.stderr) process.stderr.write(webResult.stderr);
  }

  if (target === 'mcp' || target === 'all') {
    const cmd = integration ? 'uv run pytest --run-integration' : 'uv run pytest -x';
    info(`Running: ${cmd}`);
    const mcpResult = await runExec(cmd, { cwd: MCP_DIR, timeout: 600000 });
    if (mcpResult.stdout) process.stdout.write(mcpResult.stdout);
    if (mcpResult.stderr) process.stderr.write(mcpResult.stderr);
    if (mcpResult.code !== 0) err(`MCP tests failed (exit ${mcpResult.code})`); else ok('MCP tests passed');
  }

  return 0;
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: mcp
// ═══════════════════════════════════════════════════════════════════════

async function cmdMcp(subcommand) {
  switch (subcommand) {
    case 'start':
      await startMcp();
      return 0;
    case 'stop':
      await stopMcp();
      return 0;
    case 'status': {
      const procs = findPythonProcesses('server.py');
      const mcpProcs = procs.filter(p =>
        p.cmd.toLowerCase().replace(/\\/g, '/').includes('kb-mcp')
      );
      if (mcpProcs.length > 0) {
        for (const p of mcpProcs) ok(`MCP server running (PID ${p.pid})`);
      } else {
        warn('MCP server not running');
      }
      return 0;
    }
    case 'tools': {
      info('MCP tools (from server.py):');
      const serverPath = path.join(MCP_DIR, 'server.py');
      if (fs.existsSync(serverPath)) {
        const content = fs.readFileSync(serverPath, 'utf8');
        const toolRegex = /@mcp\.tool\(\)\s*\n(?:async\s+)?def\s+(\w+)/g;
        const tools = [];
        let match;
        while ((match = toolRegex.exec(content)) !== null) {
          tools.push(match[1]);
        }
        if (tools.length > 0) {
          for (const t of tools) console.log(`  - ${t}`);
          console.log(`\n  Total: ${tools.length} tools`);
        } else {
          warn('No tools found in server.py');
        }
      } else {
        err('server.py not found');
      }
      return 0;
    }
    default:
      err(`Unknown mcp subcommand: ${subcommand}`);
      console.log('  Available: start, stop, status, tools');
      return 1;
  }
}

// ═══════════════════════════════════════════════════════════════════════
//  COMMAND: kb
// ═══════════════════════════════════════════════════════════════════════

async function cmdKb(subcommand, query) {
  const ports = getServicePorts();

  if (!(await portInUse(ports.backend))) {
    err('Backend is not running. Start it with: ragctl start backend');
    return 1;
  }

  const baseUrl = `http://localhost:${ports.backend}`;
  const webUrl = (await portInUse(ports.web)) ? `http://localhost:${ports.web}` : null;

  if (subcommand === 'list') {
    let url = webUrl ? `${webUrl}/api/kb/catalog` : `${baseUrl}/api/v1/kb/list`;
    let { code, body } = await httpGet(url, 10000);
    if (code !== 200 && webUrl) {
      ({ code, body } = await httpGet(`${baseUrl}/api/v1/kb/list`, 10000));
    }
    if (code === 200) {
      const data = JSON.parse(body);
      let kbs = Array.isArray(data) ? data : (data.knowledgeBases || data.kbs || data.data || []);
      if (!Array.isArray(kbs) && typeof kbs === 'object') kbs = Object.values(kbs);
      header(`Knowledge Bases (${kbs.length})`);
      for (const kb of kbs) {
        const name = kb.name || kb.kb_name || '?';
        const docCount = kb.documentCount || kb.doc_count || kb.document_count || '?';
        const desc = (kb.description || '').slice(0, 60);
        console.log(`  ${_c(C.CYAN, name)}  (${docCount} docs)  ${desc}`);
      }
      return 0;
    } else {
      err(`Failed to list KBs: ${body}`);
      return 1;
    }
  } else if (subcommand === 'search') {
    if (!query) {
      err('Usage: kb search <query>');
      return 1;
    }
    const encoded = encodeURIComponent(query);
    // web proxy exposes GET /api/kb/search?query=&top_k= (search.get.ts); backend has no equivalent endpoint
    const url = webUrl
      ? `${webUrl}/api/kb/search?query=${encoded}&top_k=10`
      : `${baseUrl}/api/v1/kb/search?query=${encoded}&top_k=10`;
    const { code, body } = await httpGet(url, 15000);
    if (code === 200) {
      const data = JSON.parse(body);
      const results = Array.isArray(data) ? data : (data.hits || data.results || data.data || []);
      header(`Search Results for '${query}' (${results.length})`);
      results.forEach((r, i) => {
        const name = r.docName || r.doc_name || r.name || '?';
        const kb = r.kbName || r.kb_name || r.kb || '?';
        const score = r.score ?? r.similarity ?? '?';
        const snippet = (r.description || r.snippet || r.content || '').slice(0, 100);
        console.log(`  ${i + 1}. ${_c(C.CYAN, name)} [${kb}] score=${score}`);
        if (snippet) console.log(`     ${_c(C.GRAY, snippet)}...`);
      });
      return 0;
    } else {
      err(`Search failed: ${body}`);
      return 1;
    }
  } else if (subcommand === 'stats') {
    let url = webUrl ? `${webUrl}/api/kb/catalog` : `${baseUrl}/api/v1/kb/list`;
    const { code, body } = await httpGet(url, 10000);
    if (code === 200) {
      const data = JSON.parse(body);
      let kbs = Array.isArray(data) ? data : (data.knowledgeBases || data.kbs || data.data || []);
      if (!Array.isArray(kbs) && typeof kbs === 'object') kbs = Object.values(kbs);
      header('KB Statistics');
      const totalDocs = kbs.reduce((sum, kb) => sum + (kb.documentCount || kb.doc_count || kb.document_count || 0), 0);
      console.log(`  Total KBs:       ${kbs.length}`);
      console.log(`  Total Documents: ${totalDocs}`);
      console.log();
      for (const kb of kbs) {
        const name = kb.name || kb.kb_name || '?';
        const docCount = kb.documentCount || kb.doc_count || kb.document_count || 0;
        const tags = kb.tags || [];
        console.log(`  ${name}: ${docCount} docs, ${tags.length} tags`);
      }
      return 0;
    } else {
      err(`Failed to get stats: ${body}`);
      return 1;
    }
  } else {
    err(`Unknown kb subcommand: ${subcommand}`);
    console.log('  Available: list, search, stats');
    return 1;
  }
}

// ═══════════════════════════════════════════════════════════════════════
//  Utilities
// ═══════════════════════════════════════════════════════════════════════

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function runExec(cmd, options = {}) {
  return new Promise((resolve) => {
    exec(cmd, {
      cwd: options.cwd || PROJECT_ROOT,
      timeout: options.timeout || 120000,
      env: { ...process.env, ...options.env },
    }, (error, stdout, stderr) => {
      if (error) {
        resolve({ code: error.code || 1, stdout: stdout || '', stderr: stderr || error.message });
      } else {
        resolve({ code: 0, stdout, stderr });
      }
    });
  });
}

// ═══════════════════════════════════════════════════════════════════════
//  CLI Argument Parser
// ═══════════════════════════════════════════════════════════════════════

function showHelp() {
  console.log(`
${_c(C.BOLD, 'ragctl')} — RAG Knowledge Platform CLI

${_c(C.CYAN, 'Usage:')}
  ragctl <command> [subcommand] [options]

${_c(C.CYAN, 'Commands:')}
  init     One-time setup: checks deps, installs everything, creates .env
  up       Start all services (Neo4j → Backend → Web)
  down     Stop all services
  start    Start specific service (backend, web, neo4j, mcp, all)
  stop     Stop specific service (backend, web, neo4j, mcp, all)
  status   Show service status
  restart  Restart services
  config   Configuration management (show, get, set, reload, edit)
  health   Health check for all services
  doctor   Diagnose common issues
  logs     View service logs
  install  Install dependencies (backend, web, mcp, all)
  test     Run tests (backend, web, mcp)
  mcp      MCP server management
  kb       Knowledge base quick operations

${_c(C.CYAN, 'Quick Start:')}
  ragctl init                   First time setup (installs everything)
  ragctl up                     Start all services
  ragctl status                 Check status
  ragctl health                 Full health check

${_c(C.CYAN, 'Examples:')}
  ragctl start all              Start all services (dev mode)
  ragctl start backend --mode prod  Start backend in prod mode
  ragctl stop all               Stop all services
  ragctl status                 Show service status
  ragctl config show            Show all configuration
  ragctl config set server.dev.backend_port 9000  Change backend port
  ragctl health                 Check all services
  ragctl doctor                 Diagnose common issues
  ragctl logs backend --lines 100  View last 100 lines of backend logs
  ragctl install all            Install all dependencies
  ragctl test backend           Run backend tests
  ragctl mcp tools              List MCP tools
  ragctl kb list                List knowledge bases
  ragctl kb search "vector search"  Search knowledge bases
`);
}

async function main() {
  // Windows: 切换控制台到 UTF-8 (chcp 65001)，避免中文/进程路径输出乱码
  if (IS_WIN) {
    try { require('child_process').execSync('chcp 65001 >nul 2>&1', { stdio: 'ignore' }); } catch {}
  }
  const args = process.argv.slice(2);
  const command = args[0];

  if (!command || command === 'help' || command === '--help' || command === '-h') {
    showHelp();
    return 0;
  }

  if (command === '--version' || command === '-V') {
    console.log('ragctl 1.0.0');
    return 0;
  }

  try {
    switch (command) {
      case 'start': {
        const service = args[1] || 'all';
        const validServices = ['backend', 'web', 'neo4j', 'mcp', 'all'];
        if (!validServices.includes(service)) {
          err(`Invalid service: ${service}. Available: ${validServices.join(', ')}`);
          return 1;
        }
        let mode = null;
        const modeIdx = args.indexOf('--mode');
        if (modeIdx !== -1 && args[modeIdx + 1]) mode = args[modeIdx + 1];
        if (mode && !['dev', 'prod'].includes(mode)) {
          err(`Invalid mode: ${mode}. Available: dev, prod`);
          return 1;
        }
        return await cmdStart(service, mode);
      }

      case 'stop': {
        const service = args[1] || 'all';
        const validServices = ['backend', 'web', 'neo4j', 'mcp', 'all'];
        if (!validServices.includes(service)) {
          err(`Invalid service: ${service}. Available: ${validServices.join(', ')}`);
          return 1;
        }
        return await cmdStop(service);
      }

      case 'status':
        return await cmdStatus();

      case 'restart': {
        const service = args[1] || 'all';
        const validServices = ['backend', 'web', 'neo4j', 'all'];
        if (!validServices.includes(service)) {
          err(`Invalid service: ${service}. Available: ${validServices.join(', ')}`);
          return 1;
        }
        let mode = null;
        const modeIdx = args.indexOf('--mode');
        if (modeIdx !== -1 && args[modeIdx + 1]) mode = args[modeIdx + 1];
        return await cmdRestart(service, mode);
      }

      case 'config': {
        const sub = args[1];
        if (!sub) {
          err('Usage: config <show|get|set|reload|edit> [args]');
          return 1;
        }
        return await cmdConfig(sub, args.slice(2));
      }

      case 'health':
        return await cmdHealth();

      case 'doctor':
        return await cmdDoctor();

      case 'init':
      case 'setup':
        return await cmdInit();

      case 'up':
      case 'start-all': {
        let mode = null;
        const modeIdx = args.indexOf('--mode');
        if (modeIdx !== -1 && args[modeIdx + 1]) mode = args[modeIdx + 1];
        return await cmdUp(mode);
      }

      case 'down':
      case 'stop-all':
        return await cmdDown();

      case 'logs': {
        const service = args[1] || 'backend';
        const validServices = ['backend', 'web', 'mineru'];
        if (!validServices.includes(service)) {
          err(`Invalid service: ${service}. Available: ${validServices.join(', ')}`);
          return 1;
        }
        let lines = 50;
        const linesIdx = args.indexOf('--lines');
        if (linesIdx !== -1 && args[linesIdx + 1]) lines = parseInt(args[linesIdx + 1]);
        const nIdx = args.indexOf('-n');
        if (nIdx !== -1 && args[nIdx + 1]) lines = parseInt(args[nIdx + 1]);
        return await cmdLogs(service, lines);
      }

      case 'install': {
        const target = args[1] || 'all';
        const validTargets = ['backend', 'web', 'mcp', 'neo4j', 'all'];
        if (!validTargets.includes(target)) {
          err(`Invalid target: ${target}. Available: ${validTargets.join(', ')}`);
          return 1;
        }
        return await cmdInstall(target);
      }

      case 'test': {
        const target = args[1] || 'backend';
        const validTargets = ['backend', 'web', 'mcp', 'all'];
        if (!validTargets.includes(target)) {
          err(`Invalid target: ${target}. Available: ${validTargets.join(', ')}`);
          return 1;
        }
        const integration = args.includes('--integration') || args.includes('-i');
        return await cmdTest(target, integration);
      }

      case 'mcp': {
        const sub = args[1];
        if (!sub) {
          err('Usage: mcp <start|stop|status|tools>');
          return 1;
        }
        return await cmdMcp(sub);
      }

      case 'kb': {
        const sub = args[1];
        if (!sub) {
          err('Usage: kb <list|search|stats> [query]');
          return 1;
        }
        return await cmdKb(sub, args.slice(2).join(' '));
      }

      default:
        err(`Unknown command: ${command}`);
        showHelp();
        return 1;
    }
  } catch (e) {
    if (e.message === 'INTERRUPTED') {
      console.log(`\n  ${_c(C.YELLOW, '[INTERRUPTED]')} Operation cancelled.`);
      return 130;
    }
    err(`Unexpected error: ${e.message}`);
    console.error(e.stack);
    return 1;
  }
}

// ── Entry Point ────────────────────────────────────────────────────────

process.on('SIGINT', () => {
  console.log(`\n  ${_c(C.YELLOW, '[INTERRUPTED]')} Operation cancelled.`);
  process.exit(130);
});

main().then(exitCode => {
  process.exit(exitCode);
}).catch(e => {
  err(`Unhandled error: ${e.message}`);
  console.error(e.stack);
  process.exit(1);
});