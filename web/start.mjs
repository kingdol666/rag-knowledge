#!/usr/bin/env node
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { spawn } from 'node:child_process'
import net from 'node:net'
import {
  PROJECT_ROOT,
  NUXT_CLI_CANDIDATES,
  getServerConfig,
} from './utils/paths.mjs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// ── Load root .env before anything else ────────────────────────────────
// Sets keys from .env ONLY when not already present in process.env, so a
// deliberate runtime override (e.g. ragctl `up --mode prod` passing WEB_PORT /
// BACKEND_PORT / APP_MODE via the spawn env) wins over the file. This is the
// standard dotenv `override: false` semantics. (Previously every key was set
// unconditionally, which blocked mode/port runtime overrides entirely.)
function loadDotenv() {
  const candidates = [
    path.resolve(__dirname, '..', '..', '.env'),     // rag-knowledge/.env
    path.resolve(__dirname, '..', '.env'),             // web/.env
  ]
  for (const envPath of candidates) {
    if (!fs.existsSync(envPath)) continue
    const content = fs.readFileSync(envPath, 'utf-8')
    for (const line of content.split('\n')) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue
      const eq = trimmed.indexOf('=')
      const key = trimmed.slice(0, eq).trim()
      const val = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, '')
      if (key && process.env[key] === undefined) {
        process.env[key] = val
      }
    }
  }
}
loadDotenv()

// ── All port / host from shared config.yml (NO hardcoded defaults) ───
// Port priority: CLI arg > WEB_PORT env > config.yml > 3000
const serverCfg = getServerConfig()
const args = process.argv.slice(2)
const cliOpts = parseArgs(args)
const host = cliOpts.host || serverCfg.host || '0.0.0.0'
const port = cliOpts.port
  || process.env.WEB_PORT
  || process.env.FRONTEND_PORT
  || serverCfg.frontend_port
  || '3000'
// mode is decided by which npm command was run:
//   `npm run dev`   -> dev   (backend on the dev port, e.g. 8765)
//   `npm run start` -> prod  (backend on the prod port, e.g. 8001)
// Explicit APP_MODE / --mode=... overrides either, so the backend API URL
// always stays in sync with the command that launched the frontend.
const mode =
  cliOpts.mode ||
  process.env.APP_MODE ||
  (process.env.npm_lifecycle_event === 'dev' ? 'dev' : 'prod')

console.log(`[start.mjs] mode=${mode}, host=${host}, port=${port} (from config.yml)`)
console.log(`[start.mjs] backend api -> ${serverCfg.backend_url}`)
// Compute the backend URL that the Nuxt server should proxy to.
//
// Priority chain (env > config.yml):
//   1. BACKEND_URL     (absolute URL, from .mcp.json / .env)
//   2. BACKEND_PORT    (number, build URL from it)
//   3. config.yml     -> backend_url
//   4. fallback:       http://localhost:8765
function resolveBackendUrl(serverCfg) {
  if (process.env.BACKEND_URL) return process.env.BACKEND_URL

  const port = process.env.BACKEND_PORT
  if (port) {
    const host = process.env.BACKEND_HOST || 'localhost'
    return `http://${host}:${port}`
  }

  return serverCfg.backend_url || 'http://localhost:8765'
}

const backendUrl = resolveBackendUrl(serverCfg)

const childEnv = {
  ...process.env,
  APP_MODE: mode,
  BACKEND_URL: backendUrl,
}

// ── find Nuxt CLI ────────────────────────────────────────────────────
const nuxtCliPath = NUXT_CLI_CANDIDATES.find((candidate) => {
  try {
    return fs.existsSync(candidate)
  } catch {
    return false
  }
})

if (!nuxtCliPath) {
  console.error('Failed to locate Nuxt CLI entry. Expected one of:')
  for (const candidate of NUXT_CLI_CANDIDATES) {
    console.error(`- ${candidate}`)
  }
  process.exit(1)
}

// ── Pre-flight: configured port must be free (NO silent fallback) ─────
// User requirement: 启动则一定要在配置端口启动,被占用即报错退出,严禁 nuxt
// 内部 get-port 自动 fallback 到 3000/3001/3002(造成 "prod 自动启动" 错觉)。
// 这里主动 bind+close 探测,失败立即 process.exit(1),nuxt 根本不会启动。
async function ensurePortFree(host, portNum) {
  return new Promise((resolve) => {
    const tester = net.createServer()
    tester.once('error', () => resolve(false))
    tester.once('listening', () => tester.close(() => resolve(true)))
    tester.listen({ host, port: portNum })
  })
}

const _portOk = await ensurePortFree(host, Number(port))
if (!_portOk) {
  console.error('')
  console.error(`✖ Port ${port} on ${host} is already in use.`)
  console.error(`  Configured port for APP_MODE=${mode} cannot be acquired.`)
  console.error(`  This launcher REFUSES to fall back to another port.`)
  console.error(`  → Free the port, then retry. Diagnose with:`)
  console.error(`      ragctl status                  # 看当前 dev/prod 进程`)
  console.error(`      ragctl down --appmode ${mode}    # 停掉当前模式`)
  console.error(`    Or change WEB_PORT in .env / config.yml.`)
  process.exit(1)
}

console.log(`[start.mjs] port ${port} is free, launching nuxt...`)
// ── launch Nuxt ──────────────────────────────────────────────────────
const child = spawn(
  process.execPath,
  [nuxtCliPath, 'dev', '--host', host, '--port', port],
  {
    cwd: __dirname,
    stdio: 'inherit',
    windowsHide: true,
    env: childEnv
  }
)

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal)
    return
  }
  process.exit(code ?? 0)
})

child.on('error', (error) => {
  console.error(`Failed to start frontend: ${error.message}`)
  process.exit(1)
})

process.on('SIGINT', () => child.kill('SIGINT'))
process.on('SIGTERM', () => child.kill('SIGTERM'))

// ── simple CLI arg parser ────────────────────────────────────────────
function parseArgs(argv) {
  const parsed = {}
  for (let i = 0; i < argv.length; i += 1) {
    const current = argv[i]
    if (!current.startsWith('--')) continue
    const key = current.slice(2)
    const next = argv[i + 1]
    if (!next || next.startsWith('--')) {
      parsed[key] = true
      continue
    }
    parsed[key] = next
    i += 1
  }
  return parsed
}
