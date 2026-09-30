/**
 * POST /api/claude/chat
 *
 * Claude Agent SDK chat endpoint. Response shape is caller-selected:
 *
 * - stream=true: SSE (text/event-stream).
 *   event: meta                -> { cwd, permissionMode, model }
 *   data: <sdk message>        -> system / assistant / user / result (streaming)
 *   event: permission_request  -> { toolName, input, toolUseId, sessionId }
 *   event: done                -> result message
 *   event: error               -> { error }
 *
 * - stream=false or omitted (DEFAULT): final-only JSON — intermediate frames
 *   are swallowed and ONE object is returned when the engine finishes:
 *   { success, engine, sessionId, model, subtype, answer, duration_ms,
 *     duration_api_ms, num_turns, total_cost_usd, elapsed_ms }
 *   Engine failure / turn timeout -> non-200 JSON { success:false, error, code }.
 *   Permission requests are auto-denied (no interactive surface; rely on the
 *   pre-allowlisted read-only tools, e.g. kbEnhanced's KB_RETRIEVAL_TOOLS).
 *
 * Request body: { prompt, stream?, cwd?, permissionMode?, model?, allowedTools?,
 *   resume?, maxTurns?, attachments?, kbEnhanced?, kbIds?, soulEnhanced?,
 *   soulKbId?, reasoningEffort?, engine?, timeout_ms? }
 *   attachments: [{ name, path, mime, isImage, isText, isPdf, size }]
 *
 * Attachment handling (SDK multimodal integration):
 *   - Images (png/jpg/gif/webp) -> Anthropic image content block (base64)
 *   - PDF                       -> Anthropic document content block (base64)
 *   - Text/code (<100KB)        -> inline in text block (with filename annotation)
 *   - Other binary (>100KB/Office)-> inject path in text block, let Claude read via Read tool
 *
 * Uses AsyncIterable<SDKUserMessage> prompt form to feed multimodal content blocks to the SDK.
 */
import { getEngine, normalizeEngine, getChatMeta, type PermissionMode } from '~/server/engines'
import { getProjectRoot } from '~/server/utils/claude-config'
import { buildKbInstruction } from '~/server/utils/kb-instruction'
import { addPending, denyAllPending, resolvePending } from '~/server/utils/claude-pending'
import { upsertSession, saveMessage, getSessionMessages } from '~/server/utils/chat-db'
import { resolve } from 'path'
import { readFileSync, statSync, existsSync } from 'fs'
import { resolveWithinAnyRoot } from '~/server/utils/safe-paths'
import { getTreeStorageAbsolutePath } from '~/server/utils/runtime-paths'

interface Attachment {
  name: string
  path: string
  mime: string
  isImage: boolean
  isText: boolean
  isPdf: boolean
  size: number
}

interface ChatBody {
  prompt: string
  cwd?: string
  permissionMode?: string
  model?: string
  allowedTools?: string[]
  resume?: string
  maxTurns?: number
  attachments?: Attachment[]
  kbEnhanced?: boolean
  kbIds?: string[]
  soulEnhanced?: boolean
  soulKbId?: string
  reasoningEffort?: 'auto' | 'low' | 'medium' | 'high' | 'xhigh' | 'max'
  engine?: 'claude' | 'omp'
  /** D4 fix: hard wall-clock budget for the whole turn (ms). */
  timeout_ms?: number
  /**
   * Response shape. true (default) = SSE stream as before (web UI).
   * false = final-only JSON: the handler swallows intermediate frames and
   * returns ONE JSON object { success, answer, duration_ms, num_turns, … }
   * when the engine finishes (errors → non-200 JSON). Permission requests
   * are auto-denied in this mode (no interactive approval surface).
   */
  stream?: boolean
}

/** Safe read-only tools (pre-approved in all modes) */
const SAFE_READS = ['Read', 'Glob', 'Grep']
/**
 * D4 fix: KB retrieval toolset. With kbEnhanced on, the injected instruction
 * drives a tool-native fast path; under `default` permission mode the previous
 * SAFE_READS-only allowlist starved the agent of `Skill`, so it wandered with
 * bare reads and never converged (83 events, no done).
 *
 * Speed fix (2026-09-28, measured 215.5s per kb turn): the read-only kb-mcp
 * tools are pre-allowlisted here so the SDK skips the canUseTool callback for
 * them — previously EVERY kb call cost a permission_request SSE round trip
 * (13 per run) and a human approval in the web UI. Only read-only tools are
 * listed; all kb-mcp write tools (kb_doc_create/update/move/delete, reindex,
 * ingest, graph build, project_start/update…) still go through the permission
 * callback. Tool names that don't exist server-side are harmless no-ops.
 */
