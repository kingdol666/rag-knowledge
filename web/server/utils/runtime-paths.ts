import { isAbsolute, join, normalize, resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import {
  getDynamicBackendUrl,
  getDynamicTreeStoragePath,
} from '~/server/utils/dynamic-config'

// -- monorepo project root (rag-knowledge/) --
// web/server/utils/runtime-paths.ts  ->  web/server/  ->  web/  ->  rag-knowledge/
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const MONOREPO_ROOT = resolve(__dirname, '../../..')

// -- runtime defaults --
export const DEFAULT_BACKEND_API_URL = 'http://localhost:8765'
export const DEFAULT_TREE_STORAGE_PATH = './storage/tree-file-system'

function readEnv(name: string): string | undefined {
  const value = process.env[name]?.trim()
  return value ? value : undefined
}

export function resolveProjectPath(pathValue: string): string {
  return normalize(
    isAbsolute(pathValue) ? pathValue : resolve(MONOREPO_ROOT, pathValue),
  )
}

/**
 * Returns the tree-file-system storage path (may be a relative path).
 * Priority: .env TREE_STORAGE_PATH > config.yml storage.tree_fs_root > default.
 *
 * Hot Reload Support: Uses dynamic reader from dynamic-config (5s TTL cache).
 */
export function getTreeStoragePath(): string {
  return getDynamicTreeStoragePath()
}

export function getTreeStorageAbsolutePath(): string {
  return resolveProjectPath(getTreeStoragePath())
}

export function resolveTreeStorageOutputPath(pathValue?: string): string | undefined {
  if (!pathValue?.trim()) {
    return undefined
  }
  return resolveProjectPath(pathValue)
}

export function joinTreeStoragePath(...segments: string[]): string {
  return join(getTreeStorageAbsolutePath(), ...segments)
}

export function toTreeStorageRelativePath(candidatePath: string): string | null {
  const normalizedCandidate = normalize(candidatePath)
  const normalizedRoot = normalize(getTreeStorageAbsolutePath())

  if (!normalizedCandidate.toLowerCase().startsWith(normalizedRoot.toLowerCase())) {
    return null
  }

  const relativePath = normalizedCandidate
    .slice(normalizedRoot.length)
    .replace(/^[/\\]+/, '')
    .replace(/\\/g, '/')

  return relativePath || null
}

/**
 * Return the PDF parser backend URL.
 * Hot Reload Support: Uses dynamic reader from dynamic-config (5s TTL cache).
 */
export function getPdfParserApiUrl(): string {
  return getDynamicBackendUrl()
}
