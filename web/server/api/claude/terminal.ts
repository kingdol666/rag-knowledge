/**
 * WebSocket PTY terminal endpoint — /api/claude/terminal
 *
 * Query params: ?cwd=<absolute path>   (defaults to project root)
 *               ?token=<api token>     (required when auth is enabled — browsers
 *                                       cannot send Authorization headers on the
 *                                       WS upgrade, so the token travels as a
 *                                       query param and is validated the same
 *                                       way as the HTTP middleware; P0 fix
 *                                       2026-10-04: this endpoint previously
 *                       accepted unauthenticated upgrades = host shell RCE)
 *
 * Protocol (JSON messages, bidirectional):
 *   client → server:
 *     { type: 'input',  data: string }
 *     { type: 'resize', cols: number, rows: number }
 *     { type: 'ping' }
 *   server → client:
 *     { type: 'output', data: string }
 *     { type: 'exit',   exitCode: number }
 *     { type: 'ready',  shell: string, cwd: string }
 *     { type: 'error',  message: string }
 *
 * Spawns a real pseudo-terminal (node-pty) bound to the user's native shell:
 *   - Windows: powershell.exe (ConPTY)
 *   - macOS:   zsh (login)
 *   - Linux:   bash (login), fallback sh
 *
 * One PTY per WS connection; killed on disconnect.
 */
import type { WebSocketServer, WebSocket } from 'ws'
import nodePty from 'node-pty'
import { resolve } from 'path'
import { existsSync, statSync } from 'fs'
import { getProjectRoot } from '~/server/utils/claude-config'
import { verifyToken } from '~/server/utils/auth-verify'
import { getDynamicAuthConfig } from '~/server/utils/dynamic-config'
import { getTreeStorageAbsolutePath } from '~/server/utils/runtime-paths'
import { resolveWithinAnyRoot } from '~/server/utils/safe-paths'

/** Resolve a safe default shell + args for the host platform. */
function resolveShell(): { file: string; args: string[] } {
  if (process.platform === 'win32') {
    // PowerShell is the most capable default on modern Windows; ConPTY handles
    // ANSI/VT sequences and resize cleanly.
    return { file: 'powershell.exe', args: ['-NoLogo'] }
  }
  if (process.platform === 'darwin') {
    return { file: 'zsh', args: ['-l'] }
  }
  // Linux: bash login shell, fall back to sh.
  return { file: 'bash', args: ['-l'] }
}

/** cwd allowlist: project root + tree storage. Anything else falls back to the
 *  project root — the WS terminal must never spawn a shell at an arbitrary
 *  attacker-chosen path (P0 fix 2026-10-04). */
function resolveCwd(requested?: string | null): string {
  const fallback = getProjectRoot()
  const roots = [fallback, getTreeStorageAbsolutePath()].filter(Boolean)
  if (!requested) return fallback
  const abs = resolve(requested)
  const allowed = resolveWithinAnyRoot(abs, roots)
  if (!allowed) return fallback
  try {
    if (existsSync(allowed) && statSync(allowed).isDirectory()) return allowed
  } catch {
    /* invalid path — fall through to project root */
  }
  return fallback
}

/** Extract the caller's token from the upgrade request: `?token=` query param
 *  first (the only channel a browser WS has), then the same headers the HTTP
 *  middleware accepts. */
function extractToken(peer: any): string {
  try {
    const url = peer.request?.url ? new URL(peer.request.url, 'http://x') : null
    const qp = url?.searchParams.get('token')?.trim()
    if (qp) return qp
    const headers = peer.request?.headers || {}
    const auth = String(headers.authorization || '')
    if (auth.toLowerCase().startsWith('bearer ')) return auth.slice(7).trim()
    return String(headers['x-kb-token'] || '').trim()
  } catch {
    return ''
  }
}

