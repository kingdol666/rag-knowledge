/**
 * Dynamic Config Reader — reads config.yml and .env on demand (with short TTL cache).
 *
 * This replaces the static `useRuntimeConfig()` pattern for server-side routes,
 * allowing config changes made via the Settings page to take effect immediately
 * without restarting the Nuxt server.
 *
 * Usage in server routes:
 *   import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'
 *   const backendUrl = getDynamicBackendUrl()
 *   $fetch(`${backendUrl}/api/v1/...`)
 */
import { readFileSync, existsSync } from 'fs'
import { resolve, isAbsolute } from 'path'
import { getMonorepoRoot } from './project-root'

// Both runtime paths and dynamic config use the same validated root.
// Resolve on demand so a runtime RAG_PROJECT_ROOT change cannot split config and storage roots.

// ── Cache (5 second TTL) ───────────────────────────────────────────────
interface CachedConfig {
  data: any
  timestamp: number
  root: string
}
interface CachedEnv {
  data: Record<string, string>
  timestamp: number
  root: string
}
let _cachedConfig: CachedConfig | null = null
let _cachedEnv: CachedEnv | null = null
const CACHE_TTL = 5000 // 5 seconds

// ── Minimal YAML parser (same logic as utils/paths.mjs) ────────────────
function parseYaml(raw: string): any {
  const lines = raw.split('\n')
  const indexed: any[] = []
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
    const isBlock = rawVal.trim() === ''
    indexed.push({ i, type: 'key', indent, key, rawVal, isBlock })
  }

  // Build ancestor paths
  const activeStack: any[] = []
  for (const entry of indexed) {
    if (entry.type !== 'key') continue
    while (activeStack.length && activeStack[activeStack.length - 1].indent >= entry.indent) {
      activeStack.pop()
    }
    entry._ancestors = activeStack.map(e => e.key)
    activeStack.push({ indent: entry.indent, key: entry.key })
  }

  // Build ancestor paths for list items
  for (const entry of indexed) {
    if (entry.type !== 'list') continue
    const ancestors: string[] = []
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

  // Build result
  const root: any = {}
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
      const ancestors = entry._ancestors || []
      const listKey = entry._listParentKey
      let cur = root
      const walk = ancestors.slice(0, -1)
      for (const a of walk) {
        if (!cur[a] || typeof cur[a] !== 'object') cur[a] = {}
        cur = cur[a]
      }
      if (listKey) {
        if (!Array.isArray(cur[listKey])) cur[listKey] = []
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

// ── Public API ─────────────────────────────────────────────────────────

/** Force-clear the cache — call after config is saved. */
export function invalidateConfigCache(): void {
  _cachedConfig = null
  _cachedEnv = null
}

/** Read config.yml (cached with TTL). */
export function getRawConfig(): any {
  const root = getMonorepoRoot()
  const configPath = resolve(root, 'config.yml')
  const now = Date.now()
  if (_cachedConfig && _cachedConfig.root === root && now - _cachedConfig.timestamp < CACHE_TTL) {
    return _cachedConfig.data
  }
  if (!existsSync(configPath)) {
    _cachedConfig = { data: {}, timestamp: now, root }
    return {}
  }
  try {
    const raw = readFileSync(configPath, 'utf-8')
    const parsed = parseYaml(raw)
    _cachedConfig = { data: parsed, timestamp: now, root }
    return parsed
  } catch {
    _cachedConfig = { data: {}, timestamp: now, root }
    return {}
  }
}

/** Read .env file (cached with TTL). */
export function getEnvConfig(): Record<string, string> {
  const root = getMonorepoRoot()
  const envPath = resolve(root, '.env')
  const now = Date.now()
  if (_cachedEnv && _cachedEnv.root === root && now - _cachedEnv.timestamp < CACHE_TTL) {
    return _cachedEnv.data
  }
  const result: Record<string, string> = {}
  if (!existsSync(envPath)) {
    _cachedEnv = { data: result, timestamp: now, root }
    return result
  }
  try {
    const raw = readFileSync(envPath, 'utf-8')
    for (const line of raw.split('\n')) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#')) continue
      if (trimmed.includes('=')) {
        const [key, ...rest] = trimmed.split('=')
        let value = rest.join('=').trim()
        if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
          value = value.slice(1, -1)
        }
        result[key.trim()] = value
      }
    }
  } catch { /* ignore */ }
  _cachedEnv = { data: result, timestamp: now, root }
  return result
}

/** Get the caller environment first, then dotenv, then mode config. */
function getEnvValue(key: string): string | undefined {
  return process.env[key] || getEnvConfig()[key]
}

