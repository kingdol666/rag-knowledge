/**
 * POST /api/kb/native-search
 *
 * ⭐ Native KB retrieval for EXTERNAL systems (AgentWorkShop rag-bridge 等).
 *
 * The caller passes ONLY the question; this endpoint drives the platform's
 * FULL native retrieval pipeline server-side and returns the final answer:
 *   claude engine (in-process Claude Agent SDK, cwd = repo root)
 *     → /knowledgebase-search skill (QDCVR v2: Step 0 query rewrite →
 *       KB selection → vector+two-stage → dedup+threshold → content
 *       verification → synthesized answer; librarian deep-retrieval
 *       fallback; honest not-found)
 *     → kb-mcp tools via the repo-root .mcp.json (stdio server).
 *
 * This is the same flow the chat UI runs with kbEnhanced=true — the
 * instruction is shared verbatim (server/utils/kb-instruction.ts, which also
 * owns prompt assembly). External callers do NOT orchestrate two-stage/index
 * steps themselves; one call, one complete answer with citations and
 * credibility annotations.
 *
 * Auth: global web token middleware (Bearer) — same as every /api/* route.
 * Unattended by design: permissionMode bypassPermissions (read-only usage,
 * server-built prompt; there is no human to answer permission prompts on a
 * machine-to-machine call) + hard timeout via AbortSignal.
 *
 * Request : { query, kb_id?, kb_ids?, top_k?, timeout_ms?, model? }
 * Response: { success, query, kb_ids, answer, engine, mode, tools_used,
 *             session_id, duration_ms, total_cost_usd, num_turns, stop_reason }
 *           failure → { success:false, error, stage:'timeout'|'engine', ... }
 *
 * Degradation contract for callers: on success:false the legacy chunk-level
 * pipeline (POST :8770/api/v1/search/two-stage) remains available as fallback.
 */
import { defineEventHandler, createError, readBody } from 'h3'
import { engineTurn, getEngine } from '~/server/engines'
import { getProjectRoot } from '~/server/utils/claude-config'
import { buildNativeSearchPrompt } from '~/server/utils/kb-instruction'

interface NativeSearchBody {
  query?: string
  kb_id?: string
  kb_ids?: string[]
  top_k?: number
  timeout_ms?: number
  max_turns?: number
  model?: string
}

// Deep flows (librarian subagent + content gate) measured 210s+ in practice —
// default and ceiling sized so a legit full run is not aborted mid-turn.
const DEFAULT_TIMEOUT_MS = 280_000
const MAX_TIMEOUT_MS = 420_000
const MAX_QUESTION_CHARS = 8000

/**
 * D4 fix: bounded retrieval turn. The librarian deep-retrieval subagent
 * ('Task') measured 210s+ per hop and was the main non-convergence driver
 * (7-11 tool calls without reaching a final answer inside 280-420s). Drop it
 * from the one-shot contract — the QDCVR skill degrades to its direct path —
 * and cap turns at 24 so the turn always settles before the caller's timeout.
 */
const RETRIEVAL_TOOLS = ['Read', 'Glob', 'Grep', 'Skill']
const DEFAULT_MAX_TURNS = 24
const MAX_MAX_TURNS = 40

/**
 * Sanitize the external question before it enters the retrieval turn:
 * strip control characters (prompt-shaping noise), cap length. Returns null
 * when nothing usable remains.
 */
function sanitizeQuestion(raw: unknown): string | null {
  const text = String(raw ?? '')
    .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, ' ')
    .replace(/\s+$/g, '')
    .trim()
  if (!text) return null
  return text.length > MAX_QUESTION_CHARS ? text.slice(0, MAX_QUESTION_CHARS) : text
}