export default defineWebSocketHandler({
  async open(peer) {
    const ws = peer.websocket as WebSocket

    // ── Prod guard ─────────────────────────────────────────────────
    // The PTY works under `nuxt dev` but in the built Nitro server the WS
    // open() async chain (auth-verify $fetch / node-pty spawn) hangs and
    // eventually kills the whole process (Windows, crossws prod runtime —
    // verified 2026-10-04). Fail fast with a clear message instead of
    // hanging the client and crashing the server. Needs a dedicated PTY
    // host process to support prod.
    if (process.env.APP_MODE === 'prod') {
      ws.send(JSON.stringify({
        type: 'error',
        message: '终端服务当前仅支持 dev 模式（prod 集成终端需独立 PTY 宿主进程，待后续支持）',
      }))
      peer.close()
      return
    }

    // ── Auth gate (P0 fix 2026-10-04) ──────────────────────────────
    // Nitro's HTTP auth middleware does NOT run for WS upgrades (verified:
    // unauthenticated upgrades reached this handler and spawned a shell),
    // so the terminal enforces the same policy itself.
    const { enabled } = getDynamicAuthConfig()
    if (enabled) {
      const token = extractToken(peer)
      const result = token ? await verifyToken(token) : { ok: false, reason: 'missing' }
      if (!result.ok) {
        ws.send(JSON.stringify({
          type: 'error',
          message: '认证失败: 终端需要有效 token（?token= 或 Authorization 头）',
        }))
        peer.close()
        return
      }
      ;(peer as any)._authUser = result.user
    }

    const cwd = resolveCwd(peer.request?.url ? new URL(peer.request.url, 'http://x').searchParams.get('cwd') : null)
    const { file: shell, args } = resolveShell()

    let pty: nodePty.IPty
    try {
      pty = nodePty.spawn(shell, args, {
        name: 'xterm-256color',
        cols: 80,
        rows: 24,
        cwd,
        // NOTE: no `encoding` option — node-pty ≥1.1 rejects it on Windows
        // ("Setting encoding on Windows is not supported") and the async throw
        // takes down the whole Nitro process (prod crash root cause, fixed
        // 2026-10-04). Output is UTF-8 by default anyway.
        env: { ...process.env, TERM: 'xterm-256color', COLORTERM: 'truecolor' } as Record<string, string>,
      })
    } catch (err) {
      ws.send(JSON.stringify({ type: 'error', message: `Failed to spawn ${shell}: ${(err as Error).message}` }))
      peer.close()
      return
    }

    // Stash the pty on the peer for cleanup in close().
    ;(peer as any)._pty = pty
    ;(peer as any)._ws = ws

    ws.send(JSON.stringify({ type: 'ready', shell, cwd, pid: pty.pid }))

    pty.onData((data: string) => {
      if (ws.readyState === ws.OPEN) {
        ws.send(JSON.stringify({ type: 'output', data }))
      }
    })

    pty.onExit(({ exitCode }: { exitCode: number }) => {
      if (ws.readyState === ws.OPEN) {
        ws.send(JSON.stringify({ type: 'exit', exitCode }))
        ws.close()
      }
    })
  },

  message(peer, message) {
    const pty = (peer as any)._pty as nodePty.IPty | undefined
    if (!pty) return

    let payload: { type?: string; data?: string; cols?: number; rows?: number }
    try {
      payload = JSON.parse(message.text())
    } catch {
      return // ignore malformed frames
    }

    switch (payload.type) {
      case 'input':
        if (typeof payload.data === 'string') pty.write(payload.data)
        break
      case 'resize':
        if (payload.cols && payload.rows) pty.resize(payload.cols, payload.rows)
        break
      case 'ping':
        // keep-alive; no response needed
        break
    }
  },

  close(peer) {
    const pty = (peer as any)._pty as nodePty.IPty | undefined
    if (pty) {
      try { pty.kill() } catch { /* already dead */ }
      ;(peer as any)._pty = undefined
    }
  },

  error(peer, error) {
    const pty = (peer as any)._pty as nodePty.IPty | undefined
    if (pty) {
      try { pty.kill() } catch { /* already dead */ }
    }
    // eslint-disable-next-line no-console
    console.error('[terminal ws] error:', error)
  },
})
