/**
 * POST /api/claude/chat
 *
 * Claude Agent SDK streaming chat endpoint (SSE).
 *
 * Request body: { prompt, cwd?, permissionMode?, model?, allowedTools?, resume?, maxTurns?, attachments? }
 *   attachments: [{ name, path, mime, isImage, isText, isPdf, size }]
 *
 * Response (text/event-stream):
 *   event: meta                -> { cwd, permissionMode, model }
 *   data: <sdk message>        -> system / assistant / user / result (streaming)
 *   event: permission_request  -> { toolName, input, toolUseId, sessionId }
 *   event: done                -> result message
 *   event: error               -> { error }
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
import { readFileSync, statSync } from 'fs'
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
}

/** Safe read-only tools (pre-approved in all modes) */
const SAFE_READS = ['Read', 'Glob', 'Grep']
/**
 * D4 fix: KB retrieval toolset. With kbEnhanced on, the injected instruction
 * drives the /knowledgebase-search skill; under `default` permission mode the
 * previous SAFE_READS-only allowlist starved the agent of `Skill`, so it
 * wandered with bare reads and never converged (83 events, no done).
 * Skill is read-only usage; MCP retrieval tools stay governed by the
 * permission callback.
 */
const KB_RETRIEVAL_TOOLS = ['Read', 'Glob', 'Grep', 'Skill']
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

const PERMISSION_TIMEOUT_MS = 5 * 60 * 1000
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
  const kbIds: string[] = Array.isArray(body?.kbIds) ? body.kbIds : []

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

  const effectiveAllowedTools =
    pm === 'bypassPermissions'
      ? ALL_TOOLS
      : allowedTools && allowedTools.length > 0
        ? allowedTools
        : kbEnhanced
          ? KB_RETRIEVAL_TOOLS
          : SAFE_READS

  // Process attachments -> content blocks
  const hasAttachments = Array.isArray(attachments) && attachments.length > 0
  const { blocks: attachmentBlocks, pathNote } = hasAttachments
    ? attachmentsToBlocks(attachments!)
    : { blocks: [], pathNote: '' }

  // KB-enhanced instruction (prepended when toggle is on)
  const kbInstruction = kbEnhanced ? buildKbInstruction(kbIds) : ''

  // SOUL persona-enhanced instruction (prepended when toggle is on)
  const soulEnhanced: boolean = body?.soulEnhanced === true
  const soulKbId: string = body?.soulKbId || ''
  const soulInstruction = soulEnhanced ? buildSoulInstruction(soulKbId) : ''

  // Full prompt = KB instruction + SOUL instruction + user input + path hint
  const fullPromptText = kbInstruction + soulInstruction + prompt + pathNote

  setResponseHeaders(event, {
    'Content-Type': 'text/event-stream; charset=utf-8',
    'Cache-Control': 'no-cache, no-transform',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  })

  const res = event.node.res

  res.write(
    `event: meta\ndata: ${JSON.stringify({
      engine: engineName,
      cwd: workCwd,
      permissionMode: pm,
      model: model || 'default',
      attachments: hasAttachments ? attachments!.map(a => ({ name: a.name, type: a.isImage ? 'image' : a.isPdf ? 'pdf' : a.isText ? 'text' : 'file', size: a.size })) : [],
    })}\n\n`,
  )

  let sessionId = ''
  let queryClosed = false

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
    let turnTimedOut = false
    const turnTimer = setTimeout(() => {
      turnTimedOut = true
      abortController.abort(new Error('turn-timeout'))
    }, turnTimeoutMs)

    // D4 fix (2/2): SSE keepalive. Silent stretches (long tool executions,
    // slow LLM turns) previously let client/proxy read timeouts kill the
    // stream before any terminal event. SSE comments (`: ping`) are ignored
    // by every standard parser but keep the socket warm.
    const keepalive = setInterval(() => {
      try {
        if (!queryClosed) res.write(': ping\n\n')
      } catch { /* socket gone; the turn timer still bounds the query */ }
    }, 15_000)

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

    const q = engine.query({
      prompt,
      cwd: workCwd,
      permissionMode: pm,
      model: model || undefined,
      allowedTools: effectiveAllowedTools,
      resume: resume || undefined,
      maxTurns: maxTurns || 50,
      reasoningEffort: reasoningEffort && reasoningEffort !== 'auto' ? reasoningEffort : undefined,
      fullPromptText,
      // Engines without native cross-request sessions get the prior
      // transcript replayed into the prompt (multi-turn continuity).
      ...(replayHistory.length ? { history: replayHistory } : {}),
      ...(isClaude && hasAttachments && attachmentBlocks.length > 0
        ? { attachmentBlocks: attachmentBlocks as any }
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
      if (message.type === 'result') {
        // result message only sends event: done once, avoiding duplicate processing by frontend handler
        res.write(`event: done\ndata: ${JSON.stringify(message)}\n\n`)
        // D4 fix (3/3): the SDK iterator may keep the stream open long after
        // the final result (background subagents, shell keeps). End the
        // response immediately on result — the client must not wait on it.
        break
      } else {
        res.write(`data: ${JSON.stringify(message)}\n\n`)
      }
    }
  } catch (e: any) {
    const errMsg = e?.message || String(e)
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
  } finally {
    clearTimeout(turnTimer)
    clearInterval(keepalive)
    if (!queryClosed) {
      denyAllPending(sessionId || '_pre_init', 'Query ended')
    }
    res.end()
  }
})
