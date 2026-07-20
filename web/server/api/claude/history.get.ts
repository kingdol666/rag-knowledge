/**
 * GET /api/claude/history
 *
 * List all persisted chat sessions (from SQLite, sorted by most recently updated).
 */
import { listSessions } from '~/server/utils/chat-db'

export default defineEventHandler((event) => {
  const q = getQuery(event)
  const limit = Math.min(parseInt(String(q.limit)) || 50, 200)
  const sessions = listSessions(limit)
  return { success: true, count: sessions.length, sessions }
})