export default defineEventHandler(async (event) => {
  const body = await readBody<NativeSearchBody>(event)
  const question = sanitizeQuestion(body?.query)
  if (!question) {
    throw createError({ statusCode: 400, statusMessage: 'query (string) 必填' })
  }

  // KB scope: kb_ids array wins; kb_id (single, two-stage 契约同形) splits on
  // commas for convenience. Empty → full-library native search.
  let kbIds = Array.isArray(body?.kb_ids)
    ? body.kb_ids.map(s => String(s).trim()).filter(Boolean)
    : []
  if (!kbIds.length && body?.kb_id) {
    kbIds = String(body.kb_id).split(',').map(s => s.trim()).filter(Boolean)
  }
  const topK = Math.min(Math.max(Math.round(Number(body?.top_k) || 5), 1), 20)
  const maxTurns = Math.min(
    Math.max(Math.round(Number(body?.max_turns) || DEFAULT_MAX_TURNS), 4),
    MAX_MAX_TURNS,
  )
  const timeoutMs = Math.min(
    Math.max(Math.round(Number(body?.timeout_ms) || DEFAULT_TIMEOUT_MS), 10_000),
    MAX_TIMEOUT_MS,
  )

  const abort = new AbortController()
  const timer = setTimeout(() => abort.abort(), timeoutMs)

  let sessionId = ''
  let resultFrame: Record<string, any> | null = null
  const toolsUsed: string[] = []

  try {
    const engine = getEngine('claude')
    for await (const msg of engineTurn(engine, {
      prompt: question,
      cwd: getProjectRoot(),
      permissionMode: 'bypassPermissions',
      model: body?.model || undefined,
      allowedTools: RETRIEVAL_TOOLS,
      maxTurns,
      fullPromptText: buildNativeSearchPrompt(kbIds, question, topK),
      signal: abort.signal,
    })) {
      if (msg.type === 'assistant') {
        for (const block of (msg.message?.content ?? []) as Array<Record<string, any>>) {
          if (block?.type === 'tool_use' && block?.name) {
            toolsUsed.push(String(block.name))
          }
        }
      } else if (msg.type === 'result') {
        resultFrame = msg as Record<string, any>
        sessionId = String(msg.session_id ?? '')
      } else if (msg.type === 'system' && msg.subtype === 'init') {
        sessionId = String(msg.session_id ?? sessionId)
      }
    }
  } catch (e) {
    const errText = e instanceof Error ? e.message : String(e)
    const timedOut = abort.signal.aborted
    return {
      success: false as const,
      stage: timedOut ? 'timeout' as const : 'engine' as const,
      error: timedOut
        ? `native retrieval timed out after ${timeoutMs}ms`
        : `native retrieval failed: ${errText}`,
      hint: '确认 web 层已配置 ANTHROPIC_API_KEY 且 kb-mcp 可用；或回退 POST :8770/api/v1/search/two-stage（chunk 级）',
      ...(toolsUsed.length ? { tools_used: toolsUsed } : {}),
    }
  } finally {
    clearTimeout(timer)
  }

  const answer = String(resultFrame?.result ?? '').trim()
  if (!resultFrame || resultFrame.is_error || !answer) {
    return {
      success: false as const,
      stage: 'engine' as const,
      error: resultFrame?.is_error
        ? `retrieval turn ended with error: ${String(resultFrame.result ?? resultFrame.terminal_reason ?? 'unknown').slice(0, 500)}`
        : 'retrieval turn produced no answer text',
      session_id: sessionId || undefined,
      ...(toolsUsed.length ? { tools_used: toolsUsed } : {}),
    }
  }

  return {
    success: true as const,
    query: question,
    kb_ids: kbIds,
    answer,
    engine: 'claude',
    mode: 'native-qdcvr',
    tools_used: toolsUsed,
    session_id: sessionId || undefined,
    duration_ms: Number(resultFrame.duration_ms ?? 0),
    total_cost_usd: Number(resultFrame.total_cost_usd ?? 0),
    num_turns: Number(resultFrame.num_turns ?? 0),
    stop_reason: resultFrame.stop_reason ?? null,
  }
})
