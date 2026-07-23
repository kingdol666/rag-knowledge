/**
 * GET /api/claude/history
 *
 * List all persisted chat sessions (from SQLite, sorted by most recently updated).
 */
import { listSessions } from '~/server/utils/chat-db'

export default defineEventHandler((event) => {
  const q = getQuery(event)
  const limit = Math.min(parseInt(String(q.limit)) || 50, 200)
  // Filter sessions by engine when the ?engine= param is provided.
  // This isolates OMP vs Claude history so each engine's dropdown shows
  // only its own conversations.
  const engine = typeof q.engine === 'string' ? q.engine : undefined
  const sessions = listSessions(limit, engine)
  return { success: true, count: sessions.length, sessions }
})
