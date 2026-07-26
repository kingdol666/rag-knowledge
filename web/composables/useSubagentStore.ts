/**
 * useSubagentStore — reactive store for delegated child-agent (subagent) sessions.
 * ─────────────────────────────────────────────────────────────────────────────
 * Both Claude Code (Task/Agent tool) and OMP delegate work to child agents.
 * The engines forward those child messages tagged with:
 *   - parent_tool_use_id  — the tool_use id of the delegating Task/Agent call
 *                            (groups all messages from ONE child into one session)
 *   - subagent_type       — e.g. "task", "code-reviewer", "archival"
 *   - task_description    — what the child was asked to do
 *
 * This store groups child messages by parent_tool_use_id into "subagent cards"
 * that the sidebar renders. Each card has a status light — pulsing while
 * running, solid when done, red on error.
 *
 * Pure TS + Vue reactivity — no backend dependency.
 */
import { ref, computed, type Ref } from 'vue'
import type { UIMessage, TodoItem } from '~/utils/claude-messages'

/** A single subagent (child agent) session, grouped by parent_tool_use_id. */
export interface SubagentSession {
  /** parent_tool_use_id — the delegating Task/Agent tool_use id. */
  id: string
  /** Child agent type (e.g. "task", "code-reviewer") — may be unknown. */
  type: string
  /** What the child was asked to do. */
  description: string
  /** Lifecycle: running → done | error. */
  status: 'running' | 'done' | 'error'
  /** Epoch ms when first seen. */
  createdAt: number
  /** Epoch ms of last update. */
  updatedAt: number
  /** The engine that produced this child ('claude' | 'omp'). */
  engine: 'claude' | 'omp'
  /** Child transcript — same UIMessage shapes the main timeline uses. */
  messages: UIMessage[]
  /** Accumulated streaming text (for live typewriter in the detail drawer). */
  streamingText: string
  /** Accumulated thinking text. */
  streamingThinking: string
  /** Latest todo snapshot from this child (if it used TodoWrite). */
  todos: TodoItem[]
  /** Tool-use counter (how many tools the child has invoked). */
  toolCount: number
  /** Final result text when the child completes. */
  resultText: string
  /** Error message if status === 'error'. */
  error: string
}

/** Read a string field off an unknown SDK message, returning undefined if absent. */
function readStr(obj: unknown, key: string): string | undefined {
  if (obj && typeof obj === 'object' && key in obj) {
    const v = (obj as Record<string, unknown>)[key]
    return typeof v === 'string' && v.length ? v : undefined
  }
  return undefined
}

/** Read parent_tool_use_id (string|null) off an unknown SDK message. */
function readParentId(obj: unknown): string | null {
  if (!obj || typeof obj !== 'object') return null
  const direct = readStr(obj, 'parent_tool_use_id')
  if (direct) return direct
  // Nested under .message
  const msg = (obj as Record<string, unknown>)['message']
  return readStr(msg, 'parent_tool_use_id') ?? null
}

// ─── module-level singleton ──────────────────────────────────────────────
const _sessions: Ref<SubagentSession[]> = ref([])
const _selectedId = ref<string | null>(null)

/** Find or create a subagent session by parent_tool_use_id. */
function _getOrCreate(
  parentToolUseId: string,
  engine: 'claude' | 'omp',
  meta: { subagentType?: string; taskDescription?: string },
): SubagentSession {
  const existing = _sessions.value.find((x) => x.id === parentToolUseId)
  if (existing) {
    if (!existing.type && meta.subagentType) existing.type = meta.subagentType
    if (!existing.description && meta.taskDescription) existing.description = meta.taskDescription
    existing.updatedAt = Date.now()
    return existing
  }
  const s: SubagentSession = {
    id: parentToolUseId,
    type: meta.subagentType || 'subagent',
    description: meta.taskDescription || '(delegated task)',
    status: 'running',
    createdAt: Date.now(),
    updatedAt: Date.now(),
    engine,
    messages: [],
    streamingText: '',
    streamingThinking: '',
    todos: [],
    toolCount: 0,
    resultText: '',
    error: '',
  }
  _sessions.value.push(s)
  return s
}

