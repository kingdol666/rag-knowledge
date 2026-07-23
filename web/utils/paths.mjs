/**
 * Project runtime paths — all directory / file paths resolved from here.
 *
 * The shared `config.yml` is the **single source of truth** for ports and URLs.
 * Everything below reads from it via getServerConfig() — no hardcoded port numbers anywhere.
 */

import path from 'node:path'
import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

// ── key anchor ────────────────────────────────────────────────────────
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

/** Absolute path to the rag-knowledge-frondend project root. */
export const PROJECT_ROOT = path.resolve(__dirname, '..')

export const ENV_PATH = path.join(PROJECT_ROOT, '.env')

const PARENT = path.resolve(PROJECT_ROOT, '..')
const SHARED_CONFIG_CANDIDATES = [
  path.join(PARENT, 'rag-knowledge', 'config.yml'),
  path.join(PARENT, 'config.yml'),
]

export const NODE_MODULES_DIR = path.join(PROJECT_ROOT, 'node_modules')

export const NUXT_CLI_CANDIDATES = [
  path.join(NODE_MODULES_DIR, 'nuxt', 'bin', 'nuxt.mjs'),
  path.join(NODE_MODULES_DIR, '@nuxt', 'cli', 'bin', 'nuxi.mjs'),
]

// ── find and read the shared config file ──────────────────────────────
function findAndReadConfig() {
  for (const candidate of SHARED_CONFIG_CANDIDATES) {
    try { return readFileSync(candidate, 'utf-8') } catch { /* next */ }
  }
  return null
}

/**
 * Minimal .env reader (matches dynamic-config.ts precedence). Returns {} if absent.
 * Reads PROJECT_ROOT/.env (rag-knowledge/.env) so env overrides are visible to
 * every consumer of getServerConfig(), not only to dynamic-config.ts callers.
 */
function readDotenv() {
  const envPath = path.join(PARENT, '.env')
  if (!existsSync(envPath)) return {}
  const result = {}
  for (const line of readFileSync(envPath, 'utf-8').split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue
    const eq = trimmed.indexOf('=')
    const key = trimmed.slice(0, eq).trim()
    const val = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, '')
    if (key) result[key] = val
  }
  return result
}

// ── YAML parser (sufficient for our config.yml) ───────────────────────
/**
 * Parse::
 *
 *   server:
 *     key: value
 *     list_key:
 *       - item1
 *       - item2
 *
 * into:
 *
 *   { server: { key: "value", list_key: ["item1","item2"] } }
 */
function parseConfig(raw) {
  const lines = raw.split('\n')

  // Build indent → key-path mapping from non-list lines
  const indentStack = []  // [{indent, key, isBlock}]
  const pathFor = new Map() // lineIndex → array of ancestor keys

  const indexed = []
  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim()
    if (trimmed === '' || trimmed.startsWith('#')) continue
    if (trimmed.startsWith('- ')) {
      indexed.push({ i, type: 'list', indent: lines[i].search(/\S/), trimmed })
      continue
    }
    const m = trimmed.match(/^(\w[\w_-]*):\s*(.*)\s*$/)
    if (!m) continue
    const indent = lines[i].search(/\S/)
    const [, key, rawVal] = m
    const isBlock = (rawVal.trim() === '')
    indexed.push({ i, type: 'key', indent, key, rawVal, isBlock })
  }

  // Populate indentStack and build paths
  const activeStack = []
  for (const entry of indexed) {
    if (entry.type !== 'key') continue
    while (activeStack.length && activeStack[activeStack.length - 1].indent >= entry.indent) {
      activeStack.pop()
    }
    entry._ancestors = activeStack.map(e => e.key).slice()
    activeStack.push({ indent: entry.indent, key: entry.key })
  }

  // Also build ancestor paths for list items
  for (const entry of indexed) {
    if (entry.type !== 'list') continue
    // find the active ancestor at the time of this list item
    const ancestors = []
    for (const e of indexed) {
      if (e === entry) break
      if (e.type !== 'key') continue
      if (e._ancestors && e.indent < entry.indent) {
        ancestors.length = 0
        ancestors.push(...e._ancestors, e.key)
      }
    }
    entry._ancestors = ancestors
    entry._listParentKey = ancestors[ancestors.length - 1] || null
  }

  // Now build the result
  const root = {}

  for (const entry of indexed) {
    if (entry.type === 'key') {
      const ancestors = entry._ancestors || []
      let cur = root
      for (const a of ancestors) {
        if (!cur[a] || typeof cur[a] !== 'object') cur[a] = {}
        cur = cur[a]
      }
      if (entry.isBlock) {
        cur[entry.key] = {}
      } else {
        let val = entry.rawVal.trim()
        if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
          val = val.slice(1, -1)
        }
        cur[entry.key] = val
      }
    } else {
      // list item
      const ancestors = entry._ancestors || []
      const listKey = entry._listParentKey
      let cur = root
      // walk ancestors EXCEPT the last one (which is the list key itself)
      const walk = ancestors.slice(0, -1)
      for (const a of walk) {
        if (!cur[a] || typeof cur[a] !== 'object') cur[a] = {}
        cur = cur[a]
      }
      if (listKey) {
        if (!Array.isArray(cur[listKey])) {
          cur[listKey] = []
        }
        let val = entry.trimmed.slice(2).trim()
        if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
          val = val.slice(1, -1)
        }
        cur[listKey].push(val)
      }
    }
  }

  return root
}

