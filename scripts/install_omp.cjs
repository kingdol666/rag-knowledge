#!/usr/bin/env node
/**
 * OMP (Oh My Pi) Global Installer for RAG Knowledge Platform
 *
 * Copies skills, agent, commands, and MCP config to ~/.omp/agent/ so that
 * the knowledge base system is available globally in every OMP session.
 *
 * Usage:
 *   node scripts/install_omp.cjs                    # interactive
 *   node scripts/install_omp.cjs --path /custom/dir # specify project path
 *   node scripts/install_omp.cjs --uninstall        # remove OMP globals
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const OMP_AGENT_DIR = path.join(os.homedir(), '.omp', 'agent');

// --- Helpers ---
function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function copyDir(src, dst) {
  if (!fs.existsSync(src)) return false;
  ensureDir(dst);
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dst, entry.name);
    if (entry.isDirectory()) {
      copyDir(s, d);
    } else if (entry.isFile()) {
      fs.copyFileSync(s, d);
    }
  }
  return true;
}

function removeDir(dir) {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function log(msg) { console.log(`  ${msg}`); }
function ok(msg) { console.log(`  ✅ ${msg}`); }
function warn(msg) { console.log(`  ⚠️  ${msg}`); }
function err(msg) { console.error(`  ❌ ${msg}`); }

// --- Main ---
const args = process.argv.slice(2);
const uninstall = args.includes('--uninstall');
const pathIdx = args.indexOf('--path');
const projectPath = pathIdx >= 0 && args[pathIdx + 1] ? args[pathIdx + 1] : ROOT;

console.log('');
console.log('  ═════════════════════════════════════════════════════');
console.log('  🚀 RAG Knowledge Platform — OMP Global Installer');
console.log('  ═════════════════════════════════════════════════════');
console.log('');

if (uninstall) {
  console.log('  Uninstalling OMP globals...\n');
  const targets = [
    ...fs.existsSync(path.join(OMP_AGENT_DIR, 'skills'))
      ? fs.readdirSync(path.join(OMP_AGENT_DIR, 'skills'))
          .filter(d => d.startsWith('knowledgebase'))
          .map(d => path.join(OMP_AGENT_DIR, 'skills', d))
      : [],
    path.join(OMP_AGENT_DIR, 'agents', 'archival.md'),
    path.join(OMP_AGENT_DIR, 'commands', 'ragctl.md'),
  ];
  for (const t of targets) {
    if (fs.existsSync(t)) { removeDir(t); log(`Removed: ${path.relative(OMP_AGENT_DIR, t)}`); }
  }
  // Remove MCP config if it only contains kb-mcp
  const mcpFile = path.join(OMP_AGENT_DIR, 'mcp.json');
  if (fs.existsSync(mcpFile)) {
    try {
      const mcp = JSON.parse(fs.readFileSync(mcpFile, 'utf8'));
      if (mcp.mcpServers && mcp.mcpServers['kb-mcp'] && Object.keys(mcp.mcpServers).length === 1) {
        removeDir(mcpFile);
        log('Removed: mcp.json (was kb-mcp only)');
      } else if (mcp.mcpServers && mcp.mcpServers['kb-mcp']) {
        delete mcp.mcpServers['kb-mcp'];
        fs.writeFileSync(mcpFile, JSON.stringify(mcp, null, 2) + '\n');
        log('Removed kb-mcp from mcp.json (kept other servers)');
      }
    } catch { /* leave intact on parse error */ }
  }
  // Remove RAG_PROJECT_ROOT from .env
  const envFile = path.join(OMP_AGENT_DIR, '.env');
  if (fs.existsSync(envFile)) {
    const lines = fs.readFileSync(envFile, 'utf8').split('\n').filter(l => !l.startsWith('RAG_PROJECT_ROOT='));
    const nonEmpty = lines.filter(l => l.trim());
    if (nonEmpty.length > 0) {
      fs.writeFileSync(envFile, lines.join('\n').trimEnd() + '\n');
      log('Removed RAG_PROJECT_ROOT from .env (kept other vars)');
    } else {
      removeDir(envFile);
      log('Removed: .env (was RAG_PROJECT_ROOT only)');
    }
  }
  ok('OMP globals uninstalled.\n');
  process.exit(0);
}

console.log(`  Project root: ${projectPath}`);
console.log(`  OMP agent dir: ${OMP_AGENT_DIR}\n`);

// Verify project structure
const skillsSrc = path.join(projectPath, '.claude', 'skills');
const agentSrc = path.join(projectPath, '.omp', 'agents', 'archival.md');
const cmdSrc = path.join(projectPath, '.omp', 'commands', 'ragctl.md');
const kbMcpDir = path.join(projectPath, 'kb-mcp');

if (!fs.existsSync(skillsSrc)) { err(`Skills not found at ${skillsSrc}`); process.exit(1); }
if (!fs.existsSync(kbMcpDir)) { err(`kb-mcp directory not found at ${kbMcpDir}`); process.exit(1); }

// Step 1 — Copy skills
console.log('  Step 1: Installing skills...');
const skillsDest = path.join(OMP_AGENT_DIR, 'skills');
ensureDir(skillsDest);
const skillDirs = fs.readdirSync(skillsSrc, { withFileTypes: true })
  .filter(e => e.isDirectory() && e.name.startsWith('knowledgebase'))
  .map(e => e.name);
for (const skill of skillDirs) {
  copyDir(path.join(skillsSrc, skill), path.join(skillsDest, skill));
  log(`  ${skill}`);
}
ok(`${skillDirs.length} skills installed\n`);

