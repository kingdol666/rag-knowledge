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
 *
 * kb-mcp mounting (requireKbMcp): OMP discovers MCP servers through its native
 * provider from `<--cwd>/.omp/mcp.json` (OMP 18.12.2 src/discovery/builtin.ts,
 * "native" provider, loadMCPServers: `path.join(ctx.cwd, ".omp", "mcp.json")`,
 * priority 100). For KB-gated runs we point `--cwd` (and the child's OS cwd) at
 * a SHARED, stable per-checkout runtime project dir containing that config with
 * an ABSOLUTE kb-mcp command — the same mechanism as a direct `omp -p` from the
 * repo root, but hermetic (does not depend on the repo's checked-in config and
 * never touches user/global OMP config, no credentials).
 *
 * Tradeoff (documented, accepted): KB-gated calls lose work-cwd fidelity —
 * file/bash tools resolve against the runtime project. Every current caller of
 * requireKbMcp is the KB service agent, whose instruction preamble forbids repo
 * browsing, so nothing depends on the original cwd. The dir is shared and never
 * deleted because OMP keys on-disk sessions by cwd: a per-request temp dir
 * would vanish under a resumed session's feet and OMP's headless resume then
 * fails (promptMoveSession → "unavailable" on non-TTY, OMP main.ts). One
 * stable dir keeps `--resume <id>` working (OMP resolves ids globally across
 * project keys, session-listing.ts resolveResumableSession).
 *
 * Readiness: OMP 18.12.2 rpc mode NEVER lists MCP tools in `get_state`
 * dumpTools (rpc-mode.ts maps `session.agent.state.tools`, which holds only
 * the built-ins, even while the model sees and successfully calls
 * `mcp__kb_mcp_*` tools). The trustworthy rpc-visible signal is the tool
 * catalog embedded in `get_state.systemPrompt`, so waitForKbMcp polls both.
 */
import { spawn, type ChildProcess, execFileSync } from 'child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs'
import { createRequire } from 'module'
import { join, resolve } from 'path'
import { getMonorepoRoot } from '~/server/utils/runtime-paths'
import { isKbMcpTool } from '~/server/utils/kb-mcp-tools'

// kb-mcp can wait 90s for a peer startup and another 45s for its own.
// Allow time for both waits and OMP initialization before reporting a timeout.
const READY_TIMEOUT_MS = 180_000
const MAX_STDOUT_BUFFER = 1024 * 1024
// Bounded, sanitized stderr kept for failure diagnostics (never relayed raw).
const MAX_STDERR_TAIL_CHARS = 600

/**
 * Shared per-checkout runtime project dir that mounts kb-mcp for OMP via the
 * native `.omp/mcp.json` provider. Lives under the repo's gitignored `.run/`
 * (not the OS temp dir) so OMP sessions created under it stay resumable across
 * web restarts and temp-dir cleanup. Idempotent + self-healing: the config is
 * rewritten only when its content drifted.
 */
function ensureKbMcpProject(projectRoot: string): string {
  const project = join(resolve(projectRoot), '.run', 'omp-kb-project')
  const configPath = join(project, '.omp', 'mcp.json')
  const config = JSON.stringify({
    mcpServers: {
      'kb-mcp': {
        command: 'uv',
        args: ['run', '--no-sync', '--directory', join(projectRoot, 'kb-mcp'), 'python', 'server.py'],
      },
    },
  }, null, 2)
  try {
    if (!existsSync(configPath) || readFileSync(configPath, 'utf8') !== config) {
      mkdirSync(join(project, '.omp'), { recursive: true })
      writeFileSync(configPath, config, { mode: 0o600 })
    }
  } catch (error) {
    throw new Error(`Failed to prepare OMP kb-mcp project config at ${configPath}: ${(error as Error).message}`)
  }
  return project
}

// Never relay raw stderr: it may contain tokens, URLs, paths or prompt content.
// Keep only bounded, predefined categories for actionable startup diagnostics.
function diagnosticCategory(text: string): string | undefined {
  if (/timed?\s*out|timeout/i.test(text)) return 'timeout'
  if (/enoent|not found|no such file|cannot find/i.test(text)) return 'file or command not found'
  if (/eacces|permission denied/i.test(text)) return 'permission denied'
  if (/mcp/i.test(text) && /fail|error|disconnect/i.test(text)) return 'MCP connection failure'
  if (/error|failed|exception/i.test(text)) return 'startup error'
  return undefined
}

/**
 * Redact credential-looking spans before exposing a stderr tail in an error.
 * Bounded to a tail so a chatty child cannot bloat the message; whitespace is
 * collapsed so multi-line output stays a one-line diagnostic.
 */
export function sanitizeStderrTail(text: string, maxChars = MAX_STDERR_TAIL_CHARS): string {
  const redacted = text
    .replace(/((?:api[_-]?key|token|secret|password|passwd|authorization|bearer|credential)[\s"'=:]{1,4})[^\s"',;)\]}]+/gi, '$1<redacted>')
    .replace(/(https?:\/\/)[^\s/@:]+:[^\s/@]+@/g, '$1<redacted>@')
  const tail = redacted.length > maxChars ? redacted.slice(-maxChars) : redacted
  return tail.replace(/\s+/g, ' ').trim()
}

/**
 * Resolve the OMP CLI executable.
 * Priority:
 *   1. Local bundled cli.js (when @oh-my-pi/pi-coding-agent is npm-installed)
 *   2. The `omp` binary on PATH (global Bun install)
 * Returns the spawn target as { command, args }. The local cli.js must run
 * under `bun` (Bun-bundled script); the global `omp` binary runs directly.
 */
function resolveOmpCli(projectRoot: string): { command: string; args: string[] } {
  // 1) Local package (optional) — npm-installed @oh-my-pi/pi-coding-agent.
  try {
    const r = createRequire(resolve(projectRoot, 'web', 'package.json'))
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
  private readySettled = false
  private killed = false
  private terminalError?: Error
  private diagnostics = new Set<string>()
  private stderrFragment = ''
  private stderrTail = ''
  private mechanism: string
  private failureNotified = false
  private eventListeners: ((frame: any) => void)[] = []
  private errorListeners: ((err: Error) => void)[] = []

  constructor(
    private cwd: string,
    private model?: string,
    private sessionPath?: string,
    private thinking?: string,
    private requireKbMcp = false,
  ) {
    const projectRoot = getMonorepoRoot()
    const cli = resolveOmpCli(projectRoot)
    // KB-gated runs trade work-cwd fidelity for a guaranteed kb-mcp mount:
    // --cwd points at the shared runtime project that carries .omp/mcp.json
    // (see the file header for the evidence and the resume rationale).
    const workDir = requireKbMcp ? ensureKbMcpProject(projectRoot) : resolve(cwd)
    this.mechanism = requireKbMcp
      ? `kb-mcp via .run/omp-kb-project/.omp/mcp.json (--cwd ${workDir})`
      : `work dir (--cwd ${workDir})`
    const args = [...cli.args, '--mode', 'rpc', '--cwd', workDir]
    if (model) args.push('--model', model)
    // 思考强度：omp 官方旗标，档位随模型（omp models --json 的 thinking 数组）
    if (thinking) args.push('--thinking', thinking)
    // Resume a prior session: OMP's CLI accepts `--resume <sessionId>` to load
    // the on-disk JSONL, restoring full multi-turn context across requests.
    if (sessionPath) args.push('--resume', sessionPath)

    this.proc = spawn(cli.command, args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: workDir,
      windowsHide: true,
      // OMP defaults to a 250ms discovery window and a 30s MCP handshake,
      // both shorter than kb-mcp's serialized cold-start waits. The 0
      // startup window makes discovery settle (connected or failed) before
      // the RPC ready frame, so readiness polling converges fast. These
      // session-local overrides do not modify the user's OMP configuration.
      env: {
        ...process.env,
        RAG_PROJECT_ROOT: projectRoot,
        OMP_MCP_STARTUP_TIMEOUT_MS: '0',
        OMP_MCP_TIMEOUT_MS: '165000',
      },
    })

    // A child can fail before its caller reaches waitReady(). Mark rejection as
    // observed immediately, while preserving it for later awaiters.
    void this.readyPromise.promise.catch(() => {})
    this.proc.stdout!.on('data', (chunk: Buffer) => this.onStdout(chunk))
    this.proc.stderr!.on('data', (chunk: Buffer) => this.onStderr(chunk))
    this.proc.stdin!.on('error', () => { /* close/exit reports the failure */ })
    this.proc.on('error', (err) => {
      this.fail(new Error(`OMP process spawn failed (${err.name})`))
    })
    // close, unlike exit, fires after stderr has been drained.
    this.proc.on('close', (code, signal) => {
      if (!this.killed) {
        this.fail(new Error(`OMP process exited (code=${code}, signal=${signal || 'none'})${this.diagnosticSummary()}`))
      }
    })
  }

  /** Wait until OMP is ready and kb-mcp startup has had time to converge. */
  async waitReady(timeoutMs = READY_TIMEOUT_MS): Promise<void> {
    if (this.readySettled) {
      if (this.terminalError) throw this.terminalError
      return
    }
    const timer = setTimeout(() => {
      this.fail(new Error(`OMP RPC ready timeout (${timeoutMs}ms)${this.diagnosticSummary()}`))
      this.kill()
    }, timeoutMs)
    try {
      await this.readyPromise.promise
    } finally {
      clearTimeout(timer)
    }
  }

  /** Wait for OMP to register kb-mcp tools, not merely for its RPC ready frame. */
  async waitForKbMcp(timeoutMs = READY_TIMEOUT_MS, signal?: AbortSignal): Promise<void> {
    const deadline = Date.now() + timeoutMs
    while (Date.now() < deadline) {
      if (signal?.aborted) throw new Error('OMP kb-mcp readiness aborted')
      const remaining = deadline - Date.now()
      if (remaining <= 0) break
      const response = await this.send({ type: 'get_state' }, Math.min(remaining, 8000))
        .catch((error: Error) => {
          // A mid-poll transport death should surface its own message; only a
          // silent per-request timeout keeps the poll loop alive.
          if (this.terminalError) throw this.terminalError
          if (!/timeout/i.test(error.message)) throw error
          return null
        })
      if (response && (response.success !== true || typeof response?.data !== 'object' || response.data === null)) {
        throw new Error('OMP kb-mcp readiness unavailable: get_state did not return a valid state object')
      }
      if (response && this.stateCarriesKbMcp(response.data)) return
      const delay = Math.min(500, deadline - Date.now())
      if (delay > 0) {
        await new Promise<void>((resolveDelay, rejectDelay) => {
          const onAbort = () => { clearTimeout(timer); rejectDelay(new Error('OMP kb-mcp readiness aborted')) }
          const timer = setTimeout(() => { signal?.removeEventListener('abort', onAbort); resolveDelay() }, delay)
          signal?.addEventListener('abort', onAbort, { once: true })
          if (signal?.aborted) onAbort()
        })
      }
    }
    throw new Error(
      `OMP kb-mcp tools not ready within ${timeoutMs}ms; mechanism: ${this.mechanism}`
      + `${this.diagnosticSummary()}`,
    )
  }

  /**
   * kb-mcp readiness probe over the rpc-visible state. Two signals, both
   * passing through the shared kb-mcp tool-name normalization:
   *   1. dumpTools entries — works on OMP builds whose rpc state lists MCP
   *      tools directly.
   *   2. The model tool catalog embedded in `systemPrompt` — OMP 18.12.2 rpc
   *      never exposes MCP tools via dumpTools (see file header), but the
   *      prompt carries every mounted `mcp__kb_mcp_*` name once the server
   *      connects, so its presence is the reliable readiness proof.
   */
  private stateCarriesKbMcp(state: Record<string, unknown>): boolean {
    const dumpTools = (state as { dumpTools?: unknown }).dumpTools
    if (Array.isArray(dumpTools) && dumpTools.some((tool: unknown) =>
      typeof tool === 'object' && tool !== null && 'name' in tool &&
      typeof (tool as { name: unknown }).name === 'string' &&
      isKbMcpTool((tool as { name: string }).name),
    )) {
      return true
    }
    const systemPrompt = (state as { systemPrompt?: unknown }).systemPrompt
    if (!Array.isArray(systemPrompt)) return false
    const text = systemPrompt
      .map((block: unknown) => {
        if (typeof block === 'string') return block
        if (typeof block === 'object' && block !== null) {
          const b = block as { text?: unknown; content?: unknown }
          if (typeof b.text === 'string') return b.text
          if (typeof b.content === 'string') return b.content
        }
        return ''
      })
      .join('\n')
    for (const match of text.matchAll(/mcp__[A-Za-z0-9_-]+/g)) {
      if (isKbMcpTool(match[0])) return true
    }
    return false
  }

  private fail(err: Error): void {
    this.terminalError = err
    this.ready = false
    if (!this.readySettled) {
      this.readySettled = true
      this.readyPromise.reject(err)
    }
    for (const [, p] of this.pending) {
      clearTimeout(p.timer)
      p.reject(err)
    }
    this.pending.clear()
    if (!this.failureNotified) {
      this.failureNotified = true
      for (const listener of this.errorListeners) listener(err)
    }
  }

  private diagnosticSummary(): string {
    const parts: string[] = []
    if (this.diagnostics.size) parts.push(`diagnostics: ${[...this.diagnostics].join(', ')}`)
    const tail = sanitizeStderrTail(this.stderrTail)
    if (tail) parts.push(`stderr tail: "${tail}"`)
    return parts.length ? `; ${parts.join('; ')}` : ''
  }

  private onStderr(chunk: Buffer): void {
    const text = chunk.toString('utf8')
    this.stderrFragment += text
    // Bound a partial line too; stderr is drained even for unbroken output.
    if (this.stderrFragment.length > 2048) this.stderrFragment = this.stderrFragment.slice(-2048)
    this.stderrTail = (this.stderrTail + text).slice(-2048)
    let newline: number
    while ((newline = this.stderrFragment.indexOf('\n')) >= 0) {
      const line = this.stderrFragment.slice(0, newline)
      this.stderrFragment = this.stderrFragment.slice(newline + 1)
      const category = diagnosticCategory(line)
      if (category && this.diagnostics.size < 5) this.diagnostics.add(category)
    }
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
    // Discard runaway non-JSON output rather than accumulating it forever.
    if (this.buffer.length > MAX_STDOUT_BUFFER) {
      this.buffer = ''
      this.diagnostics.add('oversized stdout frame')
    }
  }

  private handleFrame(frame: any) {
    // Ready frame
    if (frame.type === 'ready') {
      if (!this.readySettled) {
        this.readySettled = true
        this.ready = true
        this.readyPromise.resolve()
      }
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
    if (this.terminalError) return Promise.reject(this.terminalError)
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

  /** Subscribe to a terminal transport failure (once per child process). */
  onError(listener: (err: Error) => void): void {
    this.errorListeners.push(listener)
    if (this.terminalError) listener(this.terminalError)
  }

  /** Send abort command. */
  abort(): void {
    this.sendNoWait({ type: 'abort' })
  }

  /** Kill the subprocess. */
  kill(): void {
    if (this.killed) return
    this.killed = true
    this.fail(this.terminalError || new Error('OMP process stopped'))
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
