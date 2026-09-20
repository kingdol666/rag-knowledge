/**
 * POST /api/kb/agent/chat
 *
 * ⭐ THE outward-facing API: external hosts (AgentWorkShop) talk to the KB
 * system's own agent — ONE endpoint, functional decoupling. The caller sends
 * a task prompt; the KB agent autonomously decides how to serve it:
 *   - retrieval / Q&A  → /knowledgebase-search skill (QDCVR pipeline)
 *   - document ingest  → kb-mcp write + index tools
 *   - experience / graph / anything KB-related → its native tools
 * One prompt in, one complete result out — the caller never orchestrates
 * retrieval or ingestion steps itself.
 *
 * Selectable knobs (all optional except prompt, see GET /api/kb/agent/meta):
 *   harness    — engine id, default `claude` (in-process Claude Agent SDK)
 *   permission — mode id, default `bypassPermissions` (highest: unattended,
 *                no human to answer prompts on a machine-to-machine call)
 *   mode       — `sync` (default): hold the HTTP request until the turn
 *                finishes and return the result.
 *                `async`: return immediately with a task_id; the KB system
 *                ALWAYS finishes the received task in the background, and the
 *                task-scoped response becomes available at
 *                GET /api/kb/agent/tasks/:taskId (the async callback surface
 *                — poll it, e.g. from the kb_agent_status tool).
 *
 * Auth: global web token middleware (Bearer). Hard timeout via AbortSignal.
 *
 * Request : { prompt, harness?, permission?, mode?, timeout_ms? }
 * Response (sync)   : { success, reply, engine, permission, tools_used,
 *                       session_id, duration_ms, total_cost_usd, num_turns,
 *                       stop_reason }
 * Response (async)  : { success:true, mode:'async', task_id, status:'running',
 *                       poll }
 *           failure → { success:false, error, stage:'timeout'|'engine'|'validation' }
 */
import { defineEventHandler, createError, readBody } from 'h3'
import { randomUUID } from 'crypto'
import { engineTurn, getEngine, normalizeEngine, getChatMeta } from '~/server/engines'
import { getProjectRoot } from '~/server/utils/claude-config'
import { buildAgentChatPreamble } from '~/server/utils/kb-instruction'
import { registerTask, settleTask } from '~/server/utils/agent-task-registry'

interface AgentChatBody {
  prompt?: string
  harness?: string
  permission?: string
  mode?: string
  timeout_ms?: number
}

const DEFAULT_TIMEOUT_MS = 420_000
const MAX_TIMEOUT_MS = 600_000
const MAX_PROMPT_CHARS = 16_000
const DEFAULT_HARNESS = 'claude'
const DEFAULT_PERMISSION = 'bypassPermissions'

/** Read-only toolset for chat turns (defense in depth under bypass). */
const RETRIEVAL_TOOLS = ['Read', 'Glob', 'Grep', 'Skill', 'Task']

/**
 * Sanitize the external prompt before it enters the agent turn: strip control
 * characters (prompt-shaping noise), cap length. Returns null when nothing
 * usable remains.
 */
function sanitizePrompt(raw: unknown): string | null {
  const text = String(raw ?? '')
    .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, ' ')
    .replace(/\s+$/g, '')
    .trim()
  if (!text) return null
  return text.length > MAX_PROMPT_CHARS ? text.slice(0, MAX_PROMPT_CHARS) : text
}

interface TurnRequest {
  task: string
  engine: string
  permission: string
  timeoutMs: number
}

