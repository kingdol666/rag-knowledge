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
import { resolvePending, getPending } from '~/server/utils/claude-pending'

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

  if (!sessionId || !toolUseId || !behavior) {
    throw createError({
      statusCode: 400,
      statusMessage: 'sessionId, toolUseId, behavior 必填',
    })
  }

  const pending = getPending(sessionId, toolUseId)
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

  resolvePending(sessionId, toolUseId, decision)

  return { success: true, behavior, toolName: pending.toolName, ...(optionId ? { optionId } : {}) }
})
