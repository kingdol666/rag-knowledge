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
import { getEngine, normalizeEngine, type PermissionMode } from '~/server/engines'
import { getProjectRoot } from '~/server/utils/claude-config'
import { addPending, denyAllPending, resolvePending } from '~/server/utils/claude-pending'
import { upsertSession, saveMessage } from '~/server/utils/chat-db'
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
  reasoningEffort?: 'auto' | 'low' | 'medium' | 'high' | 'xhigh' | 'max'
  engine?: 'claude' | 'omp'
}

/** Safe read-only tools (pre-approved in all modes) */
const SAFE_READS = ['Read', 'Glob', 'Grep']
/** All tools (bypassPermissions mode) */
const ALL_TOOLS = [
  'Read', 'Glob', 'Grep', 'Bash', 'Edit', 'Write', 'WebSearch', 'WebFetch',
]

const PERMISSION_TIMEOUT_MS = 5 * 60 * 1000
const TEXT_INLINE_LIMIT = 100 * 1024 // 文本类附件内联上限 100KB

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
 * Build a KB-enhanced system instruction prepended to the user prompt.
 * When kbEnhanced is true, this tells Claude Agent to use the
 * knowledgebase-search skill for retrieval-augmented answers.
 *
 * @param kbIds - selected KB IDs; empty = search ALL KBs
 */
function buildKbInstruction(kbIds: string[]): string {
  if (kbIds.length > 0) {
    const kbIdList = kbIds.map((id) => '`' + id + '`').join(', ')
    const kbCount = kbIds.length

    return [
      '',
      '## [System: Knowledge Base Retrieval-Augmented Answer Mode]',
      '',
      'You are answering the user\'s question. You MUST use the knowledge base retrieval system to enhance your answer quality.',
      'Follow these steps strictly:',
      '',
      '### Step 1: Analyze the Question',
      'Carefully read the user\'s question. Extract key entities, attributes, and constraints.',
      '',
      `### Step 2: Search Knowledge Bases`,
      `Invoke \`/knowledgebase-search\` skill to search the following ${kbCount} knowledge base(s): ${kbIdList}.`,
      '  - Follow the knowledgebase-search skill QDCVR pipeline strictly (Step 0 Query Rewrite -> Step 1 KB Selection -> Step 2 Vector + Two-Stage Retrieval -> Step 2.5 Dedup + Threshold -> Step 3 Content Verification -> Step 6 Synthesized Answer)',
      '  - Only use results with content verification score >= 4 for your answer',
      '  - Focus on the specified KBs, do not drift to unrelated topics',
      '',
      '### Step 3: Synthesize Answer',
      'Based on the reliably retrieved knowledge, synthesize a clear, structured answer.',
      '  - Cite specific document names and sources',
      '  - Annotate information credibility (P0 strong / P1 reference / P2 weak)',
      '  - If no relevant information is found, state this honestly',
      '',
      '### Critical Reminders:',
      '- **Retrieve first, then answer** -- never guess from memory',
      '- **Stay focused** on the specified knowledge bases',
      '- Use Step 0 query rewriting for vague queries to optimize retrieval',
      '- Never fabricate answers -- say "not found in KB" if needed',
      '',
      '---',
      '',
      'Here is the user\'s question:',
      '',
    ].join('\n')
  }

  // All-KB search mode
  return [
    '',
    '## [System: Knowledge Base Retrieval-Augmented Answer Mode -- Full Library Search]',
    '',
    'You are answering the user\'s question. You MUST use the knowledge base retrieval system to enhance your answer quality.',
    'Follow these steps strictly:',
    '',
    '### Step 1: Analyze the Question',
    'Carefully read the user\'s question. Extract key entities, attributes, and constraints.',
    '',
    '### Step 2: Full Library Search',
    'Invoke `/knowledgebase-search` skill to search ALL available knowledge bases.',
    '  - Follow the knowledgebase-search skill QDCVR pipeline strictly (Step 0 Query Rewrite -> Step 1 KB Selection -> Step 2 Vector + Two-Stage Retrieval -> Step 2.5 Dedup + Threshold -> Step 3 Content Verification -> Step 6 Synthesized Answer)',
    '  - If results concentrate in <2 KBs, auto-upgrade to enterprise multi-strategy search',
    '  - Only use results with content verification score >= 4 for your answer',
    '',
    '### Step 3: Synthesize Answer',
    'Based on the reliably retrieved knowledge, synthesize a clear, structured answer.',
    '  - Cite specific document names and source KBs',
    '  - Annotate information credibility (P0 strong / P1 reference / P2 weak)',
    '  - If no relevant information is found in ANY KB, state this honestly',
    '',
    '### Critical Reminders:',
    '- **Retrieve first, then answer** -- never guess from memory',
    '- **Search across ALL KBs** comprehensively -- don\'t miss any relevant source',
    '- Use Step 0 query rewriting for vague queries to optimize retrieval',
    '- Never fabricate answers -- say "not found in KB" if needed',
    '',
    '---',
    '',
    'Here is the user\'s question:',
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

  const pm: PermissionMode =
    permissionMode &&
    ['default', 'acceptEdits', 'bypassPermissions', 'plan', 'dontAsk'].includes(
      permissionMode,
    )
      ? (permissionMode as PermissionMode)
      : 'default'

  const engineName = normalizeEngine(engineParam)
  const workCwd = cwd?.trim() || getProjectRoot()

  const effectiveAllowedTools =
    pm === 'bypassPermissions'
      ? ALL_TOOLS
      : allowedTools && allowedTools.length > 0
        ? allowedTools
        : SAFE_READS

  const needsCanUseTool = pm !== 'bypassPermissions' && pm !== 'dontAsk'

  // Process attachments -> content blocks
  const hasAttachments = Array.isArray(attachments) && attachments.length > 0
  const { blocks: attachmentBlocks, pathNote } = hasAttachments
    ? attachmentsToBlocks(attachments!)
    : { blocks: [], pathNote: '' }

  // KB-enhanced instruction (prepended when toggle is on)
  const kbInstruction = kbEnhanced ? buildKbInstruction(kbIds) : ''

  // Full prompt = KB instruction + user input + path hint
  const fullPromptText = kbInstruction + prompt + pathNote

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
    // Permission callback factory — shared by both engines (approval modes only)
    const onPermissionRequest = needsCanUseTool
      ? async (
          toolName: string,
          input: Record<string, unknown>,
          toolUseId: string,
          sid: string,
        ): Promise<{ behavior: string; message?: string }> => {
          res.write(
            `event: permission_request\ndata: ${JSON.stringify({
              toolName,
              input,
              toolUseId,
              sessionId: sid || sessionId,
            })}\n\n`,
          )
          const { promise, resolve } = Promise.withResolvers<{ behavior: string; message?: string }>()
          addPending(sessionId || '_pre_init', toolUseId, toolName, input, resolve as any)
          setTimeout(() => {
            resolvePending(sessionId || '_pre_init', toolUseId, {
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

    // ══════ 用户提问持久化（放在 query 前，覆盖多轮 resume 和首轮新会话） ══════
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
      } else {
        res.write(`data: ${JSON.stringify(message)}\n\n`)
      }
    }
  } catch (e: any) {
    const errMsg = e?.message || String(e)
    res.write(
      `event: error\ndata: ${JSON.stringify({ error: errMsg, code: 'SDK_QUERY_FAILED' })}\n\n`,
    )
  } finally {
    if (!queryClosed) {
      denyAllPending(sessionId || '_pre_init', 'Query ended')
    }
    res.end()
  }
})
