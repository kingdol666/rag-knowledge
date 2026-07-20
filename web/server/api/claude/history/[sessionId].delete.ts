/**
 * DELETE /api/claude/history/[sessionId]
 *
 * Delete a specific session and all its messages.
 */
import { deleteSession } from '~/server/utils/chat-db'

export default defineEventHandler((event) => {
  const sessionId = getRouterParam(event, 'sessionId')
  if (!sessionId) {
    throw createError({ statusCode: 400, statusMessage: 'sessionId 必填' })
  }
  deleteSession(sessionId)
  return { success: true, sessionId }
})
