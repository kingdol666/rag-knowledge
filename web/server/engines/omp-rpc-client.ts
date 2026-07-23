/**
 * OMP RPC client — manages a single `bun omp --mode rpc` subprocess.
 *
 * Protocol: newline-delimited JSON over stdio.
 *   stdin:  JSONL commands ({ type: "prompt", ... })
 *   stdout: JSONL frames (events, responses, ready)
 *
 * Each HTTP request spawns one OMP RPC process (consistent with Claude SDK's
 * per-query binary spawn). Process is killed when the query completes or the
 * HTTP connection closes.
 */
import { spawn, type ChildProcess, execFileSync } from 'child_process'
import { existsSync } from 'fs'

/**
 * Resolve the OMP CLI executable.
 * Priority:
 *   1. Local bundled cli.js (when @oh-my-pi/pi-coding-agent is npm-installed)
 *   2. The `omp` binary on PATH (global Bun install)
 * Returns the spawn target as { command, args }. The local cli.js must run
 * under `bun` (Bun-bundled script); the global `omp` binary runs directly.
 */
function resolveOmpCli(cwd: string): { command: string; args: string[] } {
  // 1) Local package (optional) — npm-installed @oh-my-pi/pi-coding-agent.
  try {
    const { createRequire } = require('module')
    const r = createRequire(import.meta.url + '/../..')
    const cliPath = r.resolve('@oh-my-pi/pi-coding-agent/dist/cli.js')
    if (existsSync(cliPath)) {
      return { command: 'bun', args: [cliPath] }
    }
  } catch { /* package not installed */ }
  // 2) Global `omp` binary on PATH.
  const probe = process.platform === 'win32' ? 'where' : 'which'
  try {
    execFileSync(probe, ['omp'], { stdio: 'ignore' })
    return { command: 'omp', args: [] }
  } catch { /* omp not on PATH */ }
  throw new Error(
    "OMP CLI not found. Install it globally (`bun add -g @oh-my-pi/pi-coding-agent`) "
    + "or locally (`npm i @oh-my-pi/pi-coding-agent`) in web/.",
  )
}

interface PendingRequest {
  resolve: (frame: any) => void
  reject: (err: Error) => void
  timer: ReturnType<typeof setTimeout>
}

export class OmpRpcClient {
  private proc: ChildProcess
  private buffer = ''
  private seq = 0
  private pending = new Map<string, PendingRequest>()
  private readyPromise = Promise.withResolvers<void>()
  private ready = false
  private killed = false
  private eventListeners: ((frame: any) => void)[] = []

  constructor(
    private cwd: string,
    private model?: string,
    private sessionPath?: string,
  ) {
    const cli = resolveOmpCli(cwd)
    const args = [...cli.args, '--mode', 'rpc', '--cwd', cwd]
    if (model) args.push('--model', model)
    // Resume a prior session: OMP's CLI accepts `--resume <sessionId>` to load
    // the on-disk JSONL, restoring full multi-turn context across requests.
    if (sessionPath) args.push('--resume', sessionPath)

    this.proc = spawn(cli.command, args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
      env: { ...process.env },
    })


    this.proc.stdout!.on('data', (chunk: Buffer) => this.onStdout(chunk))
    this.proc.stderr!.on('data', () => {
      /* Swallow stderr — OMP logs diagnostics we don't need */
    })
    this.proc.on('error', (err) => {
      if (!this.killed) {
        for (const [, p] of this.pending) {
          clearTimeout(p.timer)
          p.reject(err)
        }
        this.pending.clear()
      }
    })
    this.proc.on('exit', () => {
      // Reject any pending requests on unexpected exit
      for (const [, p] of this.pending) {
        clearTimeout(p.timer)
        p.reject(new Error('OMP process exited unexpectedly'))
      }
      this.pending.clear()
    })
  }

  /** Wait for the `{ type: "ready" }` frame. */
  async waitReady(timeoutMs = 30000): Promise<void> {
    const timer = setTimeout(() => {
      throw new Error('OMP RPC: ready timeout (30s)')
    }, timeoutMs)
    await this.readyPromise
    clearTimeout(timer)
    this.ready = true
  }

  private onStdout(chunk: Buffer) {
    this.buffer += chunk.toString('utf8')
    let idx: number
    while ((idx = this.buffer.indexOf('\n')) >= 0) {
      const line = this.buffer.slice(0, idx).trim()
      this.buffer = this.buffer.slice(idx + 1)
      if (!line) continue
      try {
        const frame = JSON.parse(line)
        this.handleFrame(frame)
      } catch {
        /* Non-JSON line — ignore */
      }
    }
  }

  private handleFrame(frame: any) {
    // Ready frame
    if (frame.type === 'ready') {
      this.readyPromise.resolve()
      return
    }

    // Command response (has id + type === 'response')
    if (frame.type === 'response' && frame.id) {
      const pending = this.pending.get(frame.id)
      if (pending) {
        this.pending.delete(frame.id)
        clearTimeout(pending.timer)
        pending.resolve(frame)
      }
      return
    }

    // Extension UI requests — auto-dismiss (no terminal surface in headless mode)
    if (frame.type === 'extension_ui_request') {
      this.write({
        type: 'extension_ui_response',
        id: frame.id,
        cancelled: true,
      })
      return
    }

    // Host tool calls — auto-deny (headless, no host tools registered)
    if (frame.type === 'host_tool_call') {
      this.write({
        type: 'host_tool_result',
        id: frame.id,
        isError: true,
        result: { content: [{ type: 'text', text: 'No host tools available' }] },
      })
      return
    }

    // Host URI requests — auto-deny
    if (frame.type === 'host_uri_request') {
      this.write({
        type: 'host_uri_result',
        id: frame.id,
        isError: true,
        error: 'No host URI schemes registered',
      })
      return
    }

    // All other frames are agent/session events — dispatch to listeners
    for (const listener of this.eventListeners) {
      listener(frame)
    }
  }

  /** Send a command, returns a promise that resolves with the response frame. */
  send(cmd: Record<string, any>, timeoutMs = 60000): Promise<any> {
    const id = `req_${++this.seq}`
    const { promise, resolve, reject } = Promise.withResolvers<any>()
    const timer = setTimeout(() => {
      this.pending.delete(id)
      reject(new Error(`OMP RPC timeout: ${cmd.type} (${timeoutMs}ms)`))
    }, timeoutMs)
    this.pending.set(id, { resolve, reject, timer })
    this.write({ id, ...cmd })
    return promise
  }

  /** Send a fire-and-forget command (no response expected). */
  sendNoWait(cmd: Record<string, any>): void {
    this.write({ id: `req_${++this.seq}`, ...cmd })
  }

  private write(frame: any): void {
    if (this.killed) return
    try {
      this.proc.stdin!.write(JSON.stringify(frame) + '\n')
    } catch {
      /* stdin closed */
    }
  }

  /** Subscribe to agent/session events. */
  onEvent(listener: (frame: any) => void): void {
    this.eventListeners.push(listener)
  }

  /** Send abort command. */
  abort(): void {
    this.sendNoWait({ type: 'abort' })
  }

  /** Kill the subprocess. */
  kill(): void {
    if (this.killed) return
    this.killed = true
    for (const [, p] of this.pending) clearTimeout(p.timer)
    this.pending.clear()
    try {
      this.proc.stdin?.end()
    } catch { /* already closed */ }
    try {
      this.proc.kill()
    } catch { /* already dead */ }
  }

  get isReady(): boolean {
    return this.ready
  }
}
