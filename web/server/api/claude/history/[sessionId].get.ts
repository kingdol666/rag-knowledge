/**
 * GET /api/claude/history/[sessionId]
 *
 * Get all messages for a specific session (from SQLite, stored order).
 * Frontend replays these SDK messages through MessageProcessor for rendering.
 * Returns session title so the UI can show the user's original question at the top
 * (covers legacy sessions that were stored before user prompts were persisted).
 */
import { getSessionMessages, getSessionMeta } from '~/server/utils/chat-db'

export default defineEventHandler((event) => {
  const sessionId = getRouterParam(event, 'sessionId')
  if (!sessionId) {
    throw createError({ statusCode: 400, statusMessage: 'sessionId 必填' })
  }
  const messages = getSessionMessages(sessionId)
  const meta = getSessionMeta(sessionId)
  return { success: true, sessionId, title: meta?.title ?? null, count: messages.length, messages }
})
