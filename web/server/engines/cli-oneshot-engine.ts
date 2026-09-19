/**
 * Generic one-shot CLI ChatEngine adapter — covers every headless CLI harness
 * without an interactive protocol: codex / gemini / copilot / cursor /
 * opencode / crush / goose / qwen / pi.
 *
 * Per turn = one headless process (the platform's one-shot job model, same
 * specs as backend/app/services/harness_specs.py). Multi-turn chat continuity
 * comes from server-side history replay (QueryRequest.history) embedded in the
 * prompt block.
 *
 * Permissions: headless one-shot mode has NO interactive approval surface —
 * that is the harnesses' real semantics, not a limitation we hide. Each mode
 * maps to the harness's documented CLI flags/env (see harness-catalog.ts);
 * unknown modes fall back to the harness's safest default.
 *
 * Spawn discipline: first argv element is always a literal (engine name or
 * cmd.exe); every dynamic argument is validated (no quotes/CR/LF/NUL) and
 * positional prompts that start with '-' are space-prefixed so they can never
 * be parsed as option flags.
 */
import { spawn, type ChildProcess } from 'child_process'
import { mkdtempSync, writeFileSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { AsyncQueue } from './async-queue'
import type { ChatEngine, QueryRequest, StandardMessage } from './types'
import { resolveCommandLocal } from '~/server/utils/harness-catalog'

// ── arg validation (parity with backend validate_spawn_arg) ────────────

function validateArg(a: string): string {
  if (/["\r\n\x00]/.test(a)) {
    throw new Error(
      `prompt/arg contains characters the cmd.exe shim chain rejects (quotes/newlines). `
      + `Use a stdin-delivery engine (claude/codex/qwen) for this message.`)
  }
  return a
}

/** Positional values must never be parseable as option flags. */
function positionalValue(v: string): string {
  return v.startsWith('-') ? ` ${v}` : v
}

// ── output parsers (ports of backend harness_specs parsers) ───────────

function* iterJsonLines(content: string): Generator<any> {
  for (const line of content.split(/\r?\n/)) {
    const t = line.trim()
    if (!t.startsWith('{') && !t.startsWith('[')) continue
    try { yield JSON.parse(t) } catch { continue }
  }
}

function parseCodex(content: string): string {
  let text = ''
  for (const ev of iterJsonLines(content)) {
    if (ev?.type === 'item.completed') {
      const item = ev.item || {}
      const itype = item.type || item.item_type
      if (itype === 'agent_message' && typeof item.text === 'string' && item.text.trim()) {
        text = item.text
      }
    }
  }
  return text.trim()
}

/** Balanced scan of every top-level JSON object/array in the text. */
function* iterBalancedJson(content: string): Generator<any> {
  let depth = 0
  let start = -1
  let inStr = false
  let escape = false
  for (let i = 0; i < content.length; i++) {
    const ch = content[i]
    if (inStr) {
      if (escape) escape = false
      else if (ch === '\\') escape = true
      else if (ch === '"') inStr = false
      continue
    }
    if (ch === '"') { inStr = true; continue }
    if (ch === '{' || ch === '[') {
      if (depth === 0) start = i
      depth++
    } else if (ch === '}' || ch === ']') {
      depth--
      if (depth === 0 && start >= 0) {
        try { yield JSON.parse(content.slice(start, i + 1)) } catch { /* skip */ }
        start = -1
      }
    }
  }
}

function parseGemini(content: string): string {
  try {
    const obj = JSON.parse(content.trim())
    if (obj && typeof obj === 'object') {
      if (typeof obj.response === 'string' && obj.response.trim()) return obj.response.trim()
      if (obj.error) {
        const detail = typeof obj.error === 'object' ? (obj.error.message || JSON.stringify(obj.error)) : String(obj.error)
        return `[gemini error] ${detail}`
      }
    }
  } catch { /* multi-object / stream-json fallback below */ }
  // gemini emits pretty-printed multi-line JSON (one object per frame);
  // line-scanning only ever sees "{", so balance-scan whole objects instead.
  let text = ''
  let err = ''
  for (const ev of iterBalancedJson(content)) {
    if (ev?.error) {
      err = typeof ev.error === 'object' ? (ev.error.message || JSON.stringify(ev.error)) : String(ev.error)
    } else if (ev?.type === 'result' && typeof ev.response === 'string') {
      text = ev.response
    } else if (ev?.type === 'message' && typeof ev.content === 'string' && ev.content.trim()) {
      text = ev.content
    } else if (typeof ev?.response === 'string' && ev.response.trim() && !text) {
      text = ev.response
    }
  }
  if (!text && err) text = `[gemini error] ${err}`
  return text.trim()
}

function parseCopilot(content: string): string {
  let text = ''
  let deltas = ''
  for (const ev of iterJsonLines(content)) {
    const etype = String(ev?.type || '')
    const data = (ev?.data && typeof ev.data === 'object') ? ev.data : {}
    if (etype === 'assistant.message') {
      const c = typeof data.content === 'string' ? data.content : ''
      if (c.trim() && (data.phase === 'final_answer' || !text)) text = c
    } else if (etype === 'assistant.message_delta' && typeof data.deltaContent === 'string') {
      deltas += data.deltaContent
    }
  }
  if (!text && deltas) text = deltas
  if (text.trim()) return text.trim()
  // Plain-text fallback: keep only non-JSON lines
  return content.split(/\r?\n/)
    .filter(l => l.trim() && !l.trim().startsWith('{') && !l.trim().startsWith('['))
    .join('\n').trim()
}

function parseCursor(content: string): string {
  // Path 1: clean single-line JSON frames (existing line-scan behavior).
  const objs = [...iterJsonLines(content)].filter(o => o && typeof o === 'object' && !Array.isArray(o))
  for (const obj of objs.reverse()) {
    if (obj.type === 'error') continue
    const r = obj.result
    if (typeof r === 'string' && r.trim()) return r.trim()
    if (typeof obj.text === 'string' && obj.text.trim()) return obj.text.trim()
  }
  // Path 2: cursor-agent stdout mixes trace lines ("cursor-retrieval:
  // tracing to …") with pretty-printed / multi-line JSON — line scanning
  // matches neither, so balance-scan whole objects and take the LAST one
  // carrying a non-empty string `result`.
  for (const obj of [...iterBalancedJson(content)].reverse()) {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) continue
    if (typeof obj.result === 'string' && obj.result.trim()) return obj.result.trim()
  }
  return content.trim()
}

/** Assistant text carried by one goose stream-json event ('' if none). */
function gooseEventText(ev: any): string {
  const etype = String(ev?.type || ev?.event || '')
  if (etype !== 'message' && etype !== 'notification') return ''
  const msg = (ev.message && typeof ev.message === 'object') ? ev.message : null
  const role = msg?.role || ev.role
  if (role !== 'assistant') return ''
  const blocks = msg ? msg.content : ev.content
  if (typeof blocks === 'string' && blocks.trim()) return blocks
  if (Array.isArray(blocks)) {
    return blocks.filter(b => b?.type === 'text').map(b => b.text).join('\n')
  }
  return ''
}

function parseGoose(content: string): string {
  let text = ''
  let sawJson = false
  for (const ev of iterJsonLines(content)) {
    sawJson = true
    const t = gooseEventText(ev)
    if (t.trim()) text = t
  }
  if (!text) {
    // goose stream-json frames may be pretty-printed / multi-line, which
    // line-scanning never matches — balance-scan whole objects as fallback.
    for (const ev of iterBalancedJson(content)) {
      const t = gooseEventText(ev)
      if (t.trim()) text = t
    }
  }
  if (!text && !sawJson) return content.trim()
  return text.trim()
}

function parseQwen(content: string): string {
  const stripped = content.trim()
  if (stripped.startsWith('[') || stripped.startsWith('{')) {
    try {
      const obj = JSON.parse(stripped)
      if (Array.isArray(obj)) {
        for (const ev of [...obj].reverse()) {
          if (ev && typeof ev === 'object') {
            const r = ev.result || ev.response
            if (typeof r === 'string' && r.trim()) return r.trim()
          }
        }
        return ''
      }
      if (obj && typeof obj === 'object') {
        const r = obj.result || obj.response
        if (typeof r === 'string' && r.trim()) return r.trim()
      }
    } catch { /* fall through */ }
  }
  return content.trim()
}

function parsePi(content: string): string {
  let text = ''
  let chunks = ''
  for (const ev of iterJsonLines(content)) {
    const etype = String(ev?.type || '')
    if (etype === 'message_end' && ev.message?.role === 'assistant') {
      const blocks = ev.message.content
      if (Array.isArray(blocks)) {
        const t = blocks.filter(b => b?.type === 'text').map(b => b.text).join('\n')
        if (t.trim()) text = t
      } else if (typeof blocks === 'string' && blocks.trim()) text = blocks
    } else if (etype === 'message_update') {
      const sub = ev.assistantMessageEvent || {}
      const delta = typeof sub.delta === 'string' ? sub.delta : (typeof ev.delta === 'string' ? ev.delta : '')
      if (delta) chunks += delta
    }
  }
  return (text || chunks).trim()
}

// ── per-engine launch specs ────────────────────────────────────────────

interface LaunchPlan {
  /** Literal argv head — program + static flags (prompt appended by delivery). */
  argv: string[]
  stdin: boolean
  env?: Record<string, string>
  /** Temp dir to remove after the turn (pi argfile delivery). */
  cleanupDir?: string
}

function modeOr(mode: string, supported: Record<string, string>, fallbackKey = 'default'): string {
  return supported[mode] ?? supported[fallbackKey]
}

function buildLaunch(engine: string, req: QueryRequest, prompt: string): LaunchPlan {
  const model = (req.model || '').trim()
  const mode = req.permissionMode || 'default'
  const argvTail: string[] = []

  switch (engine) {
    case 'codex': {
      // exec mode has NO interactive approver ("approval policy is never"),
      // and MCP tool calls require approval under --sandbox — the default
      // chat mode therefore uses --approve-for-me (codex's own automatic
      // review on top of its built-in workspace-write sandbox; the two flags
      // are mutually exclusive). bypass removes sandbox + approvals entirely.
      // NOTE: '-' (stdin marker) must stay LAST — it is a positional.
      argvTail.push('exec', '--json', '--skip-git-repo-check')
      if (mode === 'bypassPermissions') {
        argvTail.push('--dangerously-bypass-approvals-and-sandbox')
      } else if (mode === 'default' || mode === 'acceptEdits') {
        argvTail.push('--approve-for-me')
      } else {
        argvTail.push('--sandbox', 'read-only')
      }
      // 思考强度：codex 官方配置键 model_reasoning_effort（minimal/low/medium/high）
      if (req.reasoningEffort) {
        argvTail.push('-c', `model_reasoning_effort="${req.reasoningEffort}"`)
      }
      if (model) argvTail.push('-m', model)
      argvTail.push('-')
      return { argv: argvTail, stdin: true }
    }
    case 'gemini': {
      argvTail.push('--output-format', 'json')
      if (mode === 'acceptEdits') argvTail.unshift('--approval-mode', 'auto_edit')
      else if (mode === 'bypassPermissions') argvTail.unshift('--approval-mode', 'yolo')
      if (model) argvTail.unshift('-m', model)
      argvTail.push('-p', positionalValue(validateArg(prompt)))
      return { argv: argvTail, stdin: false }
    }
    case 'copilot': {
      if (mode === 'bypassPermissions') argvTail.push('--allow-all-tools')
      argvTail.push('--output-format', 'json', '--no-ask-user')
      if (model) argvTail.push('--model', model)
      // 思考强度：copilot --effort（none/minimal/low/medium/high/xhigh/max）
      if (req.reasoningEffort) argvTail.push('--effort', req.reasoningEffort)
      argvTail.push('-p', positionalValue(validateArg(prompt)))
      return { argv: argvTail, stdin: false }
    }
    case 'cursor': {
      argvTail.push('-p', '--output-format', 'json')
      if (model) argvTail.push('--model', model)
      if (mode === 'bypassPermissions') argvTail.push('--force')
      argvTail.push(positionalValue(validateArg(prompt)))
      return { argv: argvTail, stdin: false }
    }
    case 'opencode': {
      argvTail.push('run')
      if (model) argvTail.push('-m', model)
      argvTail.push(positionalValue(validateArg(prompt)))
      return { argv: argvTail, stdin: false }
    }
    case 'crush': {
      argvTail.push('run')
      if (model) argvTail.push('--model', model)
      argvTail.push(positionalValue(validateArg(prompt)))
      return { argv: argvTail, stdin: false }
    }
    case 'goose': {
      argvTail.push('run', '--output-format', 'stream-json', '-t', positionalValue(validateArg(prompt)))
      return {
        argv: argvTail,
        stdin: false,
        env: { GOOSE_MODE: 'auto', GOOSE_DISABLE_SESSION_NAMING: 'true', ...(model ? { GOOSE_MODEL: model } : {}) },
      }
    }
    case 'qwen': {
      if (model) argvTail.push('-m', model)
      return { argv: argvTail, stdin: true }
    }
    case 'pi': {
      argvTail.push('-p', '--mode', 'json')
      // pi 官方旗标：--model 支持 provider/id 形态；--thinking off..xhigh
      if (req.reasoningEffort) argvTail.push('--thinking', req.reasoningEffort)
      if (model) argvTail.push('--model', model)
      // argfile delivery (backend parity): prompt via @tempfile
      const dir = mkdtempSync(join(tmpdir(), 'pi-prompt-'))
      const file = join(dir, 'prompt.txt')
      writeFileSync(file, prompt, 'utf8')
      argvTail.push(`@${validateArg(file)}`)
      return { argv: argvTail, stdin: false, cleanupDir: dir }
    }
    default:
      throw new Error(`No one-shot launch spec for harness '${engine}'`)
  }
}

const PARSERS: Record<string, (content: string) => string> = {
  codex: parseCodex,
  gemini: parseGemini,
  copilot: parseCopilot,
  cursor: parseCursor,
  goose: parseGoose,
  qwen: parseQwen,
  pi: parsePi,
  opencode: (c: string) => c.trim(),
  crush: (c: string) => c.trim(),
}

const TIMEOUT_MS = 300_000

// ── the adapter ────────────────────────────────────────────────────────

export class CliOneShotEngine implements ChatEngine {
  constructor(readonly name: string) {}

  async *query(req: QueryRequest): AsyncIterable<StandardMessage> {
    const queue = new AsyncQueue<StandardMessage>()
    const state = { startTime: Date.now(), finished: false }
    const finish = (err?: string): void => {
      if (state.finished) return
      state.finished = true
      if (err) {
        queue.push({
          type: 'result', result: '', is_error: true, total_cost_usd: 0,
          duration_ms: Date.now() - state.startTime, num_turns: 0,
          usage: { input_tokens: 0, output_tokens: 0 },
          stop_reason: 'error', terminal_reason: err,
          session_id: '',
        })
      }
      queue.close()
    }

    // Advisory availability note only — the actual spawn resolves through the
    // OS PATH (cmd.exe PATHEXT on win32), which is broader than the local fs
    // scan; a hard pre-check here produced false negatives (e.g. cursor-agent
    // installed outside the scanned dirs while the backend catalog says
    // available). Real spawn failures surface via the 'error'/exit handlers.
    if (!resolveCommandLocal(this.name)) {
      console.warn(`[chat] local scan missed '${this.name}' binary — relying on OS PATH resolution`)
    }

    // History replay (these CLIs have no cross-request session API we drive).
    const hist = req.history || []
    const transcript = hist
      .map(m => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.text}`)
      .join('\n\n')
    const promptText = transcript
      ? `<conversation_history>\n${transcript}\n</conversation_history>\n\nUser: ${req.fullPromptText}`
      : req.fullPromptText

    // Prompt length guard for cmd-shim arg delivery (backend parity).
    const meta = { gemini: 7500, copilot: 7500, opencode: 7500, cursor: 30000, crush: 30000, goose: 30000 }[this.name]
    if (meta && promptText.length > meta) {
      finish(`Prompt too long for '${this.name}' arg delivery: ${promptText.length} chars (limit ${meta}). Use a stdin/@file engine (claude/codex/omp/pi).`)
      for await (const m of queue) yield m
      return
    }

    let plan: LaunchPlan
    try {
      plan = buildLaunch(this.name, req, promptText)
    } catch (e) {
      finish(e instanceof Error ? e.message : String(e))
      for await (const m of queue) yield m
      return
    }

    queue.push({
      type: 'system', subtype: 'init',
      session_id: `oneshot-${this.name}-${state.startTime}`,
      model: req.model || 'default',
      cwd: req.cwd, permissionMode: req.permissionMode,
      tools: [], mcp_servers: [], slash_commands: [],
    })

    // ── literal-program spawn (every first argv element is a literal) ──
    const opts = {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
      cwd: req.cwd,
      env: { ...process.env, ...(plan.env || {}) },
    }
    let proc: ChildProcess
    if (process.platform === 'win32') {
      switch (this.name) {
        case 'codex': proc = spawn('cmd.exe', ['/d', '/s', '/c', 'codex', ...plan.argv], opts); break
        case 'gemini': proc = spawn('cmd.exe', ['/d', '/s', '/c', 'gemini', ...plan.argv], opts); break
        case 'copilot': proc = spawn('cmd.exe', ['/d', '/s', '/c', 'copilot', ...plan.argv], opts); break
        case 'cursor': proc = spawn('cmd.exe', ['/d', '/s', '/c', 'cursor-agent', ...plan.argv], opts); break
        case 'opencode': proc = spawn('cmd.exe', ['/d', '/s', '/c', 'opencode', ...plan.argv], opts); break
        case 'crush': proc = spawn('cmd.exe', ['/d', '/s', '/c', 'crush', ...plan.argv], opts); break
        case 'goose': proc = spawn('cmd.exe', ['/d', '/s', '/c', 'goose', ...plan.argv], opts); break
        case 'qwen': proc = spawn('cmd.exe', ['/d', '/s', '/c', 'qwen', ...plan.argv], opts); break
        case 'pi': proc = spawn('cmd.exe', ['/d', '/s', '/c', 'pi', ...plan.argv], opts); break
        default:
          finish(`No spawn spec for '${this.name}'`)
          for await (const m of queue) yield m
          return
      }
    } else {
      switch (this.name) {
        case 'codex': proc = spawn('codex', plan.argv, opts); break
        case 'gemini': proc = spawn('gemini', plan.argv, opts); break
        case 'copilot': proc = spawn('copilot', plan.argv, opts); break
        case 'cursor': proc = spawn('cursor-agent', plan.argv, opts); break
        case 'opencode': proc = spawn('opencode', plan.argv, opts); break
        case 'crush': proc = spawn('crush', plan.argv, opts); break
        case 'goose': proc = spawn('goose', plan.argv, opts); break
        case 'qwen': proc = spawn('qwen', plan.argv, opts); break
        case 'pi': proc = spawn('pi', plan.argv, opts); break
        default:
          finish(`No spawn spec for '${this.name}'`)
          for await (const m of queue) yield m
          return
      }
    }

    let stdout = ''
    let stderrTail = ''
    proc.stdout!.on('data', (c: Buffer) => { stdout += c.toString('utf8') })
    proc.stderr!.on('data', (c: Buffer) => {
      stderrTail = (stderrTail + c.toString('utf8')).slice(-2000)
    })
    const timer = setTimeout(() => {
      try { proc.kill() } catch { /* dead */ }
      finish(`timeout after ${TIMEOUT_MS / 1000}s`)
    }, TIMEOUT_MS)
    timer.unref?.()

    proc.on('error', (err) => {
      clearTimeout(timer)
      finish(`spawn failed: ${err.message}`)
      // 'close' may never fire after a spawn error — unblock the waiter.
      exitSettled.resolve(null)
    })

    if (req.signal) {
      req.signal.addEventListener('abort', () => {
        try { proc.kill() } catch { /* dead */ }
        finish('aborted by client disconnect')
      }, { once: true })
    }

    const exitSettled = Promise.withResolvers<number | null>()
    const exitCode = await new Promise<number | null>((resolve) => {
      void exitSettled.promise.then(resolve)
      proc.on('close', (code) => resolve(code))
      if (plan.stdin && proc.stdin) {
        proc.stdin.write(promptText)
        proc.stdin.end()
      } else {
        try { proc.stdin?.end() } catch { /* closed */ }
      }
    })
    clearTimeout(timer)
    if (plan.cleanupDir) {
      try { rmSync(plan.cleanupDir, { recursive: true, force: true }) } catch { /* best effort */ }
    }

    const parser = PARSERS[this.name]
    let text = parser ? parser(stdout) : stdout.trim()
    // Some engines (gemini on auth/config errors) emit their JSON to stderr
    // with an empty stdout — parse that too before declaring "no output".
    if (!text && stderrTail.trim() && parser) {
      text = parser(stderrTail)
    }
    const looksLikeError = /^(error|fatal|api error|failed to authenticate|unauthorized|not configured)/i.test(text)
      || /^\[(gemini|goose) error\]/.test(text)
      || /no provider configured|api key (is )?not set|insufficient_quota|authentication failed|set an Auth method|Auth method.*before running/i.test(text)
    if (!text || looksLikeError) {
      const detail = (stderrTail || stdout).slice(-800)
      queue.push({
        type: 'result', result: text, is_error: true, total_cost_usd: 0,
        duration_ms: Date.now() - state.startTime, num_turns: 0,
        usage: { input_tokens: 0, output_tokens: 0 },
        stop_reason: 'error',
        terminal_reason: looksLikeError
          ? `engine error (exit=${exitCode}): ${text || detail}`
          : `no output (exit=${exitCode}). ${detail}`,
        session_id: '',
      })
    } else {
      queue.push({
        type: 'assistant',
        message: { role: 'assistant', content: [{ type: 'text', text }] },
      })
      queue.push({
        type: 'result', result: text, is_error: false, total_cost_usd: 0,
        duration_ms: Date.now() - state.startTime, num_turns: 1,
        usage: { input_tokens: 0, output_tokens: 0 },
        stop_reason: 'stop', terminal_reason: 'stop',
        session_id: '',
      })
    }
    // Close LAST — push() after close() is silently dropped by AsyncQueue.
    finish()

    for await (const msg of queue) {
      yield msg
    }
  }
}
