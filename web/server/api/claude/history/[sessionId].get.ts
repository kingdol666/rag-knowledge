/**
 * GET /api/claude/history/[sessionId]
 *
 * Get all messages for a specific session (from SQLite, stored order).
 * Frontend replays these SDK messages through MessageProcessor for rendering.
 */
import { getSessionMessages } from '~/server/utils/chat-db'

export default defineEventHandler((event) => {
  const sessionId = getRouterParam(event, 'sessionId')
  if (!sessionId) {
    throw createError({ statusCode: 400, statusMessage: 'sessionId 必填' })
  }
  const messages = getSessionMessages(sessionId)
  return { success: true, sessionId, count: messages.length, messages }
})
