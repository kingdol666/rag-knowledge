import { existsSync } from 'fs'
import { dirname, isAbsolute, join, resolve } from 'path'
import { fileURLToPath } from 'url'

function isProjectRoot(candidate: string): boolean {
  return existsSync(join(candidate, 'config.yml')) && existsSync(join(candidate, 'kb-mcp', 'server.py'))
}

function findProjectAncestor(start: string): string | undefined {
  let candidate = resolve(start)
  while (true) {
    if (isProjectRoot(candidate)) return candidate
    const parent = dirname(candidate)
    if (parent === candidate) return undefined
    candidate = parent
  }
}

export interface ProjectRootOptions {
  configuredRoot?: string
  cwd?: string
  moduleUrl?: string
}

/** Resolve one verified project root for source and bundled Nitro runtimes. */
export function resolveProjectRoot({
  configuredRoot = process.env.RAG_PROJECT_ROOT,
  cwd = process.cwd(),
  moduleUrl = import.meta.url,
}: ProjectRootOptions = {}): string {
  const override = configuredRoot?.trim()
  if (override) {
    if (!isAbsolute(override) || !isProjectRoot(override)) {
      throw new Error('RAG_PROJECT_ROOT must be an absolute project directory containing config.yml and kb-mcp/server.py')
    }
    return resolve(override)
  }

  // cwd is authoritative for service launchers and Nitro deployments.
  const cwdRoot = findProjectAncestor(cwd)
  if (cwdRoot) return cwdRoot

  // When a server is launched from another directory, a real source/module URL
  // can still anchor discovery. Nitro's synthetic entry URL is never trusted.
  try {
    if (moduleUrl.startsWith('file:') && moduleUrl !== 'file:///_entry.js') {
      const moduleRoot = findProjectAncestor(dirname(fileURLToPath(moduleUrl)))
      if (moduleRoot) return moduleRoot
    }
  } catch { /* synthetic, non-file, or platform-invalid URL */ }

  throw new Error('Cannot locate project root from working directory or module; set RAG_PROJECT_ROOT to the project directory')
}

export function getMonorepoRoot(): string {
  return resolveProjectRoot()
}