// ── mode detection ────────────────────────────────────────────────────
export function getAppMode() {
  const env = process.env.APP_MODE || 'dev'
  return env === 'prod' ? 'prod' : 'dev'
}

// ── primary public API ────────────────────────────────────────────────
/**
 * Return the server section for the current mode.
 *
 *   const cfg = getServerConfig()
 *   cfg.backend_port   // "8765" (dev) or "8001" (prod)
 *   cfg.frontend_port  // "6789" (dev) or "3000" (prod) — reads from config.yml
 *   cfg.backend_url    // "http://localhost:8765"
 *   cfg.cors_origins   // ["http://localhost:6789", ...]
 *
 * @returns {Record<string, any>}
 */
export function getServerConfig() {
  const mode = getAppMode()
  const raw = findAndReadConfig()
  if (!raw) return {}
  const parsed = parseConfig(raw)
  const server = parsed.server || {}

  // Merge bare server keys with mode block
  const merged = {}
  for (const [k, v] of Object.entries(server)) {
    if (k !== 'dev' && k !== 'prod') merged[k] = v
  }
  const modeSection = server[mode]
  if (modeSection && typeof modeSection === 'object') {
    Object.assign(merged, modeSection)
  }

  // ENV-AWARE OVERRIDE (parity with dynamic-config.ts getDynamicServerConfig):
  // process.env wins, then .env, then config.yml. Without this, callers of
  // getServerConfig() (experience routes, tree-file-system-service, start.mjs,
  // nuxt.config) silently diverged from getDynamicBackendUrl() consumers
  // whenever BACKEND_URL/BACKEND_PORT/WEB_PORT were set via env. This keeps a
  // single precedence rule across the whole web subsystem.
  const dotenv = readDotenv()
  const envBackendUrl = process.env.BACKEND_URL || dotenv.BACKEND_URL
  const envBackendPort = process.env.BACKEND_PORT || dotenv.BACKEND_PORT
  const envWebPort = process.env.WEB_PORT || process.env.FRONTEND_PORT
    || dotenv.WEB_PORT || dotenv.FRONTEND_PORT
  if (envBackendUrl) {
    merged.backend_url = envBackendUrl
  } else if (envBackendPort) {
    merged.backend_url = `http://localhost:${envBackendPort}`
  }
  if (envWebPort) merged.frontend_port = envWebPort

  return merged
}

/** Convenience: backend base URL for current mode. */
export function getBackendUrl() {
  return getServerConfig().backend_url || 'http://localhost:8765'
}

/** Convenience: frontend port for current mode. */
export function getFrontendPort() {
  return getServerConfig().frontend_port || '3000'
}

/** Resolve a path relative to PROJECT_ROOT. */
export function resolveProjectPath(segment) {
  return path.resolve(PROJECT_ROOT, segment)
}
