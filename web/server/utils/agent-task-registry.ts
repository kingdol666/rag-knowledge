/**
 * Agent chat async task registry — in-process store for tasks submitted via
 * POST /api/kb/agent/chat with mode:"async".
 *
 * Lifecycle: the chat endpoint registers a `running` record, executes the
 * agent turn detached from the HTTP request, and stores the full response
 * envelope under the same task_id when the turn settles. External callers
 * (AgentWorkShop kb_agent_status) poll GET /api/kb/agent/tasks/:taskId for
 * the response "针对之前 task" — the callback surface of the async contract.
 *
 * Scope: single web-server process (the production deployment runs one).
 * Entries are pruned oldest-first past MAX_ENTRIES / TASK_TTL_MS so a long
 *-running server cannot leak memory.
 */

export interface AgentTaskRecord {
  task_id: string
  status: 'running' | 'completed' | 'failed'
  mode: 'async'
  prompt: string
  engine: string
  permission: string
  created_at: string
  finished_at?: string
  /** The full chat response envelope, present once status !== 'running'. */
  result?: Record<string, any>
}

const TASK_TTL_MS = 2 * 60 * 60_000 // 2h
const MAX_ENTRIES = 200

// HMR / dev hot-reload resilience: keep the map on globalThis like the
// other cross-reload singletons in this codebase.
const g = globalThis as typeof globalThis & { __kbAgentTaskRegistry?: Map<string, AgentTaskRecord> }
if (!g.__kbAgentTaskRegistry) g.__kbAgentTaskRegistry = new Map()
const registry: Map<string, AgentTaskRecord> = g.__kbAgentTaskRegistry

export function registerTask(rec: AgentTaskRecord): void {
  registry.set(rec.task_id, rec)
  prune()
}

export function getTask(taskId: string): AgentTaskRecord | undefined {
  return registry.get(taskId)
}

export function settleTask(taskId: string, status: 'completed' | 'failed', result: Record<string, any>): void {
  const rec = registry.get(taskId)
  if (!rec) return
  rec.status = status
  rec.finished_at = new Date().toISOString()
  rec.result = result
}

function prune(): void {
  const now = Date.now()
  for (const [id, rec] of registry) {
    const created = Date.parse(rec.created_at)
    if (Number.isFinite(created) && now - created > TASK_TTL_MS) registry.delete(id)
  }
  while (registry.size > MAX_ENTRIES) {
    const oldest = registry.keys().next().value
    if (oldest === undefined) break
    registry.delete(oldest)
  }
}
