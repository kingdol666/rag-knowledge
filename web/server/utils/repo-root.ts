/**
 * Repo root (rag-knowledge/) — lazy, prod-build safe.
 *
 * NEVER resolve import.meta.url at module top level. After `nuxt build`,
 * rollup hoists static imports so chunks execute BEFORE index.mjs's module
 * body sets globalThis._importMeta_, and the polyfill fallback
 * "file:///_entry.js" reaches fileURLToPath() and crashes Nitro startup with
 * ERR_INVALID_FILE_URL_PATH (prod build verified broken 2026-10-04).
 *
 * Even resolved lazily the chunk's physical location differs between dev
 * (web/server/utils/...) and prod (.output/server/chunks/_/...), so relative
 * path arithmetic is unreliable — instead walk up from candidate anchors
 * looking for the repo markers: config.yml + web/package.json.
 */
import { resolve, dirname } from 'path'
import { existsSync } from 'fs'
import { fileURLToPath } from 'url'

let _root: string | null = null

export function getRepoRoot(): string {
  if (_root) return _root

  const override = process.env.CLAUDE_PROJECT_ROOT?.trim()
  if (override && existsSync(resolve(override, 'config.yml'))) return (_root = override)

  const anchors: string[] = []
  try {
    anchors.push(dirname(fileURLToPath(import.meta.url)))
  } catch {
    /* rollup polyfill fallback (file:///_entry.js) — skip this anchor */
  }
  if (process.cwd()) anchors.push(resolve(process.cwd()))

  for (const start of anchors) {
    let dir = start
    for (let i = 0; i < 8; i++) {
      if (existsSync(resolve(dir, 'config.yml')) && existsSync(resolve(dir, 'web', 'package.json'))) {
        return (_root = dir)
      }
      const parent = dirname(dir)
      if (parent === dir) break
      dir = parent
    }
  }

  // Last resort: nitro dev/prod both run with cwd = web/ (start.mjs spawns
  // with cwd=__dirname), so the repo root is one level up.
  const fallback = resolve(process.cwd(), '..')
  // eslint-disable-next-line no-console
  console.warn('[repo-root] repo markers not found — falling back to', fallback)
  return (_root = fallback)
}