/** Explicit process environment always wins over .env; .env wins over config.yml. */
export function getAppMode(): string {
  return process.env.APP_MODE || getEnvConfig().APP_MODE || 'dev'
}

/**
 * Get the backend URL for the current mode.
 * Priority: env BACKEND_URL > env BACKEND_PORT > config.yml server.{mode}.backend_url > default.
 */
/** Resolve a backend URL without reading files; useful for tests and callers with known provenance. */
export function resolveBackendUrl({
  processEnv = {},
  dotenv = {},
  mode = 'dev',
  modeConfig = {},
}: {
  processEnv?: Record<string, string | undefined>
  dotenv?: Record<string, string | undefined>
  mode?: string
  modeConfig?: { backend_url?: string }
} = {}): string {
  if (processEnv.BACKEND_URL) return processEnv.BACKEND_URL
  if (processEnv.BACKEND_PORT) {
    return `http://${processEnv.BACKEND_HOST || 'localhost'}:${processEnv.BACKEND_PORT}`
  }
  if (dotenv.BACKEND_URL) return dotenv.BACKEND_URL
  if (dotenv.BACKEND_PORT) {
    return `http://${dotenv.BACKEND_HOST || 'localhost'}:${dotenv.BACKEND_PORT}`
  }
  return modeConfig.backend_url || (mode === 'prod' ? 'http://localhost:8001' : 'http://localhost:8765')
}

export function getDynamicBackendUrl(): string {
  const cfg = getRawConfig()
  const mode = getAppMode()
  const server = cfg.server || {}
  const modeSection = server[mode] || {}
  return resolveBackendUrl({
    processEnv: process.env,
    dotenv: getEnvConfig(),
    mode,
    modeConfig: modeSection,
  })
}

/**
 * Get the frontend port for the current mode.
 */
export function getDynamicFrontendPort(): string {
  const env = getEnvConfig()
  const port = process.env.WEB_PORT || process.env.FRONTEND_PORT || process.env.PORT
    || env.WEB_PORT || env.FRONTEND_PORT || env.PORT
  if (port) return port

  const cfg = getRawConfig()
  const mode = getAppMode()
  const server = cfg.server || {}
  const modeSection = server[mode] || {}
  return modeSection.frontend_port || '3000'
}

/**
 * Get the tree storage path.
 * Priority: env TREE_STORAGE_PATH > config.yml storage.tree_fs_root > default.
 */
export function getDynamicTreeStoragePath(): string {
  const treeStoragePath = getEnvValue('TREE_STORAGE_PATH')
  if (treeStoragePath) return treeStoragePath

  const cfg = getRawConfig()
  return cfg.storage?.tree_fs_root || './storage/tree-file-system'
}

/**
 * Get the full config for the current mode (all sections merged with env overrides).
 */
export function getDynamicServerConfig(): Record<string, any> {
  const cfg = getRawConfig()
  const mode = getAppMode()
  const server = cfg.server || {}

  // Merge bare server keys with mode block
  const merged: any = {}
  for (const [k, v] of Object.entries(server)) {
    if (k !== 'dev' && k !== 'prod') merged[k] = v
  }
  const modeSection = server[mode]
  if (modeSection && typeof modeSection === 'object') {
    Object.assign(merged, modeSection)
  }
  return merged
}

/**
 * Read shared-token auth config.
 *
 * Returns {enabled, token}:
 *  - enabled: from config.yml server.auth.enabled (default false).
 *    The minimal YAML parser returns scalar values as strings, so we coerce.
 *  - token: from .env KB_AUTH_TOKEN or process.env (empty when unset).
 */
export function getDynamicAuthConfig(): { enabled: boolean; token: string } {
  const env = getEnvConfig()
  // 2026-09-09: dedicated MCP service token (auto-generated into .env by the
  // backend) takes precedence; it is what server-to-server calls should use.
  const envToken = (env.MCP_AUTH_TOKEN || process.env.MCP_AUTH_TOKEN
    || env.KB_AUTH_TOKEN || process.env.KB_AUTH_TOKEN || '').trim()
  const cfg = getRawConfig()
  const auth = cfg.server?.auth || {}
  const rawEnabled = String(auth.enabled ?? 'false').trim().toLowerCase()
  return { enabled: rawEnabled === 'true', token: envToken }
}

/**
 * Resolve a path relative to the monorepo root.
 */
export function resolveMonorepoPath(pathValue: string): string {
  return isAbsolute(pathValue) ? pathValue : resolve(getMonorepoRoot(), pathValue)
}

/**
 * Get the absolute tree storage path.
 */
export function getDynamicTreeStorageAbsolutePath(): string {
  return resolveMonorepoPath(getDynamicTreeStoragePath())
}