// KB lane toolsets / strict-MCP config / internal-tool bans live in
// ~/server/utils/kb-lane.ts — shared verbatim with the kb retrieval lanes so
// the chat UI and the AgentWorkShop rag-bridge run the identical lane.
import { KB_MCP_SERVERS, KB_MCP_TOOLS, KB_DISALLOWED_TOOLS, SOUL_READ_TOOLS } from '~/server/utils/kb-lane'

/** Pinned-KB lane = vector fast path: MCP read tools incl. vector search. */
const KB_RETRIEVAL_TOOLS = KB_MCP_TOOLS
/**
 * All-KB retrieval turns = the librarian lane ONLY (逐级检索): vector tools
 * are withheld so the agent MUST navigate catalog → descriptions → doc IDs
 * → kb_laya_judge → kb_doc_read. Measured 2026-09-28: with vector tools
 * present, the model short-circuited to vector search + reads and skipped
 * the spine entirely (session 21bf40ef).
 */
const KB_LIBRARIAN_TOOLS = KB_MCP_TOOLS.filter(t => !t.startsWith('mcp__kb-mcp__kb_search_vector')
  && !t.startsWith('mcp__kb-mcp__kb_search_two_stage')
  && !t.startsWith('mcp__kb-mcp__kb_search_stats'))
/** D4 fix: hard wall-clock budget for a chat turn (graceful error, not a reset). */
const DEFAULT_TURN_TIMEOUT_MS = 600_000
const MAX_TURN_TIMEOUT_MS = 900_000
/**
 * All tools (bypassPermissions mode). Includes `Task` so the main agent can
 * delegate to subagents — required for the subagent sidebar to ever populate.
 * Subagents themselves are loaded from .claude/agents/ via settingSources.
 */
const ALL_TOOLS = [
  'Read', 'Glob', 'Grep', 'Bash', 'Edit', 'Write', 'WebSearch', 'WebFetch', 'Task',
]

/**
 * KB MCP reachability gate. When the persistent MCP (127.0.0.1:8000) is down,
 * the kb toolset silently vanishes and the model's retrieval calls mis-route
 * into harness tools (measured 2026-09-30: ScheduleWakeup ×4 instead of
 * kb_search_vector). kbEnhanced/soulEnhanced turns therefore probe first;
 * on failure they auto-start the server once (same launch command as the
 * watchdog automation), then fail fast with 503 instead of burning LLM turns.
 */
async function ensureKbMcp(): Promise<boolean> {
  const probe = async (): Promise<boolean> => {
    try {
      const r = await fetch('http://127.0.0.1:8000/sse', { signal: AbortSignal.timeout(3000) })
      return r.ok
    } catch { return false }
  }
  if (await probe()) return true
  try {
    const { spawn } = await import('child_process')
    spawn('uv', ['run', '--no-sync', '--directory', 'kb-mcp', 'python', 'server.py', '--http'],
      { cwd: getProjectRoot(), detached: true, stdio: 'ignore' }).unref()
  } catch { /* spawn failure — the polling probes decide the outcome */ }
  const deadline = Date.now() + 30_000
  while (Date.now() < deadline) {
    await new Promise(r => setTimeout(r, 2000))
    if (await probe()) return true
  }
  return false
}

const PERMISSION_TIMEOUT_MS = 5 * 60 * 1000
// KB_MCP_SERVERS / KB_DISALLOWED_TOOLS imported from ~/server/utils/kb-lane.
const TEXT_INLINE_LIMIT = 100 * 1024 // 文本类附件内联上限 100KB
const HISTORY_REPLAY_TURNS = 20 // server-replay 引擎注入的最大历史轮数（防 prompt 膨胀）

/** Anthropic-shaped content → plain text (text blocks only). */
function extractText(content: any): string {
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content
      .filter((b: any) => b?.type === 'text' && typeof b.text === 'string')
      .map((b: any) => b.text)
      .join('\n')
  }
  return ''
}

/**
 * Rebuild the prior transcript from chat-db for engines without native
 * cross-request sessions (oneshot / acp). Only complete user/assistant text
 * turns are used — tool_use/tool_result/stream_event frames are skipped.
 */
function buildHistory(sessionId: string): Array<{ role: 'user' | 'assistant'; text: string }> {
  const out: Array<{ role: 'user' | 'assistant'; text: string }> = []
  try {
    for (const row of getSessionMessages(sessionId)) {
      if (row.sdk_type !== 'user' && row.sdk_type !== 'assistant') continue
      try {
        const msg = JSON.parse(row.content)
        const text = extractText(msg?.message?.content)
        if (text.trim()) {
          out.push({ role: row.sdk_type === 'user' ? 'user' : 'assistant', text })
        }
      } catch { /* malformed row — skip */ }
    }
  } catch { /* DB unavailable — chat still works, continuity is degraded */ }
  return out.slice(-HISTORY_REPLAY_TURNS)
}

