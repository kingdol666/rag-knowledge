/**
 * GET /api/kb/agent/meta
 *
 * Discovery surface for the KB system's outward-facing agent chat API
 * (POST /api/kb/agent/chat): which harnesses an external caller may select,
 * which permission modes each supports, and the defaults applied when the
 * caller omits them (harness=claude, permission=bypassPermissions — the
 * highest, unattended-friendly mode).
 *
 * Auth: global web token middleware (Bearer), same as every /api/* route.
 */
import { defineEventHandler } from 'h3'
import { CHAT_CAPABLE_IDS, getChatMeta } from '~/server/engines'
import { PERMISSION_MODES } from '~/server/utils/claude-config'

const DEFAULT_HARNESS = 'claude'
const DEFAULT_PERMISSION = 'bypassPermissions'

export default defineEventHandler(async () => {
  const engines = CHAT_CAPABLE_IDS.map((id) => {
    const meta = getChatMeta(id)
    return {
      id,
      label: meta?.label ?? id,
      transport: meta?.transport ?? null,
      hitl: meta?.hitl === true,
      permissionModes: (meta?.permissionModes ?? []).map(m => ({
        id: m.id,
        label: m.label,
        desc: m.desc,
      })),
      defaultMode: meta?.defaultMode ?? DEFAULT_PERMISSION,
    }
  })

  return {
    success: true as const,
    chat: {
      endpoint: 'POST /api/kb/agent/chat',
      body: {
        prompt: 'string (required) — the task for the KB agent (retrieve / ingest / experience / ...)',
        harness: `string (optional, default "${DEFAULT_HARNESS}") — one of engines[].id`,
        permission: `string (optional, default "${DEFAULT_PERMISSION}") — one of engines[].permissionModes[].id`,
        mode: "string (optional, default 'sync') — 'sync': wait and return the result; 'async': return task_id immediately, the KB system always finishes the task in the background",
        timeout_ms: 'number (optional, default 420000, max 600000)',
      },
      async_callback: {
        submit: "POST /api/kb/agent/chat {mode:'async'} → { task_id }",
        poll: 'GET /api/kb/agent/tasks/:taskId → { status: running|completed|failed, result }',
      },
    },
    defaults: { harness: DEFAULT_HARNESS, permission: DEFAULT_PERMISSION },
    permission_modes: PERMISSION_MODES,
    engines,
  }
})
