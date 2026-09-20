/**
 * ACP ChatEngine adapter — Agent Client Protocol v1 over stdio.
 *
 * Drives one full ACP session turn per query(): initialize → session/new →
 * session/prompt, translating agent updates into StandardMessage frames.
 *
 * ⭐ Real HITL: the agent's `session/request_permission` calls are forwarded
 * verbatim (tool title/kind + the harness-provided option list) to the
 * platform approval UI via onPermissionRequest; the user's selected
 * optionId is sent back as the ACP `selected` outcome. When the session
 * permission mode is bypassPermissions the adapter auto-picks allow_always.
 *
 * Sessions: ACP gives us a fresh session per spawned process, so multi-turn
 * continuity uses server-side history replay (QueryRequest.history) — the
 * full transcript is embedded in the prompt block.
 *
 * Spawn discipline (matches the backend registry): fully literal argv built
 * per harness — no dynamic program path, no shell. The CLI is resolved from
 * PATH by the OS itself; availability is probed separately via
 * resolveCommandLocal (pure filesystem scan).
 */
import { spawn, type ChildProcess, type SpawnOptions } from 'child_process'
import { existsSync, readFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { AsyncQueue } from './async-queue'
import type {
  ChatEngine,
  PermissionRequestOption,
  QueryRequest,
  StandardMessage,
} from './types'
import { resolveCommandLocal } from '~/server/utils/harness-catalog'

/**
 * MCP servers handed to the agent via ACP `session/new` (protocol-native
 * skill access — ACP harnesses get the platform's kb-mcp tools without any
 * per-user CLI config).
 *
 * Transport is per harness: dsh declares mcpCapabilities {http:true} only
 * (stdio servers are ignored), so we lazily start a kb-mcp SSE sidecar and
 * hand over its URL. stdio servers (from the monorepo .mcp.json) are passed
 * to harnesses that spawn them themselves (hermes).
 */

let _kbHttp: { proc: ChildProcess | null; url: string } | null = null

function monorepoRoot(): string {
  return resolve(dirname(fileURLToPath(import.meta.url)), '../../../..') // engines/ -> server/ -> web/ -> repo
}

async function ensureKbMcpHttp(): Promise<string | null> {
  if (_kbHttp) return _kbHttp.url
  const root = monorepoRoot()
  const port = Number(process.env.KB_MCP_HTTP_PORT || 8801)
  const url = `http://127.0.0.1:${port}/sse`
  // SSRF guard: the only URL ever contacted here is our own loopback
  // sidecar — enforce scheme/host/port against a literal allowlist before
  // any fetch (the URL string is never user-controlled).
  const allowedHosts = new Set(['127.0.0.1', 'localhost', '[::1]'])
  const probe = async (candidate: string): Promise<boolean> => {
    let parsed: URL
    try {
      parsed = new URL(candidate)
    } catch {
      return false
    }
    if (parsed.protocol !== 'http:') return false
    if (!allowedHosts.has(parsed.hostname)) return false
    if (parsed.port !== String(port)) return false
    try {
      const res = await fetch(parsed.toString(), { method: 'GET', signal: AbortSignal.timeout(1500) })
      return res.status < 500
    } catch {
      return false // not up yet
    }
  }
  // Adopt an already-healthy sidecar first (survives Nitro HMR module
  // reloads, which reset module state and would otherwise double-spawn).
  if (await probe(url)) {
    _kbHttp = { proc: null, url }
    return url
  }
  const proc = (process.platform === 'win32'
    ? spawn('cmd.exe', ['/d', '/s', '/c', 'uv', 'run', '--directory', resolve(root, 'kb-mcp'), 'python', 'server.py', '--http'], {
        stdio: ['ignore', 'ignore', 'pipe'],
        windowsHide: true,
        env: { ...process.env, KB_MCP_HTTP_PORT: String(port) },
      })
    : spawn('uv', ['run', '--directory', resolve(root, 'kb-mcp'), 'python', 'server.py', '--http'], {
        stdio: ['ignore', 'ignore', 'pipe'],
        windowsHide: true,
        env: { ...process.env, KB_MCP_HTTP_PORT: String(port) },
      }))
  proc.on('error', (err) => {
    console.error(`[acp] kb-mcp SSE sidecar spawn failed: ${err.message}`)
    _kbHttp = null
  })
  proc.stderr?.on('data', () => { /* drain FastMCP logs */ })
  proc.on('exit', (code) => {
    console.warn(`[acp] kb-mcp SSE sidecar exited (code=${code})`)
    _kbHttp = null
  })
  _kbHttp = { proc, url }
  // Wait for the SSE endpoint to accept connections (≤20s)
  for (let i = 0; i < 40; i++) {
    if (proc.exitCode !== null) return null
    if (await probe(url)) return url
    await new Promise(r => setTimeout(r, 500))
  }
  return null
}

function stdioMcpServers(): Array<Record<string, unknown>> {
  try {
    const root = monorepoRoot()
    const mcpJson = resolve(root, '.mcp.json')
    if (!existsSync(mcpJson)) return []
    const parsed = JSON.parse(readFileSync(mcpJson, 'utf-8'))
    const out: Array<Record<string, unknown>> = []
    for (const [name, cfg] of Object.entries(parsed.mcpServers || {})) {
      const c = cfg as { command: string; args?: string[]; env?: Record<string, string> }
      if (!c?.command) continue
      const args = (c.args || []).map((a) => {
        // Anchor relative --directory/--add-dir style paths to the repo root.
        if (/^(\.\.|[A-Za-z0-9_.-]+$)/.test(a) && !a.startsWith('-')) {
          const abs = resolve(root, a)
          return existsSync(abs) ? abs : a
        }
        return a
      })
      out.push({
        name,
        command: c.command,
        args,
        env: {
          ...(c.env || {}),
          APP_MODE: c.env?.APP_MODE || 'dev',
          RAG_PROJECT_ROOT: c.env?.RAG_PROJECT_ROOT || root,
        },
      })
    }
    return out
  } catch {
    return []
  }
}

async function acpMcpServers(harness: string): Promise<Array<Record<string, unknown>>> {
  if (harness === 'dsh') {
    // dsh only connects HTTP-transport MCP servers.
    const url = await ensureKbMcpHttp()
    return url ? [{ name: 'kb-mcp', type: 'http', url }] : []
  }
  return stdioMcpServers() // hermes: stdio servers it spawns itself
}

export class AcpEngine implements ChatEngine {
  constructor(readonly name: string) {}

  /**
   * Apply the caller's model / reasoning-effort choices via ACP
   * `session/set_config_option` — the protocol-native per-session settings
   * channel (dsh exposes configIds `model` and `reasoning_effort`; effort
   * values are validated per-model by the agent itself).
   */
  private async applySessionConfigs(
    sessionId: string,
    configOptions: Array<Record<string, any>>,
    request: (method: string, params: any, timeoutMs?: number) => Promise<any>,
    req: QueryRequest,
  ): Promise<void> {
    const wanted: Array<[string, string]> = []
    if (req.model) wanted.push(['model', req.model])
    if (req.reasoningEffort) wanted.push(['reasoning_effort', req.reasoningEffort])
    for (const [configId, value] of wanted) {
      if (!configOptions.some(o => String(o?.id) === configId)) continue
      try {
        await request('session/set_config_option', {
          sessionId, configId, value,
        }, 15000)
      } catch (e) {
        console.warn(`[acp:${this.name}] set_config_option ${configId}=${value} failed:`,
          e instanceof Error ? e.message : e)
      }
    }
  }

  /**
   * Map the chat permission mode to the harness's REAL env knob.
   * dsh's acp profile composes its approval policy from DSH_PERMISSION_MODE:
   *   read-only / workspace-write → approval=ask (real HITL via
   *   session/request_permission), danger-full-access → approval=never.
   * (The user's global ~/.dsh defaultPreset is danger-full-access; injecting
   * the env per spawn gives per-session HITL without touching that config.)
   */
  private permissionEnv(mode: string): Record<string, string> {
    if (this.name !== 'dsh') return {}
    if (mode === 'bypassPermissions') return { DSH_PERMISSION_MODE: 'danger-full-access' }
    if (mode === 'acceptEdits') return { DSH_PERMISSION_MODE: 'workspace-write' }
    if (mode === 'plan') return { DSH_PERMISSION_MODE: 'read-only' }
    // default: read-only sandbox + approval=ask — the safe chat default
    // (agents with shell access under workspace-write can write freely).
    return { DSH_PERMISSION_MODE: 'read-only' }
  }

  async *query(req: QueryRequest): AsyncIterable<StandardMessage> {
    // ── Availability note (advisory; OS PATH resolves at spawn) ─────────
    const cmdName = this.name === 'dsh' ? 'dsh' : 'hermes'
    if (!resolveCommandLocal(cmdName)) {
      console.warn(`[chat] local scan missed '${this.name}' binary — relying on OS PATH resolution`)
    }

    // ── Literal spawn tables (one row per harness × platform) ──────────
    const opts: SpawnOptions = {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
      cwd: req.cwd,
      env: { ...process.env, ...this.permissionEnv(req.permissionMode) },
    }
    let proc: ChildProcess
    if (process.platform === 'win32') {
      if (this.name === 'hermes') {
        proc = spawn('cmd.exe', ['/d', '/s', '/c', 'hermes', 'acp'], opts)
      } else {
        proc = spawn('cmd.exe', ['/d', '/s', '/c', 'dsh', '--profile', 'acp'], opts)
      }
    } else {
      if (this.name === 'hermes') {
        proc = spawn('hermes', ['acp'], opts)
      } else {
        proc = spawn('dsh', ['--profile', 'acp'], opts)
      }
    }
    let stderrTail = ''
    proc.stderr!.on('data', (c: Buffer) => {
      // Keep the last chunk for error surfacing (ACP agents log here by spec).
      stderrTail = c.toString('utf8').slice(-800)
    })

    const queue = new AsyncQueue<StandardMessage>()
    const state = {
      sessionId: '',
      text: '',
      startTime: Date.now(),
      autoApprove: req.permissionMode === 'bypassPermissions',
      promptDone: Promise.withResolvers<any>(),
      promptDoneSettled: false,
      promptReqId: null as number | string | null,
      nextId: 1,
      finished: false,
    }
    const pending = new Map<number | string, {
      resolve: (v: any) => void
      reject: (e: Error) => void
    }>()

    const finish = (err?: string): void => {
      if (state.finished) return
      state.finished = true
      if (err) {
        queue.push({
          type: 'result', result: state.text, is_error: true, total_cost_usd: 0,
          duration_ms: Date.now() - state.startTime, num_turns: 1,
          usage: { input_tokens: 0, output_tokens: 0 },
          stop_reason: 'error', terminal_reason: err,
          session_id: state.sessionId,
        })
      }
      queue.close()
    }

    const send = (obj: Record<string, any>): void => {
      try {
        proc.stdin!.write(JSON.stringify(obj) + '\n')
      } catch { /* stdin closed */ }
    }
    const request = (method: string, params: any, timeoutMs = 30000): Promise<any> => {
      const id = state.nextId++
      const { promise, resolve, reject } = Promise.withResolvers<any>()
      pending.set(id, { resolve, reject })
      const timer = setTimeout(() => {
        if (pending.has(id)) {
          pending.delete(id)
          reject(new Error(`ACP timeout: ${method} (${timeoutMs}ms)`))
        }
      }, timeoutMs)
      timer.unref?.()
      send({ jsonrpc: '2.0', id, method, params })
      return promise
    }

    const respondPermission = (
      reqId: number | string,
      options: PermissionRequestOption[],
      decision: { behavior: string; optionId?: string; message?: string },
    ): void => {
      if (decision.behavior === 'allow') {
        // Pick the user's optionId, else the first allow_* option, else cancelled.
        const chosen
          = options.find(o => o.optionId === decision.optionId)
            ?? options.find(o => String(o.kind).startsWith('allow'))
        if (chosen) {
          send({
            jsonrpc: '2.0', id: reqId,
            result: { outcome: { outcome: 'selected', optionId: chosen.optionId } },
          })
          return
        }
      } else {
        const rejected = options.find(o => String(o.kind).startsWith('reject'))
        if (rejected) {
          send({
            jsonrpc: '2.0', id: reqId,
            result: { outcome: { outcome: 'selected', optionId: rejected.optionId } },
          })
          return
        }
      }
      send({ jsonrpc: '2.0', id: reqId, result: { outcome: { outcome: 'cancelled' } } })
    }

    const handleServerRequest = async (id: number | string, method: string, params: any) => {
      if (method === 'session/request_permission') {
        const options: PermissionRequestOption[] = Array.isArray(params?.options)
          ? params.options.map((o: any) => ({
              optionId: String(o.optionId ?? o.id ?? ''),
              name: String(o.name ?? o.optionId ?? ''),
              kind: String(o.kind ?? ''),
            }))
          : []
        const toolName = String(params?.toolCall?.title || params?.toolCall?.toolName || params?.toolCall?.kind || 'tool')
        const input = (params?.toolCall?.rawInput ?? params?.toolCall?._meta ?? {}) as Record<string, unknown>
        if (state.autoApprove) {
          const allowAlways = options.find(o => o.kind === 'allow_always')
            ?? options.find(o => String(o.kind).startsWith('allow'))
          if (allowAlways) {
            send({ jsonrpc: '2.0', id, result: { outcome: { outcome: 'selected', optionId: allowAlways.optionId } } })
            return
          }
        }
        try {
          const decision = await req.onPermissionRequest?.(
            toolName, input, String(id), state.sessionId, options,
          ) ?? { behavior: 'deny', message: 'No approval handler' }
          respondPermission(id, options, decision)
        } catch (e) {
          respondPermission(id, options, {
            behavior: 'deny',
            message: e instanceof Error ? e.message : 'approval error',
          })
        }
        return
      }
      // fs/read_text_file & fs/write_text_file (ACP fs API) — not implemented;
      // answer method-not-found per JSON-RPC so the agent can degrade.
      send({
        jsonrpc: '2.0', id,
        error: { code: -32601, message: `client does not implement ${method}` },
      })
    }

    const handleUpdate = (upd: any) => {
      const kind = String(upd?.sessionUpdate || '')
      if (kind === 'agent_message_chunk' || kind === 'agent_message' || kind === 'agent_thought_chunk') {
        const c = upd.content || {}
        const text = typeof c === 'object' ? (c.text ?? '') : String(c ?? '')
        if (kind === 'agent_thought_chunk') {
          if (text) {
            queue.push({
              type: 'stream_event',
              event: { type: 'content_block_delta', index: 1, delta: { type: 'thinking_delta', thinking: text } },
            })
          }
          return
        }
        if (text) {
          state.text += text
          queue.push({
            type: 'stream_event',
            event: { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text } },
          })
        }
      } else if (kind === 'tool_call') {
        const tid = String(upd.toolCallId || `tu_${Date.now()}`)
        queue.push({
          type: 'assistant',
          message: {
            role: 'assistant',
            content: [{ type: 'tool_use', id: tid, name: String(upd.title || upd.kind || 'tool'), input: upd.rawInput ?? {} }],
          },
        })
      } else if (kind === 'tool_call_update') {
        const tid = String(upd.toolCallId || '')
        if (upd.status === 'completed' || upd.status === 'failed') {
          queue.push({
            type: 'user',
            message: {
              role: 'user',
              content: [{ type: 'tool_result', tool_use_id: tid, content: upd.rawOutput ?? upd.content ?? '', is_error: upd.status === 'failed' }],
            },
          })
        }
      }
      // plan / available_commands_update / others — not rendered yet
    }

    proc.on('error', (err) => {
      finish(`spawn failed: ${err.message}`)
    })

    let buffer = ''
    proc.stdout!.on('data', (chunk: Buffer) => {
      buffer += chunk.toString('utf8')
      let idx: number
      while ((idx = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, idx).trim()
        buffer = buffer.slice(idx + 1)
        if (!line) continue
        let msg: any
        try {
          msg = JSON.parse(line)
        } catch { continue }
        if (!msg || typeof msg !== 'object') continue

        if ('id' in msg && 'method' in msg) {
          void handleServerRequest(msg.id, String(msg.method), msg.params)
          continue
        }
        if ('id' in msg && ('result' in msg || 'error' in msg)) {
          const p = pending.get(msg.id)
          if (p) {
            pending.delete(msg.id)
            if (msg.error) p.reject(new Error(String(msg.error.message || JSON.stringify(msg.error)).slice(0, 300)))
            else p.resolve(msg.result)
          }
          if (msg.id === state.promptReqId && !state.promptDoneSettled) {
            state.promptDoneSettled = true
            const promptErr = msg.error
              ? String(msg.error.message || JSON.stringify(msg.error)).slice(0, 300)
              : ''
            const stop = String(msg.result?.stopReason ?? (msg.error ? 'error' : 'end_turn'))
            queue.push({
              type: 'result',
              result: state.text,
              is_error: Boolean(msg.error),
              total_cost_usd: 0,
              duration_ms: Date.now() - state.startTime,
              num_turns: 1,
              usage: { input_tokens: 0, output_tokens: 0 },
              stop_reason: msg.error ? 'error' : stop,
              terminal_reason: msg.error ? `prompt error: ${promptErr}` : stop,
              session_id: state.sessionId,
            })
            state.promptDone.resolve(msg.result)
          }
          continue
        }
        if (msg.method === 'session/update') {
          handleUpdate(msg.params?.update ?? msg.params)
        }
      }
    })

    proc.on('exit', (code) => {
      if (!state.promptDoneSettled) {
        state.promptDoneSettled = true
        state.promptDone.reject(new Error(
          `ACP process exited before turn end (code=${code})${stderrTail ? ` stderr: ${stderrTail.slice(-300)}` : ''}`))
      }
      finish(`ACP process exited unexpectedly (code=${code})${stderrTail ? ` stderr: ${stderrTail.slice(-300)}` : ''}`)
    })

    if (req.signal) {
      req.signal.addEventListener('abort', () => {
        try { proc.stdin?.end() } catch { /* closed */ }
        try { proc.kill() } catch { /* already dead */ }
        finish('aborted by client disconnect')
      }, { once: true })
    }

    try {
      await request('initialize', {
        protocolVersion: 1,
        clientCapabilities: {},
        clientInfo: { name: 'rag-knowledge-web', title: 'RAG Knowledge Platform', version: '1.0' },
      })
      const sess = await request('session/new', { cwd: req.cwd, mcpServers: await acpMcpServers(this.name) })
      state.sessionId = String(sess?.sessionId ?? sess?.session_id ?? '')
      const configOptions: Array<Record<string, any>> = Array.isArray(sess?.configOptions)
        ? sess.configOptions
        : []
      await this.applySessionConfigs(state.sessionId, configOptions, request, req)

      queue.push({
        type: 'system', subtype: 'init',
        session_id: state.sessionId, model: req.model || 'default',
        cwd: req.cwd, permissionMode: req.permissionMode,
        tools: [], mcp_servers: [], slash_commands: [],
      })

      // History replay: ACP sessions are per-process, so continuity comes
      // from embedding the prior transcript in the prompt block.
      const hist = req.history || []
      const transcript = hist
        .map(m => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.text}`)
        .join('\n\n')
      const promptText = transcript
        ? `<conversation_history>\n${transcript}\n</conversation_history>\n\nUser: ${req.fullPromptText}`
        : req.fullPromptText

      state.promptReqId = state.nextId++
      send({
        jsonrpc: '2.0', id: state.promptReqId, method: 'session/prompt',
        params: {
          sessionId: state.sessionId,
          prompt: [{ type: 'text', text: promptText }],
        },
      })

      await state.promptDone.promise
      finish()
    } catch (e) {
      finish(e instanceof Error ? e.message : String(e))
    } finally {
      // Protocol engines exit on stdin EOF; kill is the fallback.
      try { proc.stdin?.end() } catch { /* closed */ }
      setTimeout(() => {
        try { proc.kill() } catch { /* already dead */ }
      }, 300)
    }

    for await (const msg of queue) {
      yield msg
    }
  }
}

// ── ACP configOptions probe（模型/思考强度下拉的数据源） ───────────────

export interface AcpConfigOptionSummary {
  modelOptions: Array<{ value: string; name: string; group?: string }>
  currentModel?: string
  reasoningEfforts: Array<{ value: string; name: string; description?: string }>
  currentEffort?: string
}

/**
 * Spawn the ACP harness once, read `session/new` configOptions (the agent's
 * own model catalog + reasoning-effort levels), and exit. Powers
 * GET /api/harnesses/dsh/models without running any prompt.
 */
export async function acpProbeConfigOptions(name: string): Promise<AcpConfigOptionSummary | null> {
  const cmdName = name === 'dsh' ? 'dsh' : 'hermes'
  if (!resolveCommandLocal(cmdName)) return null

  const opts: SpawnOptions = {
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
    cwd: monorepoRoot(),
    env: { ...process.env },
  }
  let proc: ChildProcess
  if (process.platform === 'win32') {
    if (name === 'hermes') {
      proc = spawn('cmd.exe', ['/d', '/s', '/c', 'hermes', 'acp'], opts)
    } else {
      proc = spawn('cmd.exe', ['/d', '/s', '/c', 'dsh', '--profile', 'acp'], opts)
    }
  } else {
    if (name === 'hermes') {
      proc = spawn('hermes', ['acp'], opts)
    } else {
      proc = spawn('dsh', ['--profile', 'acp'], opts)
    }
  }

  const pending = new Map<number, { resolve: (v: any) => void; reject: (e: Error) => void }>()
  let nextId = 1
  const send = (obj: Record<string, any>): void => {
    try { proc.stdin!.write(JSON.stringify(obj) + '\n') } catch { /* closed */ }
  }
  const request = (method: string, params: any, timeoutMs = 20000): Promise<any> => {
    const id = nextId++
    const { promise, resolve, reject } = Promise.withResolvers<any>()
    pending.set(id, { resolve, reject })
    const timer = setTimeout(() => {
      if (pending.has(id)) { pending.delete(id); reject(new Error(`timeout: ${method}`)) }
    }, timeoutMs)
    timer.unref?.()
    send({ jsonrpc: '2.0', id, method, params })
    return promise
  }
  let buffer = ''
  proc.stdout!.on('data', (chunk: Buffer) => {
    buffer += chunk.toString('utf8')
    let idx: number
    while ((idx = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, idx).trim()
      buffer = buffer.slice(idx + 1)
      if (!line) continue
      try {
        const msg = JSON.parse(line)
        if ('id' in msg && ('result' in msg || 'error' in msg)) {
          const p = pending.get(msg.id)
          if (p) {
            pending.delete(msg.id)
            if (msg.error) p.reject(new Error(String(msg.error.message || 'acp error').slice(0, 200)))
            else p.resolve(msg.result)
          }
        }
      } catch { /* non-JSON */ }
    }
  })

  try {
    await request('initialize', {
      protocolVersion: 1,
      clientCapabilities: {},
      clientInfo: { name: 'rag-knowledge-web', title: 'RAG Knowledge Platform', version: '1.0' },
    })
    const sess = await request('session/new', { cwd: monorepoRoot(), mcpServers: [] })
    const options: Array<Record<string, any>> = Array.isArray(sess?.configOptions) ? sess.configOptions : []
    const summary: AcpConfigOptionSummary = { modelOptions: [], reasoningEfforts: [] }
    for (const o of options) {
      if (o?.id === 'model') {
        summary.currentModel = o.currentValue ? JSON.stringify(o.currentValue) : undefined
        for (const group of o.options || []) {
          for (const m of group.options || []) {
            summary.modelOptions.push({ value: m.value, name: m.name || String(m.value), group: group.group || group.name })
          }
        }
      } else if (o?.id === 'reasoning_effort') {
        summary.currentEffort = o.currentValue
        for (const e of o.options || []) {
          summary.reasoningEfforts.push({ value: e.value, name: e.name || e.value, description: e.description })
        }
      }
    }
    return summary
  } catch (e) {
    console.warn(`[acp] configOptions probe for ${name} failed:`, e instanceof Error ? e.message : e)
    return null
  } finally {
    try { proc.stdin?.end() } catch { /* closed */ }
    setTimeout(() => { try { proc.kill() } catch { /* dead */ } }, 200)
  }
}