/** MIME -> Anthropic media_type mapping (for image/document blocks) */
function toMediaType(mime: string): string {
  const m: Record<string, string> = {
    'image/png': 'image/png',
    'image/jpeg': 'image/jpeg',
    'image/jpg': 'image/jpeg',
    'image/gif': 'image/gif',
    'image/webp': 'image/webp',
    'application/pdf': 'application/pdf',
  }
  return m[mime] || mime
}

/**
 * Build a SOUL persona-enhanced system instruction.
 * When soulEnhanced is true, tells the agent to answer with the selected
 * SOUL persona via soul_ask (soul-rag skill), auto-routing if none given.
 *
 * @param soulKbId - selected SOUL kb_id; empty = auto-route
 */
function buildSoulInstruction(soulKbId: string): string {
  const personaLine = soulKbId
    ? `Use the SOUL persona \`${soulKbId}\` explicitly (do NOT auto-route).`
    : 'Let the SOUL router auto-select the best-matching persona (do NOT guess).'

  return [
    '',
    '## [System: SOUL Persona-Augmented Answer Mode]',
    '',
    'You are answering with a SOUL persona to make the answer persona-consistent and evidence-grounded.',
    'Follow these steps strictly:',
    '',
    '### Step 1: Invoke soul_ask',
    `Invoke \`soul_ask\` (via the \`soul-rag\` skill or directly the kb-mcp soul_ask tool) with the user question. ${personaLine}`,
    '  - Pass task_type/task_goal if inferable from the question',
    '  - If soul_ask returns route_uncertain=true, report the candidates to the user',
    '',
    '### Step 2: Present the persona answer',
    'Return the soul_ask answer verbatim as the main answer.',
    '  - Include its citations (path + score) when present',
    '  - Report pas_score (persona alignment 0-5)',
    '  - If soul_ask reports retrieval failure (no citations), state honestly that the KB lacks evidence',
    '',
    '### Critical Reminders:',
    '- **Persona first, evidence second** -- the answer must sound like the persona AND cite real sources',
    '- Never fabricate citations -- soul_ask only returns real retrieval paths',
    '- If the SOUL system is unavailable, fall back to a normal answer and say so',
    '',
    '---',
    '',
  ].join('\n')
}

/**
 * Convert attachment array to Anthropic content blocks.
 * Returns { blocks, pathNote } — blocks are content blocks to append to user message,
 * pathNote is a hint text telling the user "N file paths referenced for Claude to Read".
 */
function attachmentsToBlocks(atts: Attachment[]): {
  blocks: Record<string, unknown>[]
  pathNote: string
} {
  const blocks: Record<string, unknown>[] = []
  const referencedPaths: string[] = []

  // Allowed attachment roots: the Claude upload dir + tree-file-system.
  // UPLOAD_DIR is resolved lazily here to avoid duplicating the path math in
  // upload.post.ts; it mirrors `storage/claude-uploads` under MONOREPO_ROOT.
  const uploadDir = resolve(getTreeStorageAbsolutePath(), '..', 'claude-uploads')
  const allowedRoots = [uploadDir, getTreeStorageAbsolutePath()]

  for (const att of atts) {
    try {
      // SECURITY (P0): every client-supplied path MUST be contained under an
      // allowed root before we touch the filesystem. Without this a caller can
      // POST attachments:[{path:'C:/Windows/win.ini'}] and exfiltrate any file
      // the server process can read (then inline it into the model prompt or
      // base64-ship it to Anthropic). Only paths handed back by
      // /api/claude/upload (or tree-storage docs) are accepted here.
      const safePath = resolveWithinAnyRoot(att.path, allowedRoots)
      if (!safePath) {
        // Skip out-of-bounds attachments silently — never reveal the rejection
        // shape, just behave as if the file did not exist.
        continue
      }

      const stat = statSync(safePath)
      if (!stat.isFile()) continue

      if (att.isImage) {
        // Image -> image content block (base64)
        const data = readFileSync(safePath).toString('base64')
        blocks.push({
          type: 'image',
          source: {
            type: 'base64',
            media_type: toMediaType(att.mime),
            data,
          },
        })
      } else if (att.isPdf) {
        // PDF -> document content block (base64)
        const data = readFileSync(safePath).toString('base64')
        blocks.push({
          type: 'document',
          source: {
            type: 'base64',
            media_type: 'application/pdf',
            data,
          },
        })
      } else if (att.isText && att.size <= TEXT_INLINE_LIMIT) {
        // Text -> inline in text block (with filename annotation)
        const content = readFileSync(safePath, 'utf-8')
        blocks.push({
          type: 'text',
          text: `\n\n--- 附件: ${att.name} ---\n${content}\n--- /附件: ${att.name} ---\n`,
        })
      } else {
        // Large file / Office / other binary -> inject path, let Claude Read
        referencedPaths.push(safePath)
      }
    } catch {
      // Failure processing one attachment does not affect others
    }
  }

  const pathNote = referencedPaths.length
    ? `\n\n[已上传 ${referencedPaths.length} 个文件，路径如下，请用 Read 工具读取：\n${referencedPaths.map(p => `- ${p}`).join('\n')}\n]`
    : ''

  return { blocks, pathNote }
}