/** Public store API. */
export function useSubagentStore() {
  /** Newest-first ordering for the sidebar. */
  const sessions = computed(() =>
    [..._sessions.value].sort((a, b) => b.updatedAt - a.updatedAt),
  )
  const runningCount = computed(
    () => _sessions.value.filter((s) => s.status === 'running').length,
  )
  const totalCount = computed(() => _sessions.value.length)
  const selectedId = _selectedId
  const selected = computed(
    () => _sessions.value.find((s) => s.id === _selectedId.value) || null,
  )

  function select(id: string | null): void {
    _selectedId.value = id
  }

  /**
   * Ingest one raw SDK message. If it carries parent_tool_use_id, route it
   * into the matching subagent session and return true (caller should NOT
   * also push it to the main timeline, OR may push a compact reference).
   * Returns false for main-agent messages (no parent_tool_use_id).
   *
   * @param uiMsgs  — already-processed UIMessages from MessageProcessor
   * @param rawMsg  — the original SDK message (for metadata extraction)
   * @param engine  — which engine produced this
   */
  function ingest(
    uiMsgs: UIMessage[],
    rawMsg: unknown,
    engine: 'claude' | 'omp',
  ): boolean {
    const parentId = readParentId(rawMsg)
    if (!parentId) return false

    const meta = {
      subagentType: readStr(rawMsg, 'subagent_type') || readStr((rawMsg as Record<string, unknown> | null)?.message, 'subagent_type'),
      taskDescription: readStr(rawMsg, 'task_description') || readStr((rawMsg as Record<string, unknown> | null)?.message, 'task_description'),
    }
    const s = _getOrCreate(parentId, engine, meta)
    s.engine = engine

    for (const m of uiMsgs) {
      if (s.messages.some((x) => x.id === m.id)) continue
      s.messages.push(m)
      if (m.kind === 'tool_use') s.toolCount++
      if (m.kind === 'todo') s.todos = m.todos
    }

    // Streaming deltas (text/thinking) for live typewriter
    const rawObj = rawMsg as Record<string, unknown> | null
    if (rawObj?.type === 'stream_event') {
      const evt = rawObj.event as Record<string, unknown> | undefined
      if (evt?.type === 'content_block_delta') {
        const delta = evt.delta as Record<string, unknown> | undefined
        const dt = delta?.type
        if (dt === 'text_delta') {
          const t = delta?.text
          if (typeof t === 'string') s.streamingText += t
        } else if (dt === 'thinking_delta') {
          const t = delta?.thinking
          if (typeof t === 'string') s.streamingThinking += t
        }
      }
    }

    // Full assistant message folds the streaming buffer back in
    if (rawObj?.type === 'assistant') {
      s.streamingText = ''
      s.streamingThinking = ''
    }

    s.updatedAt = Date.now()
    return true
  }

  /**
   * Proactively register a delegation the moment the main agent invokes the
   * Agent/Task tool — before any child messages arrive. This guarantees the
   * sidebar shows a "running" card even for async/background delegations whose
   * child messages never reach the frontend (they arrive after the SSE stream
   * closes). When the main turn ends, finalizeEngine flips it to done.
   *
   * Idempotent: if a session with this id already exists (child messages
   * already arrived via ingest), it is left untouched.
   */
  function registerDelegation(
    toolUseId: string,
    engine: 'claude' | 'omp',
    meta: { subagentType?: string; taskDescription?: string },
  ): void {
    if (_sessions.value.some((x) => x.id === toolUseId)) return
    _sessions.value.push({
      id: toolUseId,
      type: meta.subagentType || 'subagent',
      description: meta.taskDescription || '(delegated task)',
      status: 'running',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      engine,
      messages: [],
      streamingText: '',
      streamingThinking: '',
      todos: [],
      toolCount: 0,
      resultText: '',
      error: '',
    })
  }

  /** Finalize all running subagents for an engine when its main turn ends. */
  function finalizeEngine(engine: 'claude' | 'omp'): void {
    for (const s of _sessions.value) {
      if (s.engine === engine && s.status === 'running') {
        s.status = 'done'
        s.updatedAt = Date.now()
      }
    }
  }

  /** Finalize a specific subagent when its delegating tool_result arrives. */
  function finalizeById(id: string, isError = false): void {
    const s = _sessions.value.find((x) => x.id === id)
    if (!s || s.status !== 'running') return
    s.status = isError ? 'error' : 'done'
    if (isError) s.error = 'tool returned an error'
    s.updatedAt = Date.now()
  }

  /** Clear all sessions (e.g. on "Clear Chat"). */
  function clear(): void {
    _sessions.value = []
    _selectedId.value = null
  }

  /** Remove only completed/error sessions. */
  function clearFinished(): void {
    _sessions.value = _sessions.value.filter((s) => s.status === 'running')
  }

  return {
    sessions,
    runningCount,
    totalCount,
    selectedId,
    selected,
    select,
    ingest,
    registerDelegation,
    finalizeEngine,
    finalizeById,
    clear,
    clearFinished,
  }
}