// Step 2 — Copy Archival agent
console.log('  Step 2: Installing Archival agent...');
const agentDest = path.join(OMP_AGENT_DIR, 'agents');
ensureDir(agentDest);
if (fs.existsSync(agentSrc)) {
  fs.copyFileSync(agentSrc, path.join(agentDest, 'archival.md'));
  ok('archival.md installed\n');
} else {
  // Fallback: use Claude Code agent
  const claudeAgent = path.join(projectPath, '.claude', 'agents', 'knowledge-admin.md');
  if (fs.existsSync(claudeAgent)) {
    warn('OMP agent not found; copying Claude Code agent as fallback');
    fs.copyFileSync(claudeAgent, path.join(agentDest, 'archival.md'));
    ok('knowledge-admin.md installed as archival.md\n');
  } else {
    warn('No agent file found — skipping agent install\n');
  }
}

// Step 3 — Copy ragctl command
console.log('  Step 3: Installing ragctl command...');
const cmdDest = path.join(OMP_AGENT_DIR, 'commands');
ensureDir(cmdDest);
if (fs.existsSync(cmdSrc)) {
  fs.copyFileSync(cmdSrc, path.join(cmdDest, 'ragctl.md'));
  ok('ragctl command installed\n');
} else {
  const claudeCmd = path.join(projectPath, 'commands', 'ragctl.md');
  if (fs.existsSync(claudeCmd)) {
    fs.copyFileSync(claudeCmd, path.join(cmdDest, 'ragctl.md'));
    ok('ragctl command installed (from commands/)\n');
  }
}

// Step 4 — Write RAG_PROJECT_ROOT to ~/.omp/agent/.env (dynamic, not hardcoded)
console.log('  Step 4: Writing RAG_PROJECT_ROOT to .env...');
const envFile = path.join(OMP_AGENT_DIR, '.env');
const absProjectRoot = path.resolve(projectPath);
let envLines = [];
if (fs.existsSync(envFile)) {
  envLines = fs.readFileSync(envFile, 'utf8').split('\n').filter(l => l.trim() && !l.startsWith('RAG_PROJECT_ROOT='));
}
envLines.push(`RAG_PROJECT_ROOT=${absProjectRoot}`);
fs.writeFileSync(envFile, envLines.join('\n') + '\n');
ok(`RAG_PROJECT_ROOT=${absProjectRoot} → ~/.omp/agent/.env`);
log(`  OMP loads .env at session start → \${RAG_PROJECT_ROOT} resolves dynamically\n`);

// Step 5 — Generate MCP config (uses ${RAG_PROJECT_ROOT} — portable, not hardcoded)
console.log('  Step 5: Configuring MCP server...');
const mcpDest = path.join(OMP_AGENT_DIR, 'mcp.json');
let mcpConfig = { mcpServers: {} };

// Read existing config if present
if (fs.existsSync(mcpDest)) {
  try {
    mcpConfig = JSON.parse(fs.readFileSync(mcpDest, 'utf8'));
    if (!mcpConfig.mcpServers) mcpConfig.mcpServers = {};
  } catch { /* start fresh */ }
}

// Use ${RAG_PROJECT_ROOT} env var — OMP expands it at session start from ~/.omp/agent/.env
// This makes the config fully portable: if the project moves, only .env needs updating
const isWindows = process.platform === 'win32';
const pythonCmd = isWindows ? 'python' : 'python3';

mcpConfig.mcpServers['kb-mcp'] = {
  command: 'uv',
  args: ['run', '--directory', '${RAG_PROJECT_ROOT}/kb-mcp', pythonCmd, 'server.py']
};

// Add schema URL if not present
if (!mcpConfig.$schema) {
  mcpConfig.$schema = 'https://raw.githubusercontent.com/can1357/oh-my-pi/main/packages/coding-agent/src/config/mcp-schema.json';
}

fs.writeFileSync(mcpDest, JSON.stringify(mcpConfig, null, 2) + '\n');
ok(`MCP config written to ${mcpDest}`);
log(`  kb-mcp → uv run --directory \${RAG_PROJECT_ROOT}/kb-mcp ${pythonCmd} server.py`);
log(`  \${RAG_PROJECT_ROOT} resolves to: ${absProjectRoot}\n`);

// Step 6 — Summary
console.log('  ═════════════════════════════════════════════════════');
console.log('  ✅ OMP Global Installation Complete!');
console.log('  ═════════════════════════════════════════════════════');
console.log('');
console.log(`  📁 Skills:     ${skillDirs.length} knowledgebase skills → ~/.omp/agent/skills/`);
console.log(`  🤖 Agent:      archival.md → ~/.omp/agent/agents/`);
console.log(`  📋 Command:    ragctl → ~/.omp/agent/commands/`);
console.log(`  🔌 MCP:        kb-mcp (76 tools) → ~/.omp/agent/mcp.json`);
console.log(`  🌐 Env:        RAG_PROJECT_ROOT → ~/.omp/agent/.env`);
console.log('');
console.log('  How path resolution works:');
console.log('    1. ~/.omp/agent/.env contains: RAG_PROJECT_ROOT=<your-path>');
console.log('    2. mcp.json uses: ${RAG_PROJECT_ROOT}/kb-mcp (NOT hardcoded)');
console.log('    3. OMP expands ${RAG_PROJECT_ROOT} at every session start');
console.log('    4. If project moves → edit RAG_PROJECT_ROOT in ~/.omp/agent/.env');
console.log('');
console.log('  Next steps:');
console.log('    1. Restart your OMP session (or run /mcp reload)');
console.log('    2. Run the init wizard:');
console.log('       In any OMP session, say: "初始化知识库" or "set up the knowledge base"');
console.log('    3. Or run manually from the project root:');
console.log('       ragctl setup && ragctl up');
console.log('');
console.log('  To uninstall: node scripts/install_omp.cjs --uninstall');
console.log('');
