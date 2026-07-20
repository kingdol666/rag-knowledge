/**
 * GET /api/claude/sessions?dir=<path>
 *
 * Lists Claude Agent SDK session history in the given directory (default project root).
 * Used by the frontend to resume previous conversations.
 */
import { listSessions } from '@anthropic-ai/claude-agent-sdk'
import { getProjectRoot } from '~/server/utils/claude-config'

export default defineEventHandler(async (event) => {
  const q = getQuery(event)
  const dir = (q.dir as string)?.trim() || getProjectRoot()

  try {
    const sessions = await listSessions({ dir, limit: 20 })
    return { success: true, dir, sessions }
  } catch (e: any) {
    // First run may have no session directory
    return { success: false, dir, sessions: [], error: e?.message }
  }
})
