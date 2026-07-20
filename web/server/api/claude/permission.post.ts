/**
 * POST /api/claude/permission
 *
 * User approves/denies a tool permission request (paired with chat SSE permission_request events).
 *
 * Request body: { sessionId, toolUseId, behavior: 'allow' | 'deny', message? }
 *
 * The canUseTool callback Promise is resolved here -> SDK query continues.
 */
import { resolvePending, getPending } from '~/server/utils/claude-pending'

interface PermissionBody {
  sessionId?: string
  toolUseId?: string
  behavior?: 'allow' | 'deny'
  message?: string
}

export default defineEventHandler(async (event) => {
  const body = await readBody<PermissionBody>(event)
  const { sessionId, toolUseId, behavior, message } = body || {}

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
      ? { behavior: 'allow' as const, updatedInput: pending.input }
      : { behavior: 'deny' as const, message: message || 'User denied' }

  resolvePending(sessionId, toolUseId, decision)

  return { success: true, behavior, toolName: pending.toolName }
})
