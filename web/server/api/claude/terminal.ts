/**
 * WebSocket PTY terminal endpoint — /api/claude/terminal
 *
 * Query params: ?cwd=<absolute path>   (defaults to project root)
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

/** Resolve and validate the requested cwd; fall back to project root. */
function resolveCwd(requested?: string | null): string {
  const fallback = getProjectRoot()
  if (!requested) return fallback
  const abs = resolve(requested)
  try {
    if (existsSync(abs) && statSync(abs).isDirectory()) return abs
  } catch {
    /* invalid path — fall through to project root */
  }
  return fallback
}

export default defineWebSocketHandler({
  open(peer) {
    const ws = peer.websocket as WebSocket
    const cwd = resolveCwd(peer.request?.url ? new URL(peer.request.url, 'http://x').searchParams.get('cwd') : null)
    const { file: shell, args } = resolveShell()

    let pty: nodePty.IPty
    try {
      pty = nodePty.spawn(shell, args, {
        name: 'xterm-256color',
        cols: 80,
        rows: 24,
        cwd,
        env: { ...process.env, TERM: 'xterm-256color', COLORTERM: 'truecolor' } as Record<string, string>,
        encoding: 'utf8',
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
