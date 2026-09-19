/**
 * POST /api/claude/permission
 *
 * User approves/denies a tool permission request (paired with chat SSE permission_request events).
 *
 * Request body: { sessionId, toolUseId, behavior: 'allow' | 'deny', message?, optionId? }
 *
 * The pending Promise is resolved here -> the engine query continues.
 * - Claude (SDK canUseTool): allow/deny with updatedInput.
 * - ACP harnesses (dsh/hermes): the user's `optionId` selects one of the
 *   harness-provided options (allow_once/allow_always/reject_*) verbatim.
 */
import { resolvePending, getPending, findSessionByToolUseId } from '~/server/utils/claude-pending'

interface PermissionBody {
  sessionId?: string
  toolUseId?: string
  behavior?: 'allow' | 'deny'
  message?: string
  optionId?: string
}

export default defineEventHandler(async (event) => {
  const body = await readBody<PermissionBody>(event)
  const { sessionId, toolUseId, behavior, message, optionId } = body || {}

  if (!toolUseId || !behavior) {
    throw createError({
      statusCode: 400,
      // sessionId 可为空：pre-init 竞态下 SSE 载荷里的 sessionId 可能是 ''，
      // 此时由全局唯一的 toolUseId 定位 pending 条目。
      statusMessage: 'toolUseId, behavior 必填（sessionId 可为空，按 toolUseId 兜底定位）',
    })
  }

  // Pre-init race: the pending entry may be keyed under '_pre_init' (or any
  // adapter session id) while the SSE payload carried an empty sessionId.
  // toolUseId is globally unique, so fall back to locating it directly.
  let pending = getPending(sessionId, toolUseId)
  let key = sessionId
  if (!pending) {
    const found = findSessionByToolUseId(toolUseId)
    if (found) {
      key = found
      pending = getPending(found, toolUseId)
    }
  }
  if (!pending) {
    return { success: false, error: '待审批请求不存在（可能已超时或已处理）' }
  }

  const decision =
    behavior === 'allow'
      ? {
          behavior: 'allow' as const,
          updatedInput: pending.input,
          ...(optionId ? { optionId } : {}),
        }
      : { behavior: 'deny' as const, message: message || 'User denied' }

  resolvePending(key, toolUseId, decision)

  return { success: true, behavior, toolName: pending.toolName, ...(optionId ? { optionId } : {}) }
})