/** Execute one agent turn and return the response envelope (shared by sync and async paths). */
async function executeTurn(req: TurnRequest): Promise<Record<string, any>> {
  const abort = new AbortController()
  const timer = setTimeout(() => abort.abort(), req.timeoutMs)

  let sessionId = ''
  let resultFrame: Record<string, any> | null = null
  let partialText = ''
  const toolsUsed: string[] = []

  try {
    const engine = getEngine(req.engine)
    for await (const msg of engineTurn(engine, {
      prompt: req.task,
      cwd: getProjectRoot(),
      permissionMode: req.permission,
      model: undefined,
      allowedTools: RETRIEVAL_TOOLS,
      maxTurns: 40,
      fullPromptText: buildAgentChatPreamble() + req.task,
      signal: abort.signal,
    })) {
      if (msg.type === 'assistant') {
        for (const block of (msg.message?.content ?? []) as Array<Record<string, any>>) {
          if (block?.type === 'tool_use' && block?.name) {
            toolsUsed.push(String(block.name))
          }
          if (block?.type === 'text' && block?.text) {
            partialText += String(block.text)
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
    clearTimeout(timer)
    return {
      success: false as const,
      stage: timedOut ? 'timeout' as const : 'engine' as const,
      error: timedOut
        ? `agent turn timed out after ${req.timeoutMs}ms`
        : `agent turn failed: ${errText}`,
      hint: '确认 web 层已配置 ANTHROPIC_API_KEY 且 kb-mcp 可用',
      ...(partialText.trim() ? { partial_text: partialText.trim() } : {}),
      ...(toolsUsed.length ? { tools_used: toolsUsed } : {}),
    }
  }
  clearTimeout(timer)

  const reply = String(resultFrame?.result ?? '').trim()
  if (!resultFrame || resultFrame.is_error || !reply) {
    const partial = partialText.trim()
    return {
      success: false as const,
      stage: abort.signal.aborted ? 'timeout' as const : 'engine' as const,
      error: resultFrame?.is_error
        ? `agent turn ended with error: ${String(resultFrame.result ?? resultFrame.terminal_reason ?? 'unknown').slice(0, 500)}`
        : abort.signal.aborted
          ? `agent turn timed out after ${req.timeoutMs}ms before a final result frame`
          : 'agent turn produced no reply text',
      ...(partial ? { partial_text: partial } : {}),
      session_id: sessionId || undefined,
      ...(toolsUsed.length ? { tools_used: toolsUsed } : {}),
    }
  }

  return {
    success: true as const,
    reply,
    engine: req.engine,
    permission: req.permission,
    tools_used: toolsUsed,
    session_id: sessionId || undefined,
    duration_ms: Number(resultFrame.duration_ms ?? 0),
    total_cost_usd: Number(resultFrame.total_cost_usd ?? 0),
    num_turns: Number(resultFrame.num_turns ?? 0),
    stop_reason: resultFrame.stop_reason ?? null,
  }
}

export default defineEventHandler(async (event) => {
  const body = await readBody<AgentChatBody>(event)
  const task = sanitizePrompt(body?.prompt)
  if (!task) {
    throw createError({ statusCode: 400, statusMessage: 'prompt (string) 必填' })
  }

  // Engine + permission selection: harness must be a chat-capable id; the
  // permission mode must be one the selected harness really exposes (each
  // adapter falls back to its safest mode for unknown values anyway).
  const harness = normalizeEngine(body?.harness || DEFAULT_HARNESS)
  if (!harness) {
    throw createError({
      statusCode: 400,
      statusMessage: `Unknown or chat-unsupported harness '${body?.harness}' — GET /api/kb/agent/meta for the selectable list`,
    })
  }
  const meta = getChatMeta(harness)
  const modeIds = (meta?.permissionModes ?? []).map(m => m.id)
  const requested = String(body?.permission || '').trim() || DEFAULT_PERMISSION
  const permission = modeIds.includes(requested) ? requested : DEFAULT_PERMISSION

  const mode = String(body?.mode || '').trim().toLowerCase() === 'async' ? 'async' : 'sync'
  const timeoutMs = Math.min(
    Math.max(Math.round(Number(body?.timeout_ms) || DEFAULT_TIMEOUT_MS), 10_000),
    MAX_TIMEOUT_MS,
  )

  if (mode === 'async') {
    // Submit-and-return: register the task, execute detached from this HTTP
    // request, expose the task-scoped response at GET /api/kb/agent/tasks/:id.
    const taskId = `kbt_${Date.now().toString(36)}_${randomUUID().slice(0, 8)}`
    registerTask({
      task_id: taskId,
      status: 'running',
      mode: 'async',
      prompt: task,
      engine: harness,
      permission,
      created_at: new Date().toISOString(),
    })
    const turnRequest: TurnRequest = { task, engine: harness, permission, timeoutMs }
    void executeTurn(turnRequest)
      .then((result) => {
        settleTask(taskId, result.success === true ? 'completed' : 'failed', result)
      })
      .catch((err) => {
        settleTask(taskId, 'failed', {
          success: false,
          stage: 'engine',
          error: err instanceof Error ? err.message : String(err),
        })
      })
    return {
      success: true as const,
      mode: 'async' as const,
      task_id: taskId,
      status: 'running' as const,
      engine: harness,
      permission,
      poll: `GET /api/kb/agent/tasks/${taskId}`,
    }
  }

  return await executeTurn({ task, engine: harness, permission, timeoutMs })
})
