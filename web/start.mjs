#!/usr/bin/env node
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { spawn } from 'node:child_process'
import net from 'node:net'
import {
  NUXT_CLI_CANDIDATES,
  getServerConfig,
} from './utils/paths.mjs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

/** Load root/web .env files without overriding values already provided by the caller. */
export function loadDotenv({ env = process.env, rootDir = path.resolve(__dirname, '..') } = {}) {
  const fromFiles = {}
  const candidates = [path.join(rootDir, '.env'), path.join(rootDir, 'web', '.env')]
  for (const envPath of candidates) {
    if (!fs.existsSync(envPath)) continue
    const content = fs.readFileSync(envPath, 'utf-8')
    for (const line of content.split(/\r?\n/)) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue
      const eq = trimmed.indexOf('=')
      const key = trimmed.slice(0, eq).trim()
      let value = trimmed.slice(eq + 1).trim()
      if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1)
      }
      if (!key || Object.hasOwn(fromFiles, key)) continue
      fromFiles[key] = value
      if (env[key] === undefined) env[key] = value
    }
  }
  return fromFiles
}

export function parseArgs(argv) {
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

/** Resolve mode independently of dotenv loading so caller-provided env always wins. */
export function resolveAppMode({ cliOpts = {}, processEnv = {}, dotenv = {}, lifecycleEvent = '' } = {}) {
  const mode = cliOpts.mode || processEnv.APP_MODE || dotenv.APP_MODE
    || (lifecycleEvent === 'dev' ? 'dev' : 'prod')
  if (mode !== 'dev' && mode !== 'prod') {
    throw new Error(`Invalid APP_MODE "${mode}". Expected "dev" or "prod".`)
  }
  return mode
}

/** Resolve mode-specific listener and backend settings with process env > .env > config precedence. */
export function resolveStartupOptions({
  cliOpts = {},
  processEnv = {},
  dotenv = {},
  modeConfig = {},
  lifecycleEvent = '',
} = {}) {
  const mode = resolveAppMode({ cliOpts, processEnv, dotenv, lifecycleEvent })
  const host = cliOpts.host || processEnv.HOST || dotenv.HOST || modeConfig.host || '0.0.0.0'
  const portValue = cliOpts.port
    || processEnv.WEB_PORT || processEnv.FRONTEND_PORT || processEnv.PORT
    || dotenv.WEB_PORT || dotenv.FRONTEND_PORT || dotenv.PORT
    || modeConfig.frontend_port || (mode === 'prod' ? '3000' : '6789')
  const port = String(portValue)
  if (!/^\d+$/.test(port) || Number(port) < 1 || Number(port) > 65535) {
    throw new Error(`Invalid frontend port "${port}". Expected an integer from 1 to 65535.`)
  }

  let backendUrl
  if (processEnv.BACKEND_URL) backendUrl = processEnv.BACKEND_URL
  else if (processEnv.BACKEND_PORT) {
    backendUrl = `http://${processEnv.BACKEND_HOST || 'localhost'}:${processEnv.BACKEND_PORT}`
  } else if (dotenv.BACKEND_URL) backendUrl = dotenv.BACKEND_URL
  else if (dotenv.BACKEND_PORT) {
    backendUrl = `http://${dotenv.BACKEND_HOST || 'localhost'}:${dotenv.BACKEND_PORT}`
  } else {
    backendUrl = modeConfig.backend_url || (mode === 'prod' ? 'http://localhost:8001' : 'http://localhost:8765')
  }

  return { mode, host, port, backendUrl }
}

/** Build a launch command. Production must use the built Nitro artifact, never Nuxt CLI. */
export function createLaunchPlan({ mode, artifactPath, nuxtCliPath, host, port }) {
  if (mode === 'prod') {
    if (!artifactPath || !fs.existsSync(artifactPath)) {
      throw new Error(`Production Nitro artifact not found: ${artifactPath || '(missing path)'}. Run npm run build before starting production.`)
    }
    return { command: process.execPath, args: [artifactPath], description: 'built Nitro server' }
  }
  if (!nuxtCliPath) {
    throw new Error('Failed to locate Nuxt CLI entry required for dev mode.')
  }
  return {
    command: process.execPath,
    args: [nuxtCliPath, 'dev', '--host', host, '--port', port],
    description: 'Nuxt dev server',
  }
}

export function createChildEnvironment(env, options) {
  return {
    ...env,
    HOST: options.host,
    PORT: options.port,
    NITRO_HOST: options.host,
    NITRO_PORT: options.port,
    APP_MODE: options.mode,
    BACKEND_URL: options.backendUrl,
  }
}

async function ensurePortFree(host, portNum) {
  return new Promise((resolve) => {
    const tester = net.createServer()
    tester.once('error', () => resolve(false))
    tester.once('listening', () => tester.close(() => resolve(true)))
    tester.listen({ host, port: portNum })
  })
}

function findNuxtCli() {
  return NUXT_CLI_CANDIDATES.find((candidate) => {
    try { return fs.existsSync(candidate) } catch { return false }
  })
}

export async function start() {
  // Snapshot caller-provided environment before dotenv populates missing keys.
  const explicitEnv = { ...process.env }
  const cliOpts = parseArgs(process.argv.slice(2))
  const dotenv = loadDotenv()
  const mode = resolveAppMode({
    cliOpts,
    processEnv: explicitEnv,
    dotenv,
    lifecycleEvent: process.env.npm_lifecycle_event,
  })
  process.env.APP_MODE = mode

  // getServerConfig selects the proper mode section; its env-aware values are
  // fallback config only, while the snapshot/file values retain their provenance.
  const serverCfg = getServerConfig()
  const options = resolveStartupOptions({
    cliOpts,
    processEnv: explicitEnv,
    dotenv,
    modeConfig: serverCfg,
    lifecycleEvent: process.env.npm_lifecycle_event,
  })
  const artifactPath = path.join(__dirname, '.output', 'server', 'index.mjs')
  const nuxtCliPath = options.mode === 'dev' ? findNuxtCli() : undefined
  const launch = createLaunchPlan({ ...options, artifactPath, nuxtCliPath })
  const childEnv = createChildEnvironment(process.env, options)

  console.log(`[start.mjs] mode=${options.mode}, host=${options.host}, port=${options.port}`)
  console.log('[start.mjs] backend API configured')

  // Refuse a silent fallback to a different port.
  if (!(await ensurePortFree(options.host, Number(options.port)))) {
    console.error(`Port ${options.port} on ${options.host} is already in use.`)
    console.error(`Configured port for APP_MODE=${options.mode} cannot be acquired; refusing to fall back.`)
    console.error('Free the port or set WEB_PORT / FRONTEND_PORT in .env or config.yml.')
    process.exitCode = 1
    return
  }

  console.log(`[start.mjs] port ${options.port} is free, launching ${launch.description}...`)
  const child = spawn(launch.command, launch.args, {
    cwd: __dirname,
    stdio: 'inherit',
    windowsHide: true,
    env: childEnv,
  })

  child.on('exit', (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal)
      return
    }
    process.exit(code ?? 0)
  })
  child.on('error', (error) => {
    console.error(`Failed to start frontend: ${error.message}`)
    process.exitCode = 1
  })
  process.on('SIGINT', () => child.kill('SIGINT'))
  process.on('SIGTERM', () => child.kill('SIGTERM'))
}

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : ''
if (invokedPath && pathToFileURL(invokedPath).href === import.meta.url) {
  start().catch((error) => {
    console.error(`Frontend startup failed: ${error.message}`)
    process.exitCode = 1
  })
}