export default defineEventHandler(async (event) => {
  const body = await readBody<ChatBody>(event)
  const { prompt, cwd, permissionMode, model, allowedTools, resume, maxTurns, attachments,
    reasoningEffort, engine: engineParam } = body || {}
  const kbEnhanced: boolean = body?.kbEnhanced === true
  const soulEnhanced: boolean = body?.soulEnhanced === true
  const soulKbId: string = body?.soulKbId || ''
  const kbIds: string[] = Array.isArray(body?.kbIds) ? body.kbIds : []
  /**
   * stream DEFAULTS TO FALSE (final-only JSON): the request blocks until the
   * engine finishes, then returns ONE object. Only an explicit
   * `"stream": true` switches to SSE (the web UI passes it explicitly).
   */
  const streamMode: boolean = body?.stream === true
  const t0 = Date.now()

  if (!prompt || typeof prompt !== 'string') {
    throw createError({ statusCode: 400, statusMessage: 'prompt (string) 必填' })
  }

  // Permission mode is a per-harness value (each harness exposes its REAL
  // modes via /api/harnesses → permissionModes); adapters fall back to the
  // harness's safest default for unknown values.
  const pm: PermissionMode = (permissionMode && String(permissionMode)) || 'default'

  const engineName = normalizeEngine(engineParam)
  if (!engineName) {
    throw createError({
      statusCode: 400,
      statusMessage: `Unknown or chat-unsupported harness '${engineParam}'. `
        + 'Fetch GET /api/harnesses for the selectable list (available ones are not grayed out).',
    })
  }
  const chatMeta = getChatMeta(engineName)
  const workCwd = cwd?.trim() || getProjectRoot()

  /**
   * Speed fix (2026-09-28): kbEnhanced turns are tool-chore loops (search →
   * read → judge → synthesize, ~6-10 calls). The user-level settings env sets
   * CLAUDE_CODE_EFFORT_LEVEL=max, which made every LLM turn in the loop cost
   * 6-22s (215.5s per retrieval). Default kb retrieval to `medium` unless the
   * caller pins an explicit effort; general (non-kb) chats keep the settings
   * default untouched.
   */
  const effectiveEffort: typeof reasoningEffort =
    reasoningEffort && reasoningEffort !== 'auto'
      ? reasoningEffort
      : (kbEnhanced ? 'medium' : undefined)

  const effectiveAllowedTools =
    pm === 'bypassPermissions'
      ? ALL_TOOLS
      : allowedTools && allowedTools.length > 0
        ? allowedTools
        : kbEnhanced
          ? (kbIds.length > 0
              ? KB_RETRIEVAL_TOOLS.filter(t => t !== 'Task')   // pinned = vector fast lane
              : KB_LIBRARIAN_TOOLS)                             // all-KB = librarian lane only
          : soulEnhanced
            ? [...SAFE_READS, ...KB_MCP_TOOLS, ...SOUL_READ_TOOLS]  // soul persona read-path (measured: all soul_* calls auto-denied without this)
            : SAFE_READS

  // Process attachments -> content blocks
  const hasAttachments = Array.isArray(attachments) && attachments.length > 0
  const { blocks: attachmentBlocks, pathNote } = hasAttachments
    ? attachmentsToBlocks(attachments!)
    : { blocks: [], pathNote: '' }

  // KB-enhanced instruction (prepended when toggle is on)
  const kbInstruction = kbEnhanced ? buildKbInstruction(kbIds) : ''

  // SOUL persona-enhanced instruction (prepended when toggle is on)
  const soulInstruction = soulEnhanced ? buildSoulInstruction(soulKbId) : ''

  // Full prompt = KB instruction + SOUL instruction + user input + path hint.
  // The answer-shape budget + lane note sit at the END of the prompt (recency
  // position): the same budget buried in the kb instruction's step 5 was
  // measured as ignored (67s / 4700-char synthesis, 2026-09-28 session
  // 97d3a693), and without an explicit lane note the model burned turns
  // calling disabled vector tools and loading Skill docs (sessions 34c3d8cb
  // / fe0d33f2).
  const kbLaneNote = kbIds.length > 0
    ? '[通道提示：本轮为指定库快速通道——直接用 kb_search_two_stage / kb_search_vector 宽网起步；判定幸存证据已足够作答时立即作答。不要加载任何 Skill 文档，不要委派 subagent，禁止以相同参数重复调用任何工具。若未找到，只陈述检索事实（库名、已执行的检索、命中数），严禁编造或猜测库的内容。]'
    : '[通道提示：本轮为全库逐级检索通道——向量/经验检索工具不可用（调用会被直接拒绝，不要尝试）。固定顺序：kb_list → kb_get_documents(lightweight=true) 描述层拿 doc_id → kb_laya_judge(refs 每批≤6、串行) → kb_doc_read 幸存者 → 作答。效率优先：若 kb_list 的目录描述已表明没有任何库覆盖问题领域，立即如实回答「知识库中无对应内容」并停止，不要逐库扫描文档层——但描述含 random/杂项/通用/真实世界内容等泛化字样的库不算「已表明无关」，必须抽查其文档描述层后再判定（实测 2026-09-30：demo 杂项库里就有 Voyager 1 文档，目录层早退造成漏检）；禁止以相同参数重复调用任何工具；禁止加载任何 Skill 文档。若 kb 工具调用失败或不可用，必须如实回答「KB 工具不可用」——严禁没有任何检索就凭记忆作答。]'
  // allowedTools-only callers that demand mcp__* tools (benchmark chat
  // tracks / external harnesses). Must be computed BEFORE fullPromptText —
  // the tool-readiness protocol below is appended for these sessions only.
  const requestMcpMount = Array.isArray(allowedTools) &&
    allowedTools.some((t) => typeof t === 'string' && t.startsWith('mcp__'))
  const fullPromptText = kbInstruction + soulInstruction + prompt + pathNote
    + (kbEnhanced
      ? '\n\n[回答格式要求：第一句必须是最终结论，不要以「检索完成」等过程汇报开头；默认总长 ≤800 字（要点 + 关键引文 + 出处）；仅当问题明确要求穷尽列举/完整表格/详细教程时才允许长答。]'
      + kbLaneNote
      : '')
    + (requestMcpMount
      ? '\n\n[执行协议：先用 1-2 句话陈述你的检索计划（查什么、用哪个工具、预期命中什么），然后再调用工具执行——不要跳过计划直接报工具状态。若执行时工具列表中没有任何 mcp__kb-mcp__ 开头的工具，不要凭记忆作答也不要长篇解释，立即以字面量 KB_TOOLS_NOT_READY 结束本轮，系统会自动重试。]'
      : '')

  const res = event.node.res

  if (streamMode) {
    setResponseHeaders(event, {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    })

    res.write(
      `event: meta\ndata: ${JSON.stringify({
        engine: engineName,
        cwd: workCwd,
        permissionMode: pm,
        model: model || 'default',
        attachments: hasAttachments ? attachments!.map(a => ({ name: a.name, type: a.isImage ? 'image' : a.isPdf ? 'pdf' : a.isText ? 'text' : 'file', size: a.size })) : [],
      })}\n\n`,
    )
  }

  let sessionId = ''
  let queryClosed = false
  // Declared OUTSIDE the try block on purpose: finally/catch reference them,
  // and try-scoped bindings are not visible there. The old try-scoped consts
  // threw ReferenceError in finally on EVERY request — invisible on the SSE
  // path (response already ended before the throw) but fatal to the
  // stream=false JSON return, which must survive finally to be serialized.
  let turnTimedOut = false
  let turnTimer: ReturnType<typeof setTimeout> | undefined
  let keepalive: ReturnType<typeof setInterval> | undefined

  try {
    // Permission callback — wired only for harnesses with a real interactive
    // approval surface (claude SDK canUseTool / ACP request_permission / mock).
    // One-shot CLIs have no such surface (their permission modes are plain
    // CLI flags) so the callback is simply never invoked there.
    const claudeNoAsk = engineName === 'claude' && (pm === 'bypassPermissions' || pm === 'dontAsk')
    const needsCanUseTool = !!chatMeta?.hitl && !claudeNoAsk
    const onPermissionRequest = needsCanUseTool
      ? async (
          toolName: string,
          input: Record<string, unknown>,
          toolUseId: string,
          sid: string,
          options?: Array<{ optionId: string; name: string; kind: string }>,
        ): Promise<{ behavior: string; message?: string; optionId?: string }> => {
          // Non-stream mode has no approval surface — deny immediately so the
          // turn fails fast instead of hanging for the 5-minute window.
          if (!streamMode) {
            return { behavior: 'deny', message: 'stream=false 无人工审批通道，仅预授权只读工具可用' }
          }
          res.write(
            `event: permission_request\ndata: ${JSON.stringify({
              toolName,
              input,
              toolUseId,
              sessionId: sid || sessionId,
              ...(options && options.length ? { options } : {}),
            })}\n\n`,
          )
          const { promise, resolve } = Promise.withResolvers<{ behavior: string; message?: string; optionId?: string }>()
          // Key the pending entry by the ADAPTER-provided session id when
          // present — the permission callback can fire before the queued
          // system/init message is consumed (ACP agents ask fast), so the
          // outer `sessionId` may still be '' here. The event payload and the
          // POST-back both use `sid`, so the keys must match exactly.
          const permKey = sid || sessionId || '_pre_init'
          addPending(permKey, toolUseId, toolName, input, resolve as any)
          setTimeout(() => {
            resolvePending(permKey, toolUseId, {
              behavior: 'deny',
              message: '审批超时（5 分钟未响应）',
            })
          }, PERMISSION_TIMEOUT_MS)
          return promise
        }
      : undefined

    // Abort signal — triggered on client disconnect
    const abortController = new AbortController()
    event.node.req.on('close', () => {
      queryClosed = true
      denyAllPending(sessionId || '_pre_init', 'Client disconnected')
      abortController.abort()
    })

    // D4 fix: hard wall-clock budget for the whole turn. Previously a hung
    // engine turn held the SSE connection until something upstream reset it,
    // and the client never received a terminal event. Now the abort surfaces
    // as a structured `event: error {code: TURN_TIMEOUT}`.
    const turnTimeoutMs = Math.min(
      Math.max(Math.round(Number(body?.timeout_ms) || DEFAULT_TURN_TIMEOUT_MS), 10_000),
      MAX_TURN_TIMEOUT_MS,
    )
    turnTimedOut = false
    turnTimer = setTimeout(() => {
      turnTimedOut = true
      abortController.abort(new Error('turn-timeout'))
    }, turnTimeoutMs)

    // D4 fix (2/2): SSE keepalive. Silent stretches (long tool executions,
    // slow LLM turns) previously let client/proxy read timeouts kill the
    // stream before any terminal event. SSE comments (`: ping`) are ignored
    // by every standard parser but keep the socket warm. Non-stream mode
    // returns a single JSON body — no socket to keep warm.
    if (streamMode) {
      keepalive = setInterval(() => {
        try {
          if (!queryClosed) res.write(': ping\n\n')
        } catch { /* socket gone; the turn timer still bounds the query */ }
      }, 15_000)
    }

    // ══════ 用户提问持久化（放在 query 前，覆盖多轮 resume 和首轮新会话） ══════
    // NOTE: replay history must be snapshotted BEFORE the current user message
    // is persisted — otherwise the current prompt lands in the replayed
    // transcript too and the engine sees the question twice.
    const replayHistory = chatMeta?.historyMode === 'server-replay' && resume
      ? buildHistory(resume)
      : []
    const attSummaryMT = hasAttachments && attachments!.length
      ? `\n\n📎 Attachments (${attachments!.length}): ${attachments!.map(a => a.name).join(', ')}`
      : ''
    const kbSummaryMT = kbEnhanced
      ? (kbIds.length
        ? `\n\n🔍 KB-enhanced: searching ${kbIds.length} KB(s)`
        : '\n\n🔍 KB-enhanced: searching all KBs')
      : ''
    const userText = prompt + attSummaryMT + kbSummaryMT
    let _userSaved = false
    const saveUserMessage = (sid: string) => {
      if (_userSaved) return
      _userSaved = true
      try {
        saveMessage(sid, 'user', JSON.stringify({
          type: 'user',
          message: { role: 'user', content: [{ type: 'text', text: userText }] },
        }))
      } catch { /* DB failure is non-fatal */ }
    }
    if (resume) saveUserMessage(resume)

    // Resolve engine and build the engine-agnostic query request
    const engine = getEngine(engineName)

    // Multimodal attachment blocks are only used by the Claude engine.
    // OMP receives path hints embedded in fullPromptText instead.
    const isClaude = engineName === 'claude'

    // ══════ KB MCP 连通门禁（挂载失败会演变成模型乱调用内置工具） ══════
    if ((kbEnhanced || soulEnhanced) && isClaude && !(await ensureKbMcp())) {
      setResponseStatus(event, 503)
      return {
        success: false,
        engine: engineName,
        elapsed_ms: Date.now() - t0,
        error: 'kb-mcp unavailable; auto-start attempted and failed (watchdog will retry)',
        code: 'KB_MCP_DOWN',
      }
    }
    // allowedTools-only sessions: warm the endpoint (idempotent probe) so the
    // session's own SSE connect finds a hot acceptor — these short-prompt
    // sessions lose the async-mount race far more often than kbEnhanced ones.
    if (requestMcpMount && isClaude) {
      try {
        await ensureKbMcp()
      } catch {
        /* probe failure tolerated — the lane's own retry handles hard down */
      }
    }

    // ══════ 引擎查询（kbEnhanced 非流式带挂载闪失败自动重试） ══════
    // MCP mount 说明：requestMcpMount（allowedTools 里点名 mcp__* 工具的调用方
    // 也挂 kb-mcp）已在 fullPromptText 之前计算——挂载以工具需求为准，而不是
    // kbEnhanced 指令开关（2026-09-30 回归：allowedTools-only 请求什么都不挂，
    // 会话凭参数记忆/网页绕路作答）。
    let finalResult: any = null
    let sawKbTool = false
    // 异步 MCP 注册与模型首个工具轮存在竞态（SDK init 时 kb-mcp 恒报 pending，
    // 工具列表晚于首轮就位时模型会零工具作答，实测 ~50% 概率）。kbEnhanced 车道
    // 凭超长系统指令天然延后首个工具轮而几乎不输竞态；allowedTools-only 调用方
    // （benchmark 轨/外部 harness）prompt 短，必须靠「就绪协议 + 探活重试」补：
    // 重试前 ensureKbMcp() 等服务端恢复，三次掷硬币后失败率 ~50%→~12%。
    const maxAttempts = (kbEnhanced || requestMcpMount) && !streamMode
      ? (requestMcpMount ? 3 : 2)
      : 1
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      sawKbTool = false
      const q = engine.query({
        prompt,
        cwd: workCwd,
        permissionMode: pm,
        model: model || undefined,
        allowedTools: effectiveAllowedTools,
        resume: resume || undefined,
        maxTurns: maxTurns || (kbEnhanced ? 18 : 50),
        reasoningEffort: effectiveEffort,
        fullPromptText,
        // Engines without native cross-request sessions get the prior
        // transcript replayed into the prompt (multi-turn continuity).
        ...(replayHistory.length ? { history: replayHistory } : {}),
        ...(isClaude && hasAttachments && attachmentBlocks.length > 0
          ? { attachmentBlocks: attachmentBlocks as any }
          : {}),
        ...((kbEnhanced || soulEnhanced) && isClaude
          ? {
              mcpServers: KB_MCP_SERVERS,
              strictMcpConfig: true,
              // The ban list covers every harness-internal tool that ever drew
              // an opening-turn detour — see kb-lane.ts for the measured log.
              disallowedTools: KB_DISALLOWED_TOOLS,
            }
          : {}),
        ...(requestMcpMount && isClaude && !(kbEnhanced || soulEnhanced)
          ? {
              // STDIO mount for allowedTools-only callers (benchmark tracks /
              // external harnesses). SSE connects asynchronously AFTER init —
              // the tool list lands mid-session and short-prompt sessions lose
              // that race ~50% (2026-09-30, three Quick10 rounds of evidence).
              // A stdio child is spawned and handshakes BEFORE init completes,
              // so tools are present at turn 1 — the race is gone by
              // construction; costs ~5s/session server cold-start instead.
              mcpServers: {
                // NOTE: direct venv python (kb-mcp/.venv) was tried and is
                // BROKEN here — the SDK ignores the stdio config's cwd, so
                // `python server.py` resolves the wrong script path (measured
                // 0/3, 2026-09-30). `uv run --directory` carries its own cwd
                // semantics and is the proven form (6/6 direct, 16/20 matrix).
                'kb-mcp': {
                  type: 'stdio' as const,
                  command: 'uv',
                  args: ['run', '--no-sync', '--directory',
                         `${getProjectRoot().replace(/\\/g, '/')}/kb-mcp`,
                         'python', 'server.py'],
                },
              },
              strictMcpConfig: true,
              // NO disallowedTools here: banning {ToolSearch, Task} suppresses
              // MCP tool registration outright (measured 2026-09-30). These
              // callers are whitelisted via allowedTools already, and
              // ENABLE_TOOL_SEARCH=false in the engine env kills the
              // ToolSearch detour at the root.
            }
          : {}),
        onPermissionRequest,
        signal: abortController.signal,
      })

      for await (const message of q) {
        if (message.type === 'system' && message.subtype === 'init') {
          sessionId = (message as any).session_id || ''
          upsertSession(sessionId, {
            title: resume ? undefined : prompt.slice(0, 100),
            cwd: workCwd,
            permissionMode: pm,
            model: (message as any).model || model || undefined,
            engine: engineName,
          })
          // ⭐ 新会话首轮：从 init 拿到的 sessionId 存入用户提问
          saveUserMessage(sessionId)
        }
        if (sessionId) {
          try {
            saveMessage(sessionId, message.type, JSON.stringify(message))
          } catch {
            /* DB write failure does not block the chat stream */
          }
        }
        if ((kbEnhanced || requestMcpMount) && message.type === 'assistant') {
          const content = (message as any).message?.content
          if (Array.isArray(content) && content.some((b: any) =>
            b?.type === 'tool_use' && String(b?.name || '').startsWith('mcp__kb-mcp__'))) {
            sawKbTool = true
          }
        }
        if (message.type === 'result') {
          if (!streamMode) {
            // stream=false: hold the result, respond with ONE JSON after cleanup.
            finalResult = message
            queryClosed = true
            denyAllPending(sessionId || '_pre_init', 'Query ended')
            abortController.abort(new Error('result-received'))
            break
          }
          // result message only sends event: done once, avoiding duplicate processing by frontend handler
          res.write(`event: done\ndata: ${JSON.stringify(message)}\n\n`)
          queryClosed = true
          denyAllPending(sessionId || '_pre_init', 'Query ended')
          abortController.abort(new Error('result-received'))
          res.end()
          break
        } else if (streamMode) {
          res.write(`data: ${JSON.stringify(message)}\n\n`)
        }
      }
      // Mount-flake auto-heal: a kb turn whose engine produced an answer
      // without touching a single kb-mcp tool is a dead session, not a
      // retrieval result — re-run. Non-stream only (the SSE stream is
      // already on the wire in stream mode). Applies to BOTH kbEnhanced
      // lanes and allowedTools-only callers (benchmark tracks / external
      // harnesses): their sessions demand mcp__* tools, and a zero-tool
      // answer is always the async-SSE-mount race (SDK init reports kb-mcp
      // "pending"; whether the tool list lands before the model's first
      // tool-seeking turn is a coin flip on short prompts).
      // Before re-rolling, probe kb-mcp health so we ride out server-side
      // accept hiccups (ensureKbMcp is idempotent and waits for recovery).
      if (!streamMode && finalResult && (kbEnhanced || requestMcpMount) &&
          !sawKbTool && attempt < maxAttempts - 1) {
        finalResult = null
        try {
          await ensureKbMcp()
        } catch {
          /* probe failure is not fatal — the retry may still reconnect */
        }
        continue
      }
      break
    }

    if (!streamMode) {
      if (finalResult) {
        const fr: any = finalResult
        const answer = typeof fr.result === 'string' && fr.result
          ? fr.result
          : extractText(fr.message?.content)
        let success = fr.subtype === 'success'
        let guardCode: string | null = null
        // Honest-failure guard: an allowedTools-only session that demanded
        // mcp__* tools but ended with ZERO kb tool calls never retrieved —
        // its answer would be parametric memory dressed as retrieval.
        // Demote to success:false so callers (benchmark runner, external
        // harnesses) can fail the unit instead of scoring a fabrication.
        if (requestMcpMount && !sawKbTool && success) {
          success = false
          guardCode = answer.includes('KB_TOOLS_NOT_READY')
            ? 'KB_TOOLS_NOT_READY'
            : 'KB_NO_RETRIEVAL'
        }
        return {
          success,
          ...(guardCode ? { code: guardCode } : {}),
          engine: engineName,
          sessionId,
          model: fr.model || model || 'default',
          subtype: fr.subtype || null,
          answer,
          duration_ms: fr.duration_ms ?? null,
          duration_api_ms: fr.duration_api_ms ?? null,
          num_turns: fr.num_turns ?? null,
          total_cost_usd: fr.total_cost_usd ?? null,
          elapsed_ms: Date.now() - t0,
        }
      }
      setResponseStatus(event, turnTimedOut ? 504 : 502)
      return {
        success: false,
        engine: engineName,
        sessionId,
        elapsed_ms: Date.now() - t0,
        error: turnTimedOut
          ? `chat turn exceeded ${Math.round(turnTimeoutMs / 1000)}s wall-clock budget`
          : 'engine ended without a result message',
        code: turnTimedOut ? 'TURN_TIMEOUT' : 'NO_RESULT',
      }
    }
  } catch (e: any) {
    const errMsg = e?.message || String(e)
    if (streamMode) {
      if (!queryClosed && turnTimedOut) {
        res.write(
          `event: error\ndata: ${JSON.stringify({
            error: `chat turn exceeded ${Math.round(turnTimeoutMs / 1000)}s wall-clock budget`,
            code: 'TURN_TIMEOUT',
          })}\n\n`,
        )
      } else if (!queryClosed) {
        res.write(
          `event: error\ndata: ${JSON.stringify({ error: errMsg, code: 'SDK_QUERY_FAILED' })}\n\n`,
        )
      }
    } else if (!queryClosed) {
      setResponseStatus(event, turnTimedOut ? 504 : 500)
      return {
        success: false,
        engine: engineName,
        sessionId,
        elapsed_ms: Date.now() - t0,
        error: turnTimedOut
          ? `chat turn exceeded ${Math.round(turnTimeoutMs / 1000)}s wall-clock budget`
          : errMsg,
        code: turnTimedOut ? 'TURN_TIMEOUT' : 'SDK_QUERY_FAILED',
      }
    }
  } finally {
    clearTimeout(turnTimer)
    if (keepalive) clearInterval(keepalive)
    if (!queryClosed) {
      denyAllPending(sessionId || '_pre_init', 'Query ended')
    }
    if (streamMode) {
      res.end()
    }
  }
})
