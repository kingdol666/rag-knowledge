/**
 * Resolve the CLI executable the Claude Agent SDK should spawn.
 *
 * WHY THIS EXISTS (measured 2026-10-13)
 * -------------------------------------
 * When `pathToClaudeCodeExecutable` is NOT passed, the SDK spawns its own
 * bundled native CLI (manifest 2.1.207). On this machine that build never
 * registers MCP servers: the `init` frame reports
 * `mcp_servers: [{name:'kb-mcp', status:'pending'}]` and a 30-tool face
 * containing ZERO `mcp__kb-mcp__*` tools, so every KB turn answers from
 * parametric memory (the benchmark a2 arm returns the literal
 * `KB_TOOLS_NOT_READY`). The PATH-installed CLI (2.1.296) registers the same
 * server from the identical argv — `--mcp-config <inline JSON>` +
 * `--strict-mcp-config` — and reports `status: connected` with 95
 * `mcp__kb-mcp__*` tools present at `init`.
 *
 * Passing `pathToClaudeCodeExecutable` pointed at the 2.1.296 executable
 * restores the mount for both stdio and SSE configs (measured 122-tool face,
 * 95 kb tools, status connected).
 *
 * Precedence: explicit env override (setup-dependent) → CLI package shipped
 * next to the running node → well-known native-installer locations → PATH
 * (`where`/`which`). Every candidate must answer `--version` before it is
 * accepted, because Windows PATH hits are POSIX shell shims. Returns null when
 * nothing usable is found, in which case the SDK keeps its own default.
 */
import { execFileSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

/** Env var operators can set to pin an exact CLI (absolute path to a binary). */
export const CLI_EXEC_ENV = 'DSH_CLAUDE_CLI_EXEC'

let cached: string | null | undefined

function isFile(p: string | undefined | null): p is string {
  if (!p) return false
  try {
    return existsSync(p)
  } catch {
    return false
  }
}

/** Native installer + npm-global layouts seen on this project's machines. */
function fromWellKnown(): string | null {
  const home = homedir()
  const candidates =
    process.platform === 'win32'
      ? [
          join(home, '.local', 'bin', 'claude.exe'),
          join(home, '.claude', 'local', 'claude.exe'),
          // npm shims next to node (nvm4w keeps the real .exe inside bin/).
          'C:/nvm4w/nodejs/node_modules/@anthropic-ai/claude-code/bin/claude.exe',
          join(process.execPath, '..', 'node_modules', '@anthropic-ai', 'claude-code', 'bin', 'claude.exe'),
        ]
      : [join(home, '.local', 'bin', 'claude'), '/usr/local/bin/claude']
  for (const c of candidates) {
    if (isFile(c)) return c
  }
  return null
}

/**
 * Does this candidate actually launch?
 *
 * WHY (measured 2026-10-13): the npm shim `C:\nvm4w\nodejs\claude` is the
 * EXTENSIONLESS POSIX shell script that npm also drops on Windows. `isFile`
 * accepts it, but the SDK's native spawn rejects it —
 * "Claude Code native binary at ... exists but failed to launch" (HTTP 500,
 * code SDK_QUERY_FAILED), which killed every chat turn with `mcpMount:'stdio'`.
 * `where.exe claude` lists that shim FIRST and the real binary only as the
 * `claude.cmd` wrapper, so the extension filter alone is not enough: the
 * candidate must answer `--version` before we hand it to the SDK.
 */
function launches(p: string): boolean {
  try {
    const out = execFileSync(p, ['--version'], {
      encoding: 'utf8',
      timeout: 10000,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'ignore'],
    })
    return /\d+\.\d+/.test(String(out))
  } catch {
    return false
  }
}

/** Bin directory of the CLI package next to the running node executable. */
function fromNodeModules(): string | null {
  if (process.platform !== 'win32') return null
  const nodeDir = process.execPath.replace(/[\\/][^\\/]+$/, '')
  const c = join(nodeDir, 'node_modules', '@anthropic-ai', 'claude-code', 'bin', 'claude.exe')
  return isFile(c) ? c : null
}

/** All non-shim candidates in preference order (deduped, existing only). */
function candidates(): Array<string | null> {
  return [
    String(process.env[CLI_EXEC_ENV] || '').trim() || null,
    fromNodeModules(),
    fromWellKnown(),
    ...pathHits(),
  ]
}

/** Raw `where claude` / `which claude` hits, shims filtered out. */
function pathHits(): string[] {
  const out: string[] = []
  const tools = process.platform === 'win32' ? ['where.exe', 'where'] : ['which']
  for (const tool of tools) {
    try {
      const res = execFileSync(tool, ['claude'], {
        encoding: 'utf8',
        timeout: 5000,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'ignore'],
      })
      for (const line of String(res).split(/\r?\n/)) {
        const candidate = line.trim()
        // Skip shell shims: node cannot exec a .cmd/.ps1 wrapper as the CLI.
        // Extensionless hits are POSIX shims on Windows — verified below.
        if (!candidate || /\.(cmd|ps1|bat)$/i.test(candidate)) continue
        if (isFile(candidate)) out.push(candidate)
      }
      break
    } catch {
      /* lookup tool missing or no hit — try the next one */
    }
  }
  return out
}

/**
 * Cached absolute path of the CLI to hand to the SDK, or null to keep the
 * SDK's own default. Each candidate costs one `--version` spawn, so the
 * result is memoized for the process lifetime.
 */
export function resolveClaudeCliExecutable(): string | null {
  if (cached !== undefined) return cached
  const seen = new Set<string>()
  for (const c of candidates()) {
    if (!c || seen.has(c)) continue
    seen.add(c)
    if (isFile(c) && launches(c)) {
      cached = c
      return cached
    }
  }
  cached = null
  return cached
}
