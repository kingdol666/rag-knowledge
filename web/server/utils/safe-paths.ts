import { resolve, sep } from 'path'
import { createError } from 'h3'
import { getTreeStorageAbsolutePath } from '~/server/utils/runtime-paths'

/**
 * Safe Path Resolution -- Phase 0 (P0 #4 #5 #7) Core Defense.
 *
 * Ensure `candidate` resolves within `root` subtree, blocking:
 *  - Path Traversal (`..`, absolute path escape)
 *  - UNC (`\\server\share`) and `\\?\` prefix (can bypass normalization)
 *  - NUL Byte Injection (Windows treats it as string terminator)
 *  - Windows case-insensitive differences
 *
 * Design: `resolve(root, candidate)` normalized then case-insensitive containment check.
 *       resolved must equal root, or start with root + sep (avoid `rootx` false prefix).
 *
 * Backward compatible: legal paths (within root subtree) unchanged; out-of-bounds changes from "read any file" to 403.
 */
export function resolveSafePath(
  candidate: string,
  root: string = getTreeStorageAbsolutePath(),
): string {
  if (!candidate || typeof candidate !== 'string' || candidate.length === 0) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid path' })
  }

  // NUL byte injection defense (Windows treats \0 as path terminator)
  if (candidate.indexOf('\0') !== -1) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid path (NUL byte rejected)' })
  }

  // UNC (`\\server\share`) and Verbatim prefix (`\\?\`) can bypass path.resolve normalization
  if (/^\\\\[?]\\/.test(candidate) || /^\\\\[^?\\]/.test(candidate)) {
    throw createError({ statusCode: 403, statusMessage: 'UNC / verbatim paths not allowed' })
  }

  const resolved = resolve(root, candidate)
  if (!isWithin(resolved, root)) {
    throw createError({ statusCode: 403, statusMessage: 'Path outside allowed root' })
  }
  return resolved
}

/**
 * Non-throwing version: Returns null for out-of-bounds. For batch scenarios that skip + warn instead of hard-failing
 * (e.g., save-parsed-files validates each result entry).
 */
export function tryResolveSafePath(
  candidate: string,
  root: string = getTreeStorageAbsolutePath(),
): string | null {
  try {
    return resolveSafePath(candidate, root)
  } catch {
    return null
  }
}

/**
 * Multi-root Validation: Candidate path is accepted if it falls within any allowed root. Used for parse output and other scenarios needing multiple roots.
 * Returns the resolved absolute path, or null if all out of bounds.
 */
export function resolveWithinAnyRoot(candidate: string, roots: string[]): string | null {
  if (!candidate || candidate.indexOf('\0') !== -1) return null
  if (/^\\\\[?]\\/.test(candidate) || /^\\\\[^?\\]/.test(candidate)) return null
  for (const root of roots) {
    const resolved = resolve(root, candidate)
    if (isWithin(resolved, root)) return resolved
  }
  return null
}

/**
 * Case-insensitive containment check (Windows NTFS is case-insensitive).
 * `resolved === root` or `resolved` starts with `root + sep`.
 */
function isWithin(resolved: string, root: string): boolean {
  const r = root.toLowerCase().replace(/[/\\]+$/, '')
  const c = resolved.toLowerCase()
  if (c === r) return true
  // sep on Windows is '\\'; compare with lowercased sep
  return c.startsWith(r + sep.toLowerCase())
}
